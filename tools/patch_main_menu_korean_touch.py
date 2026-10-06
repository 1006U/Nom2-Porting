#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


PORT_VERSION_CODE = 108
PORT_VERSION_NAME = "1.0.43-port8-ko-s10"
PORT_REVISION = "nom2-port8-ko-s10-r7"


def insert_before(text: str, needle: str, block: str, description: str) -> str:
    if block.strip().splitlines()[0].strip() in text:
        return text
    pos = text.find(needle)
    if pos < 0:
        raise RuntimeError(f"Could not find {description}: {needle}")
    line_start = text.rfind("\n", 0, pos) + 1
    return text[:line_start] + block + text[line_start:]


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

    helpers = """\t\t// NOM2_KOREAN_MAIN_MENU_TOUCH
\t\tprivate PopupWindow nom2MainMenuPopup;
\t\tprivate long nom2MainMenuPopupSuppressedUntil;

\t\tprivate String nom2MainMenuLabel(int item) {
\t\t\tswitch (item) {
\t\t\t\tcase 1: return "이어하기";
\t\t\t\tcase 2: return "새 게임";
\t\t\t\tcase 3: return "게임 방법";
\t\t\t\tcase 4: return "설정";
\t\t\t\tcase 5: return "리더보드 (사용 안 함)";
\t\t\t\tcase 6: return "게임 정보";
\t\t\t\tcase 7: return "더 많은 게임";
\t\t\t\tcase 8: return "우주 메시지";
\t\t\t\tcase 9: return "종료";
\t\t\t\tdefault: return "메뉴";
\t\t\t}
\t\t}

\t\tprivate void nom2DismissMainMenuOverlay() {
\t\t\tif (nom2MainMenuPopup != null) {
\t\t\t\ttry {
\t\t\t\t\tif (nom2MainMenuPopup.isShowing()) nom2MainMenuPopup.dismiss();
\t\t\t\t} catch (Throwable ignored) {}
\t\t\t\tnom2MainMenuPopup = null;
\t\t\t}
\t\t}

\t\tprivate void nom2ActivateMainMenuItem(int item) {
\t\t\tif (item < 1 || item > 9 || item == 5) return;
\t\t\tnom2MainMenuPopupSuppressedUntil = System.currentTimeMillis() + 500L;
\t\t\tnom2DismissMainMenuOverlay();
\t\t\tif (!nom2SetStaticInt("cm", item)) return;
\t\t\tCanvas.this.repaint();
\t\t\tfireNom2Key(KEY_NUM5);
\t\t}

\t\tprivate void nom2RefreshMainMenuOverlay() {
\t\t\tif (nom2State() != 3) {
\t\t\t\tnom2DismissMainMenuOverlay();
\t\t\t\treturn;
\t\t\t}
\t\t\tif (System.currentTimeMillis() < nom2MainMenuPopupSuppressedUntil) return;
\t\t\tif (nom2MainMenuPopup != null && nom2MainMenuPopup.isShowing()) return;

\t\t\tLinearLayout panel = new LinearLayout(mView.getContext());
\t\t\tpanel.setOrientation(LinearLayout.VERTICAL);
\t\t\tpanel.setGravity(Gravity.CENTER);
\t\t\tpanel.setPadding(nom2Dp(8), nom2Dp(6), nom2Dp(8), nom2Dp(8));
\t\t\tpanel.setBackgroundColor(android.graphics.Color.argb(242, 18, 18, 18));

\t\t\tandroid.widget.TextView title = new android.widget.TextView(mView.getContext());
\t\t\ttitle.setText("메인 메뉴");
\t\t\ttitle.setTextColor(android.graphics.Color.WHITE);
\t\t\ttitle.setTextSize(TypedValue.COMPLEX_UNIT_SP, 16);
\t\t\ttitle.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
\t\t\ttitle.setGravity(Gravity.CENTER);
\t\t\tpanel.addView(title, new LinearLayout.LayoutParams(
\t\t\t\t\tViewGroup.LayoutParams.MATCH_PARENT, nom2Dp(34)));

\t\t\tint selected = nom2StaticInt("cm", 1);
\t\t\tfor (int item = 1; item <= 9; item++) {
\t\t\t\tfinal int menuItem = item;
\t\t\t\tButton button = new Button(mView.getContext());
\t\t\t\tbutton.setAllCaps(false);
\t\t\t\tbutton.setText(nom2MainMenuLabel(item));
\t\t\t\tbutton.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
\t\t\t\tbutton.setTextColor(item == 5
\t\t\t\t\t\t? android.graphics.Color.rgb(145, 145, 145)
\t\t\t\t\t\t: android.graphics.Color.WHITE);
\t\t\t\tbutton.setGravity(Gravity.CENTER);
\t\t\t\tbutton.setPadding(nom2Dp(3), 0, nom2Dp(3), 0);
\t\t\t\tbutton.setMinHeight(0);
\t\t\t\tbutton.setMinimumHeight(0);
\t\t\t\tbutton.setBackgroundColor(item == selected
\t\t\t\t\t\t? android.graphics.Color.rgb(76, 76, 76)
\t\t\t\t\t\t: android.graphics.Color.rgb(34, 34, 34));
\t\t\t\tbutton.setEnabled(item != 5);
\t\t\t\tbutton.setOnClickListener(v -> nom2ActivateMainMenuItem(menuItem));
\t\t\t\tLinearLayout.LayoutParams row = new LinearLayout.LayoutParams(
\t\t\t\t\t\tViewGroup.LayoutParams.MATCH_PARENT, nom2Dp(34));
\t\t\t\trow.setMargins(0, nom2Dp(1), 0, nom2Dp(1));
\t\t\t\tpanel.addView(button, row);
\t\t\t}

\t\t\tnom2MainMenuPopup = new PopupWindow(
\t\t\t\t\tpanel,
\t\t\t\t\tnom2Dp(224),
\t\t\t\t\tViewGroup.LayoutParams.WRAP_CONTENT,
\t\t\t\t\tfalse);
\t\t\tnom2MainMenuPopup.setTouchable(true);
\t\t\tnom2MainMenuPopup.setOutsideTouchable(false);
\t\t\tnom2MainMenuPopup.setClippingEnabled(false);
\t\t\tnom2MainMenuPopup.setBackgroundDrawable(
\t\t\t\t\tnew android.graphics.drawable.ColorDrawable(android.graphics.Color.TRANSPARENT));
\t\t\tnom2MainMenuPopup.showAtLocation(mView, Gravity.CENTER, 0, -nom2Dp(12));
\t\t}

\t\tprivate int nom2MainMenuSpriteHeight() {
\t\t\ttry {
\t\t\t\tjava.lang.reflect.Field field = nom2FindRuntimeField("ff");
\t\t\t\tif (field == null) return 10;
\t\t\t\tObject array = field.get(null);
\t\t\t\tif (array == null || java.lang.reflect.Array.getLength(array) <= 4) return 10;
\t\t\t\tObject image = java.lang.reflect.Array.get(array, 4);
\t\t\t\tif (image instanceof Image) return Math.max(1, ((Image) image).getHeight());
\t\t\t} catch (Throwable error) {
\t\t\t\tLog.w(TAG, "Could not read NOM 2 main menu sprite height", error);
\t\t\t}
\t\t\treturn 10;
\t\t}

\t\tprivate boolean nom2SelectMainMenuItem(float screenY) {
\t\t\tif (nom2State() != 3 || onHeight <= 0) return false;
\t\t\tif (screenY < onY || screenY > onY + onHeight) return false;

\t\t\tfloat logicalY = (screenY - onY) * 208.0f / (float) onHeight;
\t\t\tint spriteH = nom2MainMenuSpriteHeight();
\t\t\tfloat step = 6.0f + spriteH;
\t\t\tfloat top = (208.0f - 9.0f * step - spriteH) / 2.0f - 11.0f + 25.0f;
\t\t\tint co = nom2StaticInt("co", 1);
\t\t\tif (co < 1 || co > 9) co = 1;

\t\t\tint bestSlot = -1;
\t\t\tfloat bestDistance = Float.MAX_VALUE;
\t\t\tfor (int slot = 1; slot <= 9; slot++) {
\t\t\t\tfloat rowY = top + step * slot + 1.0f;
\t\t\t\tfloat distance = Math.abs(logicalY - rowY);
\t\t\t\tif (distance < bestDistance) {
\t\t\t\t\tbestDistance = distance;
\t\t\t\t\tbestSlot = slot;
\t\t\t\t}
\t\t\t}
\t\t\tif (bestSlot < 1 || bestDistance > Math.max(8.0f, step * 0.60f)) return false;
\t\t\tint item = co + bestSlot - 1;
\t\t\tif (item < 1 || item > 9 || item == 5) return false;
\t\t\tnom2ActivateMainMenuItem(item);
\t\t\treturn true;
\t\t}

"""
    text = insert_before(
        text,
        "private boolean nom2PauseOverlayVisible()",
        helpers,
        "main-menu helper insertion point",
    )

    marker = "\t\t\t// Pause screen: touching one of the six visible menu rows selects\n"
    if "nom2SelectMainMenuItem(event.getY())" not in text:
        pos = text.find(marker)
        if pos < 0:
            raise RuntimeError("Could not find pause-touch marker in handleNom2Touch")
        direct_touch = """\t\t\t// Main menu (W=3): tap the original visible row directly. The
\t\t\t// Korean PopupWindow below is the primary UI; this remains as a
\t\t\t// fallback when Android suppresses the popup on a device/rotation.
\t\t\tif (state == 3
\t\t\t\t\t&& Math.abs(dx) < threshold
\t\t\t\t\t&& Math.abs(dy) < threshold
\t\t\t\t\t&& nom2SelectMainMenuItem(event.getY())) {
\t\t\t\tnom2SoftKey = 0;
\t\t\t\treturn true;
\t\t\t}

"""
        text = text[:pos] + direct_touch + text[pos:]

    refresh_guard = "\t\t\tif (nom2ButtonBar == null) return;"
    refresh_add = refresh_guard + "\n\t\t\tnom2RefreshMainMenuOverlay();"
    if "nom2RefreshMainMenuOverlay();" not in text:
        if refresh_guard not in text:
            raise RuntimeError("Could not hook main-menu overlay into refreshNom2Buttons")
        text = text.replace(refresh_guard, refresh_add, 1)

    path.write_text(text, encoding="utf-8")

    final_text = path.read_text(encoding="utf-8")
    required = (
        "NOM2_KOREAN_MAIN_MENU_TOUCH",
        'case 1: return "이어하기"',
        'case 9: return "종료"',
        'nom2SetStaticInt("cm", item)',
        "nom2SelectMainMenuItem(event.getY())",
        "nom2RefreshMainMenuOverlay();",
        'nom2State() != 3',
    )
    missing = [token for token in required if token not in final_text]
    if missing:
        raise RuntimeError("Korean main-menu patch validation failed: " + ", ".join(missing))


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
    text2 = re.sub(
        r'private static final String PORT_REVISION = "nom2-port\d+-ko-s10-r\d+";',
        f'private static final String PORT_REVISION = "{PORT_REVISION}";',
        text,
        count=1,
    )
    if text2 == text and PORT_REVISION not in text:
        raise RuntimeError("Could not update NOM 2 port8 launcher revision")
    path.write_text(text2, encoding="utf-8")


