#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


def replace_regex(path: Path, pattern: str, replacement: str, description: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, lambda _: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"Could not apply {description} in {path}")
    path.write_text(updated, encoding="utf-8")


def replace_java_method(path: Path, signature: str, replacement: str, description: str) -> None:
    """Replace exactly one Java method by brace matching instead of a broad regex.

    Canvas.java is patched by several scripts before this one runs. The previous
    implementation matched from handleNom2Touch() all the way to ViewCallbacks(),
    which accidentally deleted the NOM2 helper fields/methods inserted in between.
    """
    text = path.read_text(encoding="utf-8")
    start = text.find(signature)
    if start < 0:
        raise RuntimeError(f"Could not find {description} signature in {path}")

    brace = text.find("{", start + len(signature) - 1)
    if brace < 0:
        raise RuntimeError(f"Could not find opening brace for {description} in {path}")

    depth = 0
    in_string = False
    in_char = False
    escaped = False
    line_comment = False
    block_comment = False
    i = brace

    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if line_comment:
            if ch == "\n":
                line_comment = False
            i += 1
            continue

        if block_comment:
            if ch == "*" and nxt == "/":
                block_comment = False
                i += 2
            else:
                i += 1
            continue

        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if in_char:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "'":
                in_char = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            block_comment = True
            i += 2
            continue
        if ch == '"':
            in_string = True
            i += 1
            continue
        if ch == "'":
            in_char = True
            i += 1
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                updated = text[:start] + replacement + text[end:]
                path.write_text(updated, encoding="utf-8")
                return
        i += 1

    raise RuntimeError(f"Could not find closing brace for {description} in {path}")


def insert_before_first_method(path: Path, helper: str) -> None:
    """Insert helper immediately before the actual nom2State() declaration."""
    text = path.read_text(encoding="utf-8")
    if "private boolean nom2PauseOverlayVisible()" in text:
        return

    # Do a direct declaration search. A plain `nom2State` occurrence may be only
    # a call inside handleNom2Touch(), so locate the declaration itself and then
    # insert at its line start. This avoids depending on indentation formatting.
    declaration_needles = (
        "private int nom2State()",
        "private int nom2State ()",
    )
    for needle in declaration_needles:
        pos = text.find(needle)
        if pos >= 0:
            line_start = text.rfind("\n", 0, pos) + 1
            updated = text[:line_start] + helper + text[line_start:]
            path.write_text(updated, encoding="utf-8")
            return

    # Fallback: regex only for the declaration, never for a whole method block.
    match = re.search(r"(?m)^[ \t]*private\s+int\s+nom2State\s*\(\s*\)\s*\{", text)
    if match:
        updated = text[:match.start()] + helper + text[match.start():]
        path.write_text(updated, encoding="utf-8")
        return

    nearby = []
    for needle in ("nom2State", "nom2NameInput", "nom2ButtonBar", "nom2LastButtonState"):
        nearby.append(f"{needle}={text.find(needle)}")
    raise RuntimeError(
        "Could not find NOM 2 helper insertion point after prior Canvas patches ("
        + ", ".join(nearby)
        + ")"
    )


