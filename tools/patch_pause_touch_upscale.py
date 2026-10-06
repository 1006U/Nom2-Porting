#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


PORT_VERSION_CODE = 107
PORT_VERSION_NAME = "1.0.43-port7-ko-s10"
PORT_REVISION = "nom2-port7-ko-s10-r6"


def replace_java_method(text: str, signature: str, replacement: str) -> str:
    sig_pos = text.find(signature)
    if sig_pos < 0:
        raise RuntimeError(f"Could not find Java method: {signature}")

    start = text.rfind("\n", 0, sig_pos) + 1
    brace = text.find("{", sig_pos)
    if brace < 0:
        raise RuntimeError(f"Could not find opening brace for: {signature}")

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
                return text[:start] + replacement + text[i + 1:]
        i += 1

    raise RuntimeError(f"Could not find closing brace for: {signature}")


def insert_pause_helpers(text: str) -> str:
    if "NOM2_PAUSE_DIRECT_TOUCH" in text:
        return text

    anchor = "private boolean nom2PauseOverlayVisible()"
    pos = text.find(anchor)
    if pos < 0:
        raise RuntimeError("Could not find nom2PauseOverlayVisible() for pause touch helpers")
    line_start = text.rfind("\n", 0, pos) + 1

    helpers = """\t\t// NOM2_PAUSE_DIRECT_TOUCH
\t\tprivate java.lang.reflect.Field nom2FindRuntimeField(String name) {
\t\t\tClass<?> type = Canvas.this.getClass();
\t\t\twhile (type != null) {
\t\t\t\ttry {
\t\t\t\t\tjava.lang.reflect.Field field = type.getDeclaredField(name);
\t\t\t\t\tfield.setAccessible(true);
\t\t\t\t\treturn field;
\t\t\t\t} catch (NoSuchFieldException missing) {
\t\t\t\t\ttype = type.getSuperclass();
\t\t\t\t} catch (Throwable error) {
\t\t\t\t\tLog.w(TAG, \"Could not find NOM 2 field \" + name, error);
\t\t\t\t\treturn null;
\t\t\t\t}
\t\t\t}
\t\t\treturn null;
\t\t}

\t\tprivate boolean nom2SetStaticInt(String name, int value) {
\t\t\ttry {
\t\t\t\tjava.lang.reflect.Field field = nom2FindRuntimeField(name);
\t\t\t\tif (field == null) return false;
\t\t\t\tfield.setInt(null, value);
\t\t\t\treturn true;
\t\t\t} catch (Throwable error) {
\t\t\t\tLog.w(TAG, \"Could not write NOM 2 int field \" + name, error);
\t\t\t\treturn false;
\t\t\t}
\t\t}

\t\tprivate int[] nom2InstanceIntArray(String name) {
\t\t\ttry {
\t\t\t\tjava.lang.reflect.Field field = nom2FindRuntimeField(name);
\t\t\t\tif (field == null) return null;
\t\t\t\tObject value = field.get(Canvas.this);
\t\t\t\treturn value instanceof int[] ? (int[]) value : null;
\t\t\t} catch (Throwable error) {
\t\t\t\tLog.w(TAG, \"Could not read NOM 2 int[] field \" + name, error);
\t\t\t\treturn null;
\t\t\t}
\t\t}

\t\tprivate boolean nom2PauseMainMenuVisible() {
\t\t\treturn nom2PauseOverlayVisible()
\t\t\t\t\t&& !nom2BooleanField(\"cX\")
\t\t\t\t\t&& !nom2BooleanField(\"cY\")
\t\t\t\t\t&& !nom2BooleanField(\"cZ\");
\t\t}

\t\tprivate boolean nom2SelectPauseMenuItem(float screenY) {
\t\t\tif (!nom2PauseMainMenuVisible() || onHeight <= 0) return false;
\t\t\tif (screenY < onY || screenY > onY + onHeight) return false;

\t\t\tint[] origin = nom2InstanceIntArray(\"am\");
\t\t\tif (origin == null || origin.length < 2) return false;

\t\t\t// NOM 2 is a 176x208 game. The pause menu draws six rows at:
\t\t\t// am[1] + 9 + row * 17. Convert the physical Galaxy S10 tap
\t\t\t// back into the original 208px logical canvas before hit testing.
\t\t\tfloat logicalY = (screenY - onY) * 208.0f / (float) onHeight;
\t\t\tfloat firstRowY = origin[1] + 9.0f;
\t\t\tint item = Math.round((logicalY - firstRowY) / 17.0f);
\t\t\tif (item < 0 || item > 5) return false;

\t\t\tfloat rowY = firstRowY + item * 17.0f;
\t\t\tif (Math.abs(logicalY - rowY) > 9.5f) return false;

\t\t\tif (!nom2SetStaticInt(\"cn\", item)) return false;
\t\t\tCanvas.this.repaint();
\t\t\t// The original pause handler consumes NUM5 using the selected cn row.
\t\t\tfireNom2Key(KEY_NUM5);
\t\t\treturn true;
\t\t}

"""
    return text[:line_start] + helpers + text[line_start:]


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
    text = insert_pause_helpers(text)

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

\t\t\t\t// Real gameplay: the whole visible surface is jump/action.
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

\t\t\tfloat dx = event.getX() - nom2TouchX;
\t\t\tfloat dy = event.getY() - nom2TouchY;
\t\t\tfloat threshold = nom2Dp(18);