def patch_build_identity(engine: Path) -> None:
    path = engine / "app" / "build.gradle"
    text = path.read_text(encoding="utf-8")
    text2 = re.sub(r"versionCode\s+107\b", f"versionCode {PORT_VERSION_CODE}", text, count=1)
    text2 = re.sub(
        r'versionName\s+"1\.0\.43-port7-ko-s10"',
        f'versionName "{PORT_VERSION_NAME}"',
        text2,
        count=1,
    )
    if text2 == text:
        if (
            f"versionCode {PORT_VERSION_CODE}" not in text
            or f'versionName "{PORT_VERSION_NAME}"' not in text
        ):
            raise RuntimeError("Could not set NOM 2 port8 build identity")
    else:
        path.write_text(text2, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Patch NOM 2 Korean/direct-touch main menu")
    parser.add_argument("--engine", default="engine")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    engine = (root / args.engine).resolve() if not Path(args.engine).is_absolute() else Path(args.engine)

    patch_canvas(engine)
    patch_launcher(engine)
    patch_build_identity(engine)

    print("NOM 2 Korean main menu patch applied:")
    print("  W=3 main menu: Korean Android overlay")
    print("  main menu: each item is directly touchable")
    print("  native cm=1..9 selection is used, then NUM5 activates the item")
    print("  leaderboard menu item is visibly disabled in the local-only port")
    print(f"  build: {PORT_VERSION_NAME} (versionCode {PORT_VERSION_CODE})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
