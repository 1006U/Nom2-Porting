#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


PORT_VERSION_CODE = 106
PORT_VERSION_NAME = "1.0.43-port6-ko-s10"


def replace_java_method(text: str, signature: str, replacement: str) -> str:
    start = text.find(signature)
    if start < 0:
        raise RuntimeError(f"Could not find Java method: {signature}")

    brace = text.find("{", start)
    if brace < 0:
        raise RuntimeError(f"Could not find opening brace for: {signature}")

    depth = 0
    in_string = False
    in_char = False
    escaped = False
    i = brace
    while i < len(text):
        ch = text[i]
        if escaped:
            escaped = False
        elif ch == "\\" and (in_string or in_char):
            escaped = True
        elif ch == '"' and not in_char:
            in_string = not in_string
        elif ch == "'" and not in_string:
            in_char = not in_char
        elif not in_string and not in_char:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    return text[:start] + replacement + text[end:]
        i += 1

    raise RuntimeError(f"Could not find closing brace for: {signature}")


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
    text = path.read_text(encoding="utf-8")

    # J2ME Loader may wrap/transform the MIDlet class. Do not assume the
    # obfuscated NOM2 field is declared directly on Canvas.this.getClass().
    # Walk the runtime hierarchy so W, bK, Y and Z are always discoverable.
    state_method = """private int nom2State() {
\t\t\tClass<?> type = Canvas.this.getClass();
\t\t\twhile (type != null) {
\t\t\t\ttry {
\t\t\t\t\tjava.lang.reflect.Field field = type.getDeclaredField(\"W\");
\t\t\t\t\tfield.setAccessible(true);
\t\t\t\t\treturn field.getInt(null);
\t\t\t\t} catch (NoSuchFieldException missing) {
\t\t\t\t\ttype = type.getSuperclass();
\t\t\t\t} catch (Throwable error) {
\t\t\t\t\tLog.w(TAG, \"Could not read NOM 2 state W\", error);
\t\t\t\t\treturn -1;
\t\t\t\t}
\t\t\t}
\t\t\treturn -1;
\t\t}"""
    text = replace_java_method(text, "private int nom2State()", state_method)

    bool_method = """private boolean nom2BooleanField(String name) {
\t\t\tClass<?> type = Canvas.this.getClass();
\t\t\twhile (type != null) {
\t\t\t\ttry {
\t\t\t\t\tjava.lang.reflect.Field field = type.getDeclaredField(name);
\t\t\t\t\tfield.setAccessible(true);
\t\t\t\t\treturn field.getBoolean(null);
\t\t\t\t} catch (NoSuchFieldException missing) {
\t\t\t\t\ttype = type.getSuperclass();
\t\t\t\t} catch (Throwable error) {
\t\t\t\t\tLog.w(TAG, \"Could not read NOM 2 boolean field \" + name, error);
\t\t\t\t\treturn false;
\t\t\t\t}
\t\t\t}
\t\t\treturn false;
\t\t}"""
    text = replace_java_method(text, "private boolean nom2BooleanField(String name)", bool_method)

    static_int_method = """private int nom2StaticInt(String name, int fallback) {
\t\t\tClass<?> type = Canvas.this.getClass();
\t\t\twhile (type != null) {
\t\t\t\ttry {
\t\t\t\t\tjava.lang.reflect.Field field = type.getDeclaredField(name);
\t\t\t\t\tfield.setAccessible(true);
\t\t\t\t\treturn field.getInt(null);
\t\t\t\t} catch (NoSuchFieldException missing) {
\t\t\t\t\ttype = type.getSuperclass();
\t\t\t\t} catch (Throwable error) {
\t\t\t\t\tLog.w(TAG, \"Could not read NOM 2 int field \" + name, error);
\t\t\t\t\treturn fallback;
\t\t\t\t}
\t\t\t}
\t\t\treturn fallback;
\t\t}"""
    text = replace_java_method(text, "private int nom2StaticInt(String name, int fallback)", static_int_method)

    invoke_method = """private boolean nom2InvokeState(int targetState) {
\t\t\tClass<?> type = Canvas.this.getClass();
\t\t\twhile (type != null) {
\t\t\t\ttry {
\t\t\t\t\tjava.lang.reflect.Method method = type.getDeclaredMethod(\"l\", Integer.TYPE);
\t\t\t\t\tmethod.setAccessible(true);
\t\t\t\t\tmethod.invoke(Canvas.this, Integer.valueOf(targetState));
\t\t\t\t\tCanvas.this.repaint();
\t\t\t\t\treturn true;
\t\t\t\t} catch (NoSuchMethodException missing) {
\t\t\t\t\ttype = type.getSuperclass();
\t\t\t\t} catch (Throwable error) {
\t\t\t\t\tLog.w(TAG, \"Could not change NOM 2 state\", error);
\t\t\t\t\treturn false;
\t\t\t\t}
\t\t\t}
\t\t\treturn false;
\t\t}"""
    text = replace_java_method(text, "private boolean nom2InvokeState(int targetState)", invoke_method)

    # Actual leaderboard flow from the original e.class:
    #   W=9  : score/result leaderboard gate (No -> local state 3)
    #   W=36 : leaderboard name entry
    #   W=37 : upload confirmation
    #   W=38..40 : obsolete network/result states
    # The Android port intentionally stays local, so reject the native online
    # path before a request can start. For 9/36/37 use the game's own right
    # soft-key path; only use direct state recovery for an already-stuck 38..40.
    skip_method = """private void skipNom2LeaderboardIfNeeded() {
\t\t\tint state = nom2State();
\t\t\tif (state != 9 && (state < 36 || state > 40)) {
\t\t\t\tnom2LastLeaderboardBypassState = Integer.MIN_VALUE;
\t\t\t\treturn;
\t\t\t}

\t\t\tlong now = System.currentTimeMillis();
\t\t\tif (state == nom2LastLeaderboardBypassState
\t\t\t\t\t&& now - nom2LastLeaderboardBypassAt < 220) {
\t\t\t\treturn;
\t\t\t}
\t\t\tnom2LastLeaderboardBypassState = state;
\t\t\tnom2LastLeaderboardBypassAt = now;

\t\t\tif (state == 9 || state == 36 || state == 37) {
\t\t\t\tLog.i(TAG, \"NOM 2 leaderboard disabled: native cancel from state \" + state);
\t\t\t\tfireNom2Key(KEY_SOFT_RIGHT);
\t\t\t\treturn;
\t\t\t}

\t\t\tint targetState = nom2LeaderboardReturnState();
\t\t\tLog.i(TAG, \"NOM 2 leaderboard recovery: state \" + state
\t\t\t\t\t+ \" -> local state \" + targetState);
\t\t\tif (!nom2InvokeState(targetState)) {
\t\t\t\tfireNom2Key(KEY_SOFT_RIGHT);
\t\t\t}
\t\t}"""
    text = replace_java_method(text, "private void skipNom2LeaderboardIfNeeded()", skip_method)

    # Make the screen-aware button updater use the corrected state immediately.
    # This also ensures the bypass runs even if an earlier updater patch changes.
    refresh_sig = "private void refreshNom2Buttons()"
    refresh_start = text.find(refresh_sig)
    if refresh_start < 0:
        raise RuntimeError("Could not find refreshNom2Buttons")
    refresh_brace = text.find("{", refresh_start)
    guard = "\n\t\t\tskipNom2LeaderboardIfNeeded();"
    if guard.strip() not in text[refresh_brace:refresh_brace + 240]:
        text = text[:refresh_brace + 1] + guard + text[refresh_brace + 1:]

    path.write_text(text, encoding="utf-8")

    final_text = path.read_text(encoding="utf-8")
    required = (
        'getDeclaredField("W")',
        'getDeclaredField(name)',
        'state == 9 || state == 36 || state == 37',
        'fireNom2Key(KEY_SOFT_RIGHT)',
        'skipNom2LeaderboardIfNeeded();',
    )
    missing = [token for token in required if token not in final_text]
    if missing:
        raise RuntimeError("Runtime-state patch validation failed: " + ", ".join(missing))


