#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path


CLASS_REPLACEMENTS = {
    "<OFF>": "<꺼짐>",
    "<ON>": "<켜짐>",
    "Clear": "지우기",
    "EXIT": "종료",
    "HOW TO PLAY": "게임 방법",
    "MAIN MENU": "메인 메뉴",
    "ON": "켜짐",
    "RESULT": "결과",
    "RESUME": "계속하기",
    "SOUND ": "소리 ",
    "Score": "점수",
    "Total": "합계",
    "VIBRATION ": "진동 ",
}


def read_u2(data: bytes, pos: int) -> int:
    return (data[pos] << 8) | data[pos + 1]


def patch_class_utf8(data: bytes, replacements: dict[str, str]) -> bytes:
    if data[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError("Not a Java class file")

    cp_count = read_u2(data, 8)
    pos = 10
    out = bytearray(data[:10])
    index = 1

    while index < cp_count:
        tag = data[pos]
        out.append(tag)
        pos += 1

        if tag == 1:
            length = read_u2(data, pos)
            pos += 2
            raw = data[pos:pos + length]
            pos += length
            try:
                value = raw.decode("utf-8")
            except UnicodeDecodeError:
                value = None
            if value in replacements:
                raw = replacements[value].encode("utf-8")
            if len(raw) > 65535:
                raise ValueError("UTF-8 constant is too long")
            out += len(raw).to_bytes(2, "big")
            out += raw
        elif tag in (3, 4):
            out += data[pos:pos + 4]
            pos += 4
        elif tag in (5, 6):
            out += data[pos:pos + 8]
            pos += 8
            index += 1
        elif tag in (7, 8, 16, 19, 20):
            out += data[pos:pos + 2]
            pos += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            out += data[pos:pos + 4]
            pos += 4
        elif tag == 15:
            out += data[pos:pos + 3]
            pos += 3
        else:
            raise ValueError(f"Unsupported constant-pool tag {tag}")
        index += 1

    out += data[pos:]
    return bytes(out)


def build_text_scr(strings: list[str]) -> bytes:
    encoded = [value.encode("utf-8") for value in strings]
    header_size = 2 + 2 * (len(encoded) + 1)
    offsets: list[int] = []
    cursor = header_size

    for raw in encoded:
        offsets.append(cursor)
        cursor += len(raw)
    offsets.append(cursor)

    if cursor > 65535:
        raise ValueError("text.scr exceeds its 16-bit offset format")

    out = bytearray()
    out += len(encoded).to_bytes(2, "little")
    for offset in offsets:
        out += offset.to_bytes(2, "little")
    for raw in encoded:
        out += raw
    return bytes(out)


def find_javac() -> str:
    path = shutil.which("javac")
    if path:
        return path

    candidates: list[Path] = []
    program_files = os.environ.get("ProgramFiles")
    local_app_data = os.environ.get("LOCALAPPDATA")
    if program_files:
        candidates.append(Path(program_files) / "Android" / "Android Studio" / "jbr" / "bin" / "javac.exe")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Programs" / "Android Studio" / "jbr" / "bin" / "javac.exe")

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    raise RuntimeError(
        "javac was not found. Install/open Android Studio with its bundled JDK, "
        "or put a JDK javac on PATH."
    )


def compile_font_bridge(source: Path, work: Path) -> bytes:
    src = work / "src"
    out = work / "classes"
    (src / "gvl").mkdir(parents=True)
    (src / "javax" / "microedition" / "lcdui").mkdir(parents=True)
    out.mkdir()

    shutil.copy2(source, src / "gvl" / "f.java")
    (src / "javax" / "microedition" / "lcdui" / "Graphics.java").write_text(
        "package javax.microedition.lcdui; public class Graphics { "
        "public Font getFont(){return null;} public void setFont(Font f){} "
        "public void drawString(String s,int x,int y,int a){} "
        "public void fillRect(int x,int y,int w,int h){} }",
        encoding="utf-8",
    )
    (src / "javax" / "microedition" / "lcdui" / "Font.java").write_text(
        "package javax.microedition.lcdui; public class Font { "
        "public Font(){} public Font(int f,int s,int z,float h){} "
        "public static Font getFont(int f,int s,int z){return new Font();} "
        "public static Font getDefaultFont(){return new Font();} "
        "public int charWidth(char c){return 7;} }",
        encoding="utf-8",
    )

    command = [
        find_javac(),
        "-source", "8",
        "-target", "8",
        "-encoding", "UTF-8",
        "-d", str(out),
        str(src / "javax" / "microedition" / "lcdui" / "Font.java"),
        str(src / "javax" / "microedition" / "lcdui" / "Graphics.java"),
        str(src / "gvl" / "f.java"),
    ]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Korean font bridge compilation failed:\n" + result.stdout + result.stderr
        )

    class_file = out / "gvl" / "f.class"
    if not class_file.is_file():
        raise RuntimeError("Compiled gvl/f.class was not produced")
    return class_file.read_bytes()


def patch_jar(source: Path, output: Path, translations: Path, bridge_source: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Source JAR not found: {source}")

    strings = json.loads(translations.read_text(encoding="utf-8"))
    if not isinstance(strings, list) or len(strings) != 88:
        raise RuntimeError(f"Expected exactly 88 translated strings, found {len(strings)}")
    if not all(isinstance(value, str) for value in strings):
        raise RuntimeError("Every Korean translation entry must be a string")

    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="nom2-ko-") as temp_name:
        temp = Path(temp_name)
        bridge_class = compile_font_bridge(bridge_source, temp)

        with zipfile.ZipFile(source, "r") as zin, zipfile.ZipFile(
            output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename == "text/text.scr":
                    data = build_text_scr(strings)
                elif info.filename == "gvl/f.class":
                    data = bridge_class
                elif info.filename == "e.class":
                    data = patch_class_utf8(data, CLASS_REPLACEMENTS)

                new_info = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                new_info.compress_type = zipfile.ZIP_DEFLATED
                new_info.external_attr = info.external_attr
                new_info.comment = info.comment
                new_info.extra = info.extra
                zout.writestr(new_info, data)

    with zipfile.ZipFile(output, "r") as zf:
        names = set(zf.namelist())
        for required in ("text/text.scr", "gvl/f.class", "e.class"):
            if required not in names:
                raise RuntimeError(f"Korean patch output is missing {required}")

        text_data = zf.read("text/text.scr")
        count = int.from_bytes(text_data[:2], "little")
        if count != 88:
            raise RuntimeError(f"Patched text.scr has an unexpected string count: {count}")

    print(f"Korean NOM 2 JAR ready: {output}")
    print("  translated text.scr: 88 entries")
    print("  hard-coded menus: Korean")
    print("  Hangul renderer: compact 7px J2ME font bridge")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply the NOM 2 Korean text/font patch")
    parser.add_argument("--input", default="game/nom2.jar", help="Original NOM 2 JAR")
    parser.add_argument("--output", default="game/generated/nom2-ko.jar", help="Patched JAR")
    parser.add_argument("--translations", default="patch/ko/text_ko.json", help="Korean translations")
    parser.add_argument("--bridge", default="patch/ko/f.java", help="Korean-capable gvl.f source")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    source = Path(args.input) if Path(args.input).is_absolute() else root / args.input
    output = Path(args.output) if Path(args.output).is_absolute() else root / args.output
    translations = (
        Path(args.translations) if Path(args.translations).is_absolute() else root / args.translations
    )
    bridge = Path(args.bridge) if Path(args.bridge).is_absolute() else root / args.bridge

    patch_jar(source.resolve(), output.resolve(), translations.resolve(), bridge.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
