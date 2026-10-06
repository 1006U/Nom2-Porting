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
    # This deliberately overrides the older letterbox-softkey behavior which
    # made normal gameplay taps open the pause menu on tall phones.
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
\t\t}

\t\tpublic ViewCallbacks(View view) {"""
    replace_regex(
        path,
        r"\t\tprivate boolean handleNom2Touch\(MotionEvent event\) \{.*?\n\t\t\}\n\n\t\tpublic ViewCallbacks\(View view\) \{",
        touch,
        "Galaxy S10 gameplay-anywhere jump touch",
    )

    # Add a reliable pause-overlay detector. NOM 2 draws its in-game pause menu
    # from e.f(Graphics) while the obfuscated static flag bK is true.
    marker = "\t\tprivate int nom2State() {\n"
    text = path.read_text(encoding="utf-8")
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
    if "private boolean nom2PauseOverlayVisible()" not in text:
        if marker not in text:
            raise RuntimeError("Could not find NOM 2 state helper insertion point")
        path.write_text(text.replace(marker, helper + marker, 1), encoding="utf-8")

    # Screen-matched bottom controls:
    # normal gameplay -> one Pause button only
    # in-game pause overlay -> Select / Back
    # story/ending confirmation states -> Confirm only
    # normal menus -> Select / Back
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
\t\t\t\t// Gameplay itself needs no action button: tapping anywhere jumps.
\t\t\t\tnom2OkButton.setText("일시정지");
\t\t\t} else if (pauseOverlay) {
\t\t\t\tnom2OkButton.setText("선택");
\t\t\t\tnom2BackButton.setText("뒤로");
\t\t\t\tnom2BackButton.setVisibility(View.VISIBLE);
\t\t\t} else if (state >= 31 && state <= 35) {
\t\t\t\t// Story/ending screens draw a centered OK prompt.
\t\t\t\tnom2OkButton.setText("확인");
\t\t\t} else if (state >= 36 && state <= 40) {
\t\t\t\t// The online leaderboard is disabled by disable_leaderboard.py;
\t\t\t\t// hide misleading controls during the very short bypass transition.
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

    # Rewrite native button actions to match the labels above.
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
\t\t\t\t\t// Dedicated pause button. Gameplay action/jump is touch-anywhere.
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

    # Make the single gameplay Pause button visually fill the bottom bar.
    # Hidden weighted siblings automatically leave the visible button full-width.
    text = path.read_text(encoding="utf-8")
    if "NOM2_FINAL_S10_CONTROLS" not in text:
        path.write_text(text.replace(
            "\t\tprivate LinearLayout nom2ButtonBar;\n",
            "\t\t// NOM2_FINAL_S10_CONTROLS\n\t\tprivate LinearLayout nom2ButtonBar;\n",
            1,
        ), encoding="utf-8")


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