def patch_build_identity(engine: Path) -> None:
    path = engine / "app" / "build.gradle"
    text = path.read_text(encoding="utf-8")
    text2 = re.sub(r"versionCode\s+105\b", f"versionCode {PORT_VERSION_CODE}", text, count=1)
    text2 = re.sub(
        r'versionName\s+"1\.0\.43-port5-ko-s10"',
        f'versionName "{PORT_VERSION_NAME}"',
        text2,
        count=1,
    )
    if text2 == text:
        if (
            f"versionCode {PORT_VERSION_CODE}" not in text
            or f'versionName "{PORT_VERSION_NAME}"' not in text
        ):
            raise RuntimeError("Could not set NOM 2 port6 build identity")
    else:
        path.write_text(text2, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fix NOM 2 runtime state detection and local-only flow")
    parser.add_argument("--engine", default="engine")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    engine = (root / args.engine).resolve() if not Path(args.engine).is_absolute() else Path(args.engine)

    patch_canvas(engine)
    patch_build_identity(engine)

    print("NOM 2 runtime state handling fixed:")
    print("  state fields are resolved through the runtime class hierarchy")
    print("  W=9 leaderboard gate is now bypassed before network flow")
    print("  W=36..40 remain bypassed/recovered")
    print("  menu/pause buttons now receive the real current state")
    print(f"  build: {PORT_VERSION_NAME} (versionCode {PORT_VERSION_CODE})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
