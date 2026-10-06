#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


PORT_VERSION_CODE = 104
PORT_VERSION_NAME = "1.0.43-port4-ko-s10"


def replace_once(path: Path, old: str, new: str, description: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Could not apply {description}: expected text not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


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

    updater_old = """\t\t\t\trefreshNom2Buttons();
\t\t\t\tmView.postDelayed(this, 120);
"""
    updater_new = """\t\t\t\tskipNom2LeaderboardIfNeeded();
\t\t\t\trefreshNom2Buttons();
\t\t\t\tmView.postDelayed(this, 120);
"""
    replace_once(path, updater_old, updater_new, "NOM 2 leaderboard bypass updater")

    marker = "\t\tprivate Object nom2NameInput() {\n"

    # IMPORTANT: this must be a normal Python string, not a raw string.
    # Canvas.java needs real tab/newline characters. A raw string would write
    # literal '\\t' sequences into Java source and cause hundreds of javac errors.
    helpers = """\t\tprivate int nom2LastLeaderboardBypassState = Integer.MIN_VALUE;
\t\tprivate long nom2LastLeaderboardBypassAt;

\t\tprivate int nom2StaticInt(String name, int fallback) {
\t\t\ttry {
\t\t\t\tjava.lang.reflect.Field field = Canvas.this.getClass().getDeclaredField(name);
\t\t\t\tfield.setAccessible(true);
\t\t\t\treturn field.getInt(null);
\t\t\t} catch (Throwable ignored) {
\t\t\t\treturn fallback;
\t\t\t}
\t\t}

\t\tprivate int nom2LeaderboardReturnState() {
\t\t\t// NOM 2's original cancel paths are:
\t\t\t//   state 36 (name entry): Y == 9 ? state 9 : state 30
\t\t\t//   state 37 (upload prompt): Z == 9 ? state 9 : state 36
\t\t\t// The Android port disables the dead online leaderboard completely.
\t\t\tint z = nom2StaticInt("Z", -1);
\t\t\tif (z == 9) return 9;
\t\t\tint y = nom2StaticInt("Y", -1);
\t\t\tif (y == 9) return 9;
\t\t\treturn 30;
\t\t}

\t\tprivate boolean nom2InvokeState(int targetState) {
\t\t\ttry {
\t\t\t\tjava.lang.reflect.Method method =
\t\t\t\t\t\tCanvas.this.getClass().getDeclaredMethod("l", Integer.TYPE);
\t\t\t\tmethod.setAccessible(true);
\t\t\t\tmethod.invoke(Canvas.this, Integer.valueOf(targetState));
\t\t\t\tCanvas.this.repaint();
\t\t\t\treturn true;
\t\t\t} catch (Throwable error) {
\t\t\t\tLog.w(TAG, "Could not bypass NOM 2 leaderboard state", error);
\t\t\t\treturn false;
\t\t\t}
\t\t}

\t\tprivate void skipNom2LeaderboardIfNeeded() {
\t\t\tint state = nom2State();
\t\t\tif (state < 36 || state > 40) {
\t\t\t\tnom2LastLeaderboardBypassState = Integer.MIN_VALUE;
\t\t\t\treturn;
\t\t\t}

\t\t\tlong now = System.currentTimeMillis();
\t\t\tif (state == nom2LastLeaderboardBypassState
\t\t\t\t\t&& now - nom2LastLeaderboardBypassAt < 350) {
\t\t\t\treturn;
\t\t\t}
\t\t\tnom2LastLeaderboardBypassState = state;
\t\t\tnom2LastLeaderboardBypassAt = now;

\t\t\tint targetState = nom2LeaderboardReturnState();
\t\t\tLog.i(TAG, "NOM 2 leaderboard disabled: state " + state
\t\t\t\t\t+ " -> local state " + targetState);

\t\t\tif (!nom2InvokeState(targetState) && (state == 36 || state == 37)) {
\t\t\t\t// Safe fallback: use the game's own Cancel/No soft-key path.
\t\t\t\tfireNom2Key(KEY_SOFT_RIGHT);
\t\t\t}
\t\t}

"""
    replace_once(path, marker, helpers + marker, "NOM 2 leaderboard bypass helpers")

    # Fail early with a useful message instead of allowing javac to report
    # hundreds of follow-on syntax errors if escaped indentation is ever
    # accidentally written into Canvas.java again.
    patched = path.read_text(encoding="utf-8")
    bad_tokens = (
        r"\t\tprivate int nom2LastLeaderboardBypassState",
        r"\t\tprivate int nom2StaticInt",
        r"\t\tprivate void skipNom2LeaderboardIfNeeded",
    )
    for token in bad_tokens:
        if token in patched:
            raise RuntimeError(
                "Leaderboard patch wrote literal \\t escapes into Canvas.java: " + token
            )


def patch_build_identity(engine: Path) -> None:
    path = engine / "app" / "build.gradle"
    text = path.read_text(encoding="utf-8")

    text2 = re.sub(
        r'versionCode\s+103\b',
        f'versionCode {PORT_VERSION_CODE}',
        text,
        count=1,
    )
    text2 = re.sub(
        r'versionName\s+"1\.0\.43-port3-ko-s10"',
        f'versionName "{PORT_VERSION_NAME}"',
        text2,
        count=1,
    )

    if text2 == text:
        if (
            f"versionCode {PORT_VERSION_CODE}" not in text
            or f'versionName "{PORT_VERSION_NAME}"' not in text
        ):
            raise RuntimeError("Could not set NOM 2 port4 build identity")
    else:
        path.write_text(text2, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Disable NOM 2's obsolete online leaderboard and keep gameplay local"
    )
    parser.add_argument("--engine", default="engine")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    engine = (
        (root / args.engine).resolve()
        if not Path(args.engine).is_absolute()
        else Path(args.engine)
    )

    patch_canvas(engine)
    patch_build_identity(engine)

    print("NOM 2 online leaderboard: disabled")
    print("  states 36-40 are automatically bypassed")
    print("  no score upload / name registration / network wait is required")
    print(f"  build: {PORT_VERSION_NAME} (versionCode {PORT_VERSION_CODE})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