\t\t\tstate = nom2State();
\t\t\tgameplay = state == 0 || state == 20;
\t\t\tpauseOverlay = nom2PauseOverlayVisible();
\t\t\tif (gameplay && !pauseOverlay) {
\t\t\t\tnom2SoftKey = 0;
\t\t\t\tfireNom2Key(KEY_NUM5);
\t\t\t\treturn true;
\t\t\t}

\t\t\t// Pause screen: touching one of the six visible menu rows selects
\t\t\t// that exact row and activates it immediately. No swipe is required.
\t\t\tif (pauseOverlay
\t\t\t\t\t&& Math.abs(dx) < threshold
\t\t\t\t\t&& Math.abs(dy) < threshold
\t\t\t\t\t&& nom2SelectPauseMenuItem(event.getY())) {
\t\t\t\tnom2SoftKey = 0;
\t\t\t\treturn true;
\t\t\t}

\t\t\tif (nom2SoftKey != 0) {
\t\t\t\tint key = nom2SoftKey;
\t\t\t\tnom2SoftKey = 0;
\t\t\t\tfireNom2Key(key);
\t\t\t\treturn true;
\t\t\t}

\t\t\tif (Math.abs(dx) >= threshold || Math.abs(dy) >= threshold) {
\t\t\t\tif (Math.abs(dx) > Math.abs(dy)) {
\t\t\t\t\tfireNom2Key(dx < 0 ? KEY_NUM4 : KEY_NUM6);
\t\t\t\t} else {
\t\t\t\t\tfireNom2Key(dy < 0 ? KEY_NUM2 : KEY_NUM8);
\t\t\t\t}
\t\t\t} else {
\t\t\t\t// Non-gameplay dialog/menu OK action.
\t\t\t\tfireNom2Key(KEY_NUM5);
\t\t\t}
\t\t\treturn true;
\t\t}"""

    text = replace_java_method(
        text,
        "private boolean handleNom2Touch(MotionEvent event)",
        touch,
    )
    path.write_text(text, encoding="utf-8")

    final_text = path.read_text(encoding="utf-8")
    required = (
        "NOM2_PAUSE_DIRECT_TOUCH",
        "nom2SelectPauseMenuItem(event.getY())",
        'nom2SetStaticInt("cn", item)',
        "fireNom2Key(KEY_NUM5);",
    )
    missing = [token for token in required if token not in final_text]
    if missing:
        raise RuntimeError("Pause direct-touch validation failed: " + ", ".join(missing))


def patch_launcher(engine: Path) -> None:
    path = (
        engine
        / "app"
        / "src"
        / "main"
        / "java"
        / "ru"
        / "woesss"
        / "j2me"
        / "installer"
        / "Nom2LauncherActivity.java"
    )
    text = path.read_text(encoding="utf-8")

    text = re.sub(
        r'private static final String PORT_REVISION = "nom2-port\d+-ko-s10-r\d+";',
        f'private static final String PORT_REVISION = "{PORT_REVISION}";',
        text,
        count=1,
    )

    # Preserve NOM 2's original 176x208 logical coordinate system so layouts
    # do not break, but scale that framebuffer to the largest aspect-fit area
    # on the Galaxy S10 and enable filtered bitmap upscaling for the output.
    text = text.replace("profile.screenScaleType = 1;", "profile.screenScaleType = 1;")
    text = text.replace("profile.screenScaleRatio = 100;", "profile.screenScaleRatio = 100;")
    text = text.replace("profile.screenFilter = false;", "profile.screenFilter = true;")

    path.write_text(text, encoding="utf-8")

    final_text = path.read_text(encoding="utf-8")
    required = (
        f'PORT_REVISION = "{PORT_REVISION}"',
        "profile.screenWidth = 176;",
        "profile.screenHeight = 208;",
        "profile.screenScaleType = 1;",
        "profile.screenScaleRatio = 100;",
        "profile.screenFilter = true;",
    )
    missing = [token for token in required if token not in final_text]
    if missing:
        raise RuntimeError("Galaxy S10 upscale profile validation failed: " + ", ".join(missing))


def patch_build_identity(engine: Path) -> None:
    path = engine / "app" / "build.gradle"
    text = path.read_text(encoding="utf-8")
    text2 = re.sub(r"versionCode\s+106\b", f"versionCode {PORT_VERSION_CODE}", text, count=1)
    text2 = re.sub(
        r'versionName\s+"1\.0\.43-port6-ko-s10"',
        f'versionName "{PORT_VERSION_NAME}"',
        text2,
        count=1,
    )
    if text2 == text:
        if (
            f"versionCode {PORT_VERSION_CODE}" not in text
            or f'versionName "{PORT_VERSION_NAME}"' not in text
        ):
            raise RuntimeError("Could not set NOM 2 port7 build identity")
    else:
        path.write_text(text2, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add direct pause-menu touch and Galaxy S10 output upscaling"
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
    patch_launcher(engine)
    patch_build_identity(engine)

    print("NOM 2 Galaxy S10 pause/upscale patch applied:")
    print("  pause menu rows: directly touchable")
    print("  pause selection: sets native cn row and activates with NUM5")
    print("  logical game canvas: original 176x208 preserved")
    print("  output: maximum aspect-fit scale with bitmap filtering")
    print(f"  build: {PORT_VERSION_NAME} (versionCode {PORT_VERSION_CODE})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