def patch_canvas(engine: Path) -> None:
    path = (
        engine
        / "app"
        / "src"
        / "main"
        / "java"
        / "javax"
        / "microedition"
        / "lcdui"
        / "Canvas.java"
    )

    # Gameplay rule for the dedicated Galaxy S10 port:
    #   * every tap anywhere inside the game/letterbox = NUM5 action/jump
    #   * no swipe or soft-key zones while actively playing
    touch = """\t\tprivate boolean handleNom2Touch(MotionEvent event) {
\t\t\tint action = event.getActionMasked();
\t\t\tint state = nom2State();
\t\t\tboolean gameplay = state == 0 || state == 20;
\t\t\tboolean pauseOverlay = nom2PauseOverlayVisible();

\t\t\tif (action == MotionEvent.ACTION_DOWN && event.getPointerCount() == 1) {
\t\t\t\tnom2TouchX = event.getX();
\t\t\t\tnom2TouchY = event.getY();
\t\t\t\tnom2TouchActive = true;
\t\t\t\tnom2SoftKey = 0;

\t\t\t\t// During real gameplay the entire emulator surface, including the
\t\t\t\t// black aspect-fit letterbox, is one large jump/action target.
\t\t\t\tif (gameplay && !pauseOverlay) {
\t\t\t\t\treturn true;
\t\t\t\t}

\t\t\t\tfloat gameBottom = onY + onHeight;
\t\t\t\tfloat softKeyTop = onY + onHeight * 0.84f;
\t\t\t\tboolean softKeyStrip = nom2TouchY >= softKeyTop;
\t\t\t\tif (nom2TouchY > gameBottom || softKeyStrip) {
\t\t\t\t\tfloat splitX = onX + onWidth / 2.0f;
\t\t\t\t\tnom2SoftKey = nom2TouchX < splitX ? KEY_SOFT_LEFT : KEY_SOFT_RIGHT;
\t\t\t\t}
\t\t\t\treturn true;
\t\t\t}

\t\t\tif (action == MotionEvent.ACTION_POINTER_DOWN) {
\t\t\t\tnom2TouchActive = false;
\t\t\t\tnom2SoftKey = 0;
\t\t\t\treturn true;
\t\t\t}

\t\t\tif (action == MotionEvent.ACTION_CANCEL) {
\t\t\t\tnom2TouchActive = false;
\t\t\t\tnom2SoftKey = 0;
\t\t\t\treturn true;
\t\t\t}

\t\t\tif (action != MotionEvent.ACTION_UP || !nom2TouchActive) {
\t\t\t\treturn true;
\t\t\t}
\t\t\tnom2TouchActive = false;

\t\t\tstate = nom2State();
\t\t\tgameplay = state == 0 || state == 20;
\t\t\tpauseOverlay = nom2PauseOverlayVisible();
\t\t\tif (gameplay && !pauseOverlay) {
\t\t\t\tnom2SoftKey = 0;
\t\t\t\tfireNom2Key(KEY_NUM5);
\t\t\t\treturn true;
\t\t\t}

\t\t\tif (nom2SoftKey != 0) {
\t\t\t\tint key = nom2SoftKey;
\t\t\t\tnom2SoftKey = 0;
\t\t\t\tfireNom2Key(key);
\t\t\t\treturn true;
\t\t\t}

\t\t\tfloat dx = event.getX() - nom2TouchX;
\t\t\tfloat dy = event.getY() - nom2TouchY;
\t\t\tfloat threshold = nom2Dp(18);
\t\t\tif (Math.abs(dx) >= threshold || Math.abs(dy) >= threshold) {
\t\t\t\tif (Math.abs(dx) > Math.abs(dy)) {
\t\t\t\t\tfireNom2Key(dx < 0 ? KEY_NUM4 : KEY_NUM6);
\t\t\t\t} else {
\t\t\t\t\tfireNom2Key(dy < 0 ? KEY_NUM2 : KEY_NUM8);
\t\t\t\t}
\t\t\t} else {
\t\t\t\t// Menu/story/pause OK action.
\t\t\t\tfireNom2Key(KEY_NUM5);
\t\t\t}
\t\t\treturn true;
\t\t}"""

    # Replace only handleNom2Touch(). Do not consume the helper fields/methods
    # that post_patch_ui.py inserted between this method and ViewCallbacks().
    replace_java_method(
        path,
        "\t\tprivate boolean handleNom2Touch(MotionEvent event) {",
        touch,
        "Galaxy S10 gameplay-anywhere jump touch",
    )

    helper = """\t\tprivate boolean nom2BooleanField(String name) {
\t\t\ttry {
\t\t\t\tjava.lang.reflect.Field field = Canvas.this.getClass().getDeclaredField(name);
\t\t\t\tfield.setAccessible(true);
\t\t\t\treturn field.getBoolean(null);
\t\t\t} catch (Throwable ignored) {
\t\t\t\treturn false;
\t\t\t}
\t\t}

\t\tprivate boolean nom2PauseOverlayVisible() {
\t\t\treturn nom2BooleanField("bK");
\t\t}

"""
    insert_before_first_method(path, helper)

    refresh = """\t\tprivate void refreshNom2Buttons() {
\t\t\tif (nom2ButtonBar == null) return;
\t\t\tint state = nom2State();
\t\t\tboolean pauseOverlay = nom2PauseOverlayVisible();
\t\t\tint visualState = state * 2 + (pauseOverlay ? 1 : 0);
\t\t\tif (visualState == nom2LastButtonState) return;
\t\t\tnom2LastButtonState = visualState;

\t\t\tnom2OkButton.setVisibility(View.VISIBLE);
\t\t\tnom2MenuButton.setVisibility(View.GONE);
\t\t\tnom2BackButton.setVisibility(View.GONE);

\t\t\tif ((state == 0 || state == 20) && !pauseOverlay) {
\t\t\t\tnom2OkButton.setText("일시정지");
\t\t\t} else if (pauseOverlay) {
\t\t\t\tnom2OkButton.setText("선택");
\t\t\t\tnom2BackButton.setText("뒤로");
\t\t\t\tnom2BackButton.setVisibility(View.VISIBLE);
\t\t\t} else if (state >= 31 && state <= 35) {
\t\t\t\tnom2OkButton.setText("확인");
\t\t\t} else if (state >= 36 && state <= 40) {
\t\t\t\tnom2OkButton.setVisibility(View.GONE);
\t\t\t} else {
\t\t\t\tnom2OkButton.setText("선택");
\t\t\t\tnom2BackButton.setText("뒤로");
\t\t\t\tnom2BackButton.setVisibility(View.VISIBLE);
\t\t\t}
\t\t}
"""
    replace_regex(
        path,
        r"\t\tprivate void refreshNom2Buttons\(\) \{.*?\n\t\t\}\n\n\t\tprivate void attachNom2ButtonBar",
        refresh + "\n\t\tprivate void attachNom2ButtonBar",
        "screen-matched NOM 2 bottom buttons",
    )

    text = path.read_text(encoding="utf-8")
    listener_pattern = re.compile(
        r"\t\t\tnom2OkButton\.setOnClickListener\(v -> \{.*?"
        r"\n\t\t\tnom2BackButton\.setOnClickListener\(v -> fireNom2Key\(KEY_SOFT_RIGHT\)\);",
        re.S,
    )
    listeners = """\t\t\tnom2OkButton.setOnClickListener(v -> {
\t\t\t\tint state = nom2State();
\t\t\t\tboolean pauseOverlay = nom2PauseOverlayVisible();
\t\t\t\tif ((state == 0 || state == 20) && !pauseOverlay) {
\t\t\t\t\tfireNom2Key(KEY_SOFT_LEFT);
\t\t\t\t} else if (pauseOverlay || (state >= 31 && state <= 35)) {
\t\t\t\t\tfireNom2Key(KEY_NUM5);
\t\t\t\t} else {
\t\t\t\t\tfireNom2Key(KEY_SOFT_LEFT);
\t\t\t\t}
\t\t\t});
\t\t\tnom2MenuButton.setOnClickListener(v -> fireNom2Key(KEY_SOFT_LEFT));
\t\t\tnom2BackButton.setOnClickListener(v -> fireNom2Key(KEY_SOFT_RIGHT));"""
    updated, count = listener_pattern.subn(lambda _: listeners, text, count=1)
    if count != 1:
        raise RuntimeError("Could not rewrite NOM 2 native button listeners")
    path.write_text(updated, encoding="utf-8")

    text = path.read_text(encoding="utf-8")
    if "NOM2_FINAL_S10_CONTROLS" not in text:
        member_pattern = re.search(r"(?m)^[ \t]*private\s+LinearLayout\s+nom2ButtonBar\s*;", text)
        if member_pattern:
            pos = member_pattern.start()
            indent_match = re.match(r"[ \t]*", text[pos:])
            indent = indent_match.group(0) if indent_match else "\t\t"
            text = text[:pos] + indent + "// NOM2_FINAL_S10_CONTROLS\n" + text[pos:]
            path.write_text(text, encoding="utf-8")

    final_text = path.read_text(encoding="utf-8")
    required = (
        "private boolean nom2PauseOverlayVisible()",
        "private int nom2State()",
        "private LinearLayout nom2ButtonBar",
        "fireNom2Key(KEY_NUM5);",
        'nom2OkButton.setText("일시정지")',
        "NOM2_FINAL_S10_CONTROLS",
    )
    missing = [token for token in required if token not in final_text]
    if missing:
        raise RuntimeError("Final NOM 2 S10 control validation failed: " + ", ".join(missing))


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize NOM 2 Galaxy S10 gameplay controls")
    parser.add_argument("--engine", default="engine")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    engine = (root / args.engine).resolve() if not Path(args.engine).is_absolute() else Path(args.engine)
    patch_canvas(engine)
    print("NOM 2 Galaxy S10 controls finalized:")
    print("  gameplay touch anywhere = jump/action")
    print("  gameplay bottom bar = Pause only")
    print("  pause/menu/story controls follow the current screen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
