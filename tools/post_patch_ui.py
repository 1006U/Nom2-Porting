#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


PORT_VERSION_CODE = 103
PORT_VERSION_NAME = "1.0.43-port3-ko-s10"


def replace_once(path: Path, old: str, new: str, description: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Could not apply {description}: expected text not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_build_identity(engine: Path) -> None:
    path = engine / "app" / "build.gradle"
    old = """            applicationId \"com.u1006.nom2\"
            versionName \"1.0.43-port1\"
"""
    new = f"""            applicationId \"com.u1006.nom2\"
            versionCode {PORT_VERSION_CODE}
            versionName \"{PORT_VERSION_NAME}\"
"""
    replace_once(path, old, new, "NOM 2 visible port build identity")


def patch_canvas(engine: Path) -> None:
    path = engine / "app" / "src" / "main" / "java" / "javax" / "microedition" / "lcdui" / "Canvas.java"

    replace_once(
        path,
        "import android.widget.LinearLayout;\nimport android.widget.PopupWindow;\n",
        "import android.widget.Button;\nimport android.widget.LinearLayout;\nimport android.widget.PopupWindow;\n",
        "NOM 2 native button import",
    )

    # Replace the initial generic tap/swipe handler before adding the state-aware
    # helpers below. This makes the soft-key labels drawn by NOM 2 itself truly
    # touchable and opens a native text editor on the leaderboard name screen.
    text = path.read_text(encoding="utf-8")
    touch_pattern = re.compile(
        r"\t\tprivate boolean handleNom2Touch\(MotionEvent event\) \{.*?"
        r"\n\t\t\}\n\n\t\tpublic ViewCallbacks\(View view\) \{",
        re.S,
    )
    touch_new = r'''\t\tprivate boolean handleNom2Touch(MotionEvent event) {
\t\t\tint action = event.getActionMasked();

\t\t\tif (action == MotionEvent.ACTION_DOWN && event.getPointerCount() == 1) {
\t\t\t\tnom2TouchX = event.getX();
\t\t\t\tnom2TouchY = event.getY();
\t\t\t\tnom2TouchActive = true;
\t\t\t\tnom2SoftKey = 0;

\t\t\t\tint state = nom2State();
\t\t\t\tfloat gameBottom = onY + onHeight;
\t\t\t\tfloat softKeyTop = onY + onHeight * 0.84f;
\t\t\t\tboolean menuSoftKeyStrip = state != 0 && state != 20
\t\t\t\t\t\t&& nom2TouchY >= softKeyTop && nom2TouchY <= gameBottom;

\t\t\t\t// NOM 2 draws its left/right soft-key captions at the bottom edge of
\t\t\t\t// the 176x208 canvas. Make those captions touchable too. The lower
\t\t\t\t// letterbox keeps the same behavior for tall Galaxy displays.
\t\t\t\tif (nom2TouchY > gameBottom || menuSoftKeyStrip) {
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

\t\t\tif (nom2SoftKey != 0) {
\t\t\t\tint key = nom2SoftKey;
\t\t\t\tnom2SoftKey = 0;
\t\t\t\tfireNom2Key(key);
\t\t\t\treturn true;
\t\t\t}

\t\t\tfloat dx = event.getX() - nom2TouchX;
\t\t\tfloat dy = event.getY() - nom2TouchY;
\t\t\tfloat threshold = nom2Dp(18);
\t\t\tint state = nom2State();

\t\t\t// State 36 is NOM 2's leaderboard-name editor. Numeric key 5 would
\t\t\t// type J/K/L, which is why arbitrary taps previously produced hidden
\t\t\t// letters. A normal tap now opens an Android text field instead.
\t\t\tif (state == 36 && Math.abs(dx) < threshold && Math.abs(dy) < threshold) {
\t\t\t\tshowNom2NameEditor();
\t\t\t\treturn true;
\t\t\t}

\t\t\tif (Math.abs(dx) >= threshold || Math.abs(dy) >= threshold) {
\t\t\t\tif (Math.abs(dx) > Math.abs(dy)) {
\t\t\t\t\tfireNom2Key(dx < 0 ? KEY_NUM4 : KEY_NUM6);
\t\t\t\t} else {
\t\t\t\t\tfireNom2Key(dy < 0 ? KEY_NUM2 : KEY_NUM8);
\t\t\t\t}
\t\t\t} else if (state != 37) {
\t\t\t\t// On the yes/no score-upload screen (state 37), only the explicit
\t\t\t\t// soft-key choices should act. Elsewhere a tap is the normal action.
\t\t\t\tfireNom2Key(KEY_NUM5);
\t\t\t}
\t\t\treturn true;
\t\t}

\t\tpublic ViewCallbacks(View view) {'''
    text2, count = touch_pattern.subn(touch_new, text, count=1)
    if count != 1:
        raise RuntimeError("Could not replace NOM 2 state-aware touch handler")
    path.write_text(text2, encoding="utf-8")

    marker = "\t\tpublic ViewCallbacks(View view) {\n"
    methods = """\t\tprivate LinearLayout nom2ButtonBar;
\t\tprivate Button nom2OkButton;
\t\tprivate Button nom2MenuButton;
\t\tprivate Button nom2BackButton;
\t\tprivate int nom2LastButtonState = Integer.MIN_VALUE;

\t\tprivate final Runnable nom2ButtonUpdater = new Runnable() {
\t\t\t@Override
\t\t\tpublic void run() {
\t\t\t\tif (nom2ButtonBar == null) {
\t\t\t\t\treturn;
\t\t\t\t}
\t\t\t\trefreshNom2Buttons();
\t\t\t\tmView.postDelayed(this, 120);
\t\t\t}
\t\t};

\t\tprivate int nom2Dp(float value) {
\t\t\treturn Math.round(TypedValue.applyDimension(
\t\t\t\t\tTypedValue.COMPLEX_UNIT_DIP,
\t\t\t\t\tvalue,
\t\t\t\t\tmView.getResources().getDisplayMetrics()));
\t\t}

\t\tprivate int nom2State() {
\t\t\ttry {
\t\t\t\tjava.lang.reflect.Field field = Canvas.this.getClass().getDeclaredField("W");
\t\t\t\tfield.setAccessible(true);
\t\t\t\treturn field.getInt(null);
\t\t\t} catch (Throwable ignored) {
\t\t\t\treturn -1;
\t\t\t}
\t\t}

\t\tprivate Object nom2NameInput() {
\t\t\ttry {
\t\t\t\tjava.lang.reflect.Field field = Canvas.this.getClass().getDeclaredField("de");
\t\t\t\tfield.setAccessible(true);
\t\t\t\treturn field.get(Canvas.this);
\t\t\t} catch (Throwable ignored) {
\t\t\t\treturn null;
\t\t\t}
\t\t}

\t\tprivate String nom2CurrentName() {
\t\t\ttry {
\t\t\t\tObject input = nom2NameInput();
\t\t\t\tif (input == null) return "";
\t\t\t\tjava.lang.reflect.Field field = input.getClass().getDeclaredField("a");
\t\t\t\tfield.setAccessible(true);
\t\t\t\tObject value = field.get(input);
\t\t\t\treturn value == null ? "" : value.toString();
\t\t\t} catch (Throwable ignored) {
\t\t\t\treturn "";
\t\t\t}
\t\t}

\t\tprivate void nom2SetName(String raw) {
\t\t\tif (raw == null) raw = "";
\t\t\tString upper = raw.toUpperCase(java.util.Locale.US);
\t\t\tStringBuilder clean = new StringBuilder();
\t\t\tfor (int p = 0; p < upper.length() && clean.length() < 12; p++) {
\t\t\t\tchar ch = upper.charAt(p);
\t\t\t\tif ((ch >= 'A' && ch <= 'Z') || (ch >= '0' && ch <= '9')) {
\t\t\t\t\tclean.append(ch);
\t\t\t\t}
\t\t\t}
\t\t\ttry {
\t\t\t\tObject input = nom2NameInput();
\t\t\t\tif (input == null) return;
\t\t\t\tjava.lang.reflect.Field bufferField = input.getClass().getDeclaredField("a");
\t\t\t\tbufferField.setAccessible(true);
\t\t\t\tStringBuffer buffer = (StringBuffer) bufferField.get(input);
\t\t\t\tbuffer.setLength(0);
\t\t\t\tbuffer.append(clean.toString());
\t\t\t\ttry {
\t\t\t\t\tjava.lang.reflect.Field cursor = input.getClass().getDeclaredField("g");
\t\t\t\t\tcursor.setAccessible(true);
\t\t\t\t\tcursor.setInt(input, clean.length());
\t\t\t\t} catch (Throwable ignored) {}
\t\t\t\ttry {
\t\t\t\t\tjava.lang.reflect.Field cycle = input.getClass().getDeclaredField("d");
\t\t\t\t\tcycle.setAccessible(true);
\t\t\t\t\tcycle.setInt(input, 0);
\t\t\t\t} catch (Throwable ignored) {}
\t\t\t\tCanvas.this.repaint();
\t\t\t} catch (Throwable error) {
\t\t\t\tLog.w(TAG, "Could not write NOM 2 leaderboard name", error);
\t\t\t}
\t\t}

\t\tprivate void showNom2NameEditor() {
\t\t\tif (nom2State() != 36) return;
\t\t\tfinal android.widget.EditText editor = new android.widget.EditText(mView.getContext());
\t\t\teditor.setSingleLine(true);
\t\t\teditor.setHint("영문/숫자 4~12자");
\t\t\teditor.setText(nom2CurrentName());
\t\t\teditor.setSelection(editor.getText().length());
\t\t\teditor.setInputType(android.text.InputType.TYPE_CLASS_TEXT
\t\t\t\t\t| android.text.InputType.TYPE_TEXT_FLAG_CAP_CHARACTERS);
\t\t\teditor.setFilters(new android.text.InputFilter[] {
\t\t\t\t\tnew android.text.InputFilter.LengthFilter(12)
\t\t\t});
\t\t\teditor.setKeyListener(android.text.method.DigitsKeyListener.getInstance(
\t\t\t\t\t"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"));

\t\t\tfinal android.app.AlertDialog dialog = new android.app.AlertDialog.Builder(mView.getContext())
\t\t\t\t\t.setTitle("리더보드 이름 입력")
\t\t\t\t\t.setMessage("영문 또는 숫자 4~12자")
\t\t\t\t\t.setView(editor)
\t\t\t\t\t.setPositiveButton("적용", (whichDialog, which) -> {
\t\t\t\t\t\tString value = editor.getText().toString();
\t\t\t\t\t\tnom2SetName(value);
\t\t\t\t\t\tif (nom2CurrentName().length() < 4) {
\t\t\t\t\t\t\tandroid.widget.Toast.makeText(mView.getContext(),
\t\t\t\t\t\t\t\t\t"이름은 4~12자로 입력하세요.",
\t\t\t\t\t\t\t\t\tandroid.widget.Toast.LENGTH_SHORT).show();
\t\t\t\t\t\t}
\t\t\t\t\t})
\t\t\t\t\t.setNegativeButton("취소", null)
\t\t\t\t\t.create();
\t\t\tdialog.setOnShowListener(ignored -> {
\t\t\t\teditor.requestFocus();
\t\t\t\tif (dialog.getWindow() != null) {
\t\t\t\t\tdialog.getWindow().setSoftInputMode(
\t\t\t\t\t\t\tandroid.view.WindowManager.LayoutParams.SOFT_INPUT_STATE_ALWAYS_VISIBLE);
\t\t\t\t}
\t\t\t});
\t\t\tdialog.show();
\t\t}

\t\tprivate android.graphics.drawable.GradientDrawable nom2ButtonShape(int color) {
\t\t\tandroid.graphics.drawable.GradientDrawable shape =
\t\t\t\t\tnew android.graphics.drawable.GradientDrawable();
\t\t\tshape.setShape(android.graphics.drawable.GradientDrawable.RECTANGLE);
\t\t\tshape.setColor(color);
\t\t\tshape.setStroke(nom2Dp(1), android.graphics.Color.rgb(95, 95, 95));
\t\t\tshape.setCornerRadius(nom2Dp(4));
\t\t\treturn shape;
\t\t}

\t\tprivate android.graphics.drawable.StateListDrawable nom2ButtonBackground() {
\t\t\tandroid.graphics.drawable.StateListDrawable states =
\t\t\t\t\tnew android.graphics.drawable.StateListDrawable();
\t\t\tstates.addState(new int[] { android.R.attr.state_pressed },
\t\t\t\t\tnom2ButtonShape(android.graphics.Color.rgb(82, 82, 82)));
\t\t\tstates.addState(new int[] {},
\t\t\t\t\tnom2ButtonShape(android.graphics.Color.rgb(42, 42, 42)));
\t\t\treturn states;
\t\t}

\t\tprivate void styleNom2Button(Button button) {
\t\t\tbutton.setAllCaps(false);
\t\t\tbutton.setTextColor(android.graphics.Color.WHITE);
\t\t\tbutton.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
\t\t\tbutton.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
\t\t\tbutton.setGravity(Gravity.CENTER);
\t\t\tbutton.setPadding(nom2Dp(3), 0, nom2Dp(3), 0);
\t\t\tbutton.setMinHeight(0);
\t\t\tbutton.setMinimumHeight(0);
\t\t\tbutton.setFocusable(false);
\t\t\tbutton.setFocusableInTouchMode(false);
\t\t\tbutton.setBackground(nom2ButtonBackground());
\t\t}

\t\tprivate void refreshNom2Buttons() {
\t\t\tif (nom2ButtonBar == null) return;
\t\t\tint state = nom2State();
\t\t\tif (state == nom2LastButtonState) return;
\t\t\tnom2LastButtonState = state;

\t\t\tnom2OkButton.setVisibility(View.VISIBLE);
\t\t\tnom2MenuButton.setVisibility(View.GONE);
\t\t\tnom2BackButton.setVisibility(View.VISIBLE);

\t\t\tif (state == 37) {
\t\t\t\tnom2OkButton.setText("예");
\t\t\t\tnom2BackButton.setText("아니오");
\t\t\t} else if (state == 36) {
\t\t\t\tnom2OkButton.setText("선택");
\t\t\t\tnom2MenuButton.setText("이름입력");
\t\t\t\tnom2MenuButton.setVisibility(View.VISIBLE);
\t\t\t\tnom2BackButton.setText("뒤로");
\t\t\t} else if (state == 0 || state == 20) {
\t\t\t\tnom2OkButton.setText("액션");
\t\t\t\tnom2MenuButton.setText("일시정지");
\t\t\t\tnom2MenuButton.setVisibility(View.VISIBLE);
\t\t\t\tnom2BackButton.setVisibility(View.GONE);
\t\t\t} else if (state == 38 || state == 39 || state == 40) {
\t\t\t\tnom2OkButton.setText("확인");
\t\t\t\tnom2BackButton.setText("뒤로");
\t\t\t} else {
\t\t\t\tnom2OkButton.setText("선택");
\t\t\t\tnom2BackButton.setText("뒤로");
\t\t\t}
\t\t}

\t\tprivate void attachNom2ButtonBar(LinearLayout parent) {
\t\t\tif (nom2ButtonBar != null) return;

\t\t\tnom2ButtonBar = new LinearLayout(mView.getContext());
\t\t\tnom2ButtonBar.setOrientation(LinearLayout.HORIZONTAL);
\t\t\tnom2ButtonBar.setGravity(Gravity.CENTER);
\t\t\tnom2ButtonBar.setBackgroundColor(android.graphics.Color.BLACK);
\t\t\tnom2ButtonBar.setPadding(nom2Dp(4), nom2Dp(4), nom2Dp(4), nom2Dp(4));

\t\t\tnom2OkButton = new Button(mView.getContext());
\t\t\tnom2MenuButton = new Button(mView.getContext());
\t\t\tnom2BackButton = new Button(mView.getContext());
\t\t\tstyleNom2Button(nom2OkButton);
\t\t\tstyleNom2Button(nom2MenuButton);
\t\t\tstyleNom2Button(nom2BackButton);

\t\t\tnom2OkButton.setOnClickListener(v -> {
\t\t\t\tint state = nom2State();
\t\t\t\tif (state == 0 || state == 20) fireNom2Key(KEY_NUM5);
\t\t\t\telse fireNom2Key(KEY_SOFT_LEFT);
\t\t\t});
\t\t\tnom2MenuButton.setOnClickListener(v -> {
\t\t\t\tif (nom2State() == 36) showNom2NameEditor();
\t\t\t\telse fireNom2Key(KEY_SOFT_LEFT);
\t\t\t});
\t\t\tnom2BackButton.setOnClickListener(v -> fireNom2Key(KEY_SOFT_RIGHT));

\t\t\tLinearLayout.LayoutParams leftParams =
\t\t\t\t\tnew LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1);
\t\t\tLinearLayout.LayoutParams middleParams =
\t\t\t\t\tnew LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1);
\t\t\tLinearLayout.LayoutParams rightParams =
\t\t\t\t\tnew LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1);
\t\t\tleftParams.setMargins(0, 0, nom2Dp(2), 0);
\t\t\tmiddleParams.setMargins(nom2Dp(2), 0, nom2Dp(2), 0);
\t\t\trightParams.setMargins(nom2Dp(2), 0, 0, 0);
\t\t\tnom2ButtonBar.addView(nom2OkButton, leftParams);
\t\t\tnom2ButtonBar.addView(nom2MenuButton, middleParams);
\t\t\tnom2ButtonBar.addView(nom2BackButton, rightParams);

\t\t\tboolean landscape = mView.getResources().getConfiguration().orientation
\t\t\t\t\t== android.content.res.Configuration.ORIENTATION_LANDSCAPE;
\t\t\tint barHeight = nom2Dp(landscape ? 40 : 48);
\t\t\tparent.addView(nom2ButtonBar,
\t\t\t\t\tnew LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, barHeight));
\t\t\trefreshNom2Buttons();
\t\t\tmView.removeCallbacks(nom2ButtonUpdater);
\t\t\tmView.post(nom2ButtonUpdater);
\t\t}

""" + marker
    replace_once(path, marker, methods, "NOM 2 state-aware bottom controls")

    view_old = """\t\t\tinnerView.setOnGenericMotionListener(callback);
\t\t\tinnerView.setFocusableInTouchMode(true);
\t\t\tlayout.addView(innerView);
\t\t\tinnerView.requestFocus();
"""
    view_new = """\t\t\tinnerView.setOnGenericMotionListener(callback);
\t\t\tinnerView.setFocusableInTouchMode(true);
\t\t\tinnerView.setLayoutParams(new LinearLayout.LayoutParams(
\t\t\t\t\tViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
\t\t\tlayout.addView(innerView);
\t\t\tcallback.attachNom2ButtonBar(layout);
\t\t\tinnerView.requestFocus();
"""
    replace_once(path, view_old, view_new, "NOM 2 game view plus state-aware button layout")


def find_icon_source(root: Path) -> Path:
    candidates = [
        root / "overlay" / "icon.jpg",
        root / "overlay" / "icon.jpeg",
        root / "overlay" / "icon.png",
        root / "branding" / "app_icon.png",
        root / "branding" / "app_icon.jpg",
        root / "branding" / "app_icon.jpeg",
        root / "branding" / "icon.png",
        root / "branding" / "icon.jpg",
        root / "branding" / "icon.jpeg",
        root / "app_icon.png",
        root / "app_icon.jpg",
        root / "app_icon.jpeg",
        root / "icon.png",
        root / "icon.jpg",
        root / "icon.jpeg",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    for directory in (root / "overlay", root / "branding", root):
        if directory.is_dir():
            for candidate in sorted(directory.iterdir()):
                if candidate.is_file() and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                    return candidate

    raise FileNotFoundError(
        "Original NOM 2 icon was not found. Put the untouched artwork at overlay/icon.jpg "
        "(current expected path), overlay/icon.png, or branding/app_icon.png."
    )


def patch_icon(root: Path, engine: Path) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required for launcher icon mipmaps") from exc

    source = find_icon_source(root)
    original = Image.open(source).convert("RGBA")
    res_dir = engine / "app" / "src" / "main" / "res"
    sizes = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }

    background = original.getpixel((0, 0))
    if background[3] == 0:
        background = (255, 255, 255, 255)
    resampling = getattr(Image, "Resampling", Image).LANCZOS

    for folder, px in sizes.items():
        out_dir = res_dir / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        scale = min(px / original.width, px / original.height)
        new_size = (
            max(1, int(round(original.width * scale))),
            max(1, int(round(original.height * scale))),
        )
        fitted = original.resize(new_size, resampling)
        canvas = Image.new("RGBA", (px, px), background)
        x = (px - fitted.width) // 2
        y = (px - fitted.height) // 2
        canvas.paste(fitted, (x, y), fitted)
        canvas.save(out_dir / "ic_launcher.png")
        canvas.save(out_dir / "ic_launcher_round.png")

    for folder in (res_dir / "mipmap-anydpi", res_dir / "mipmap-anydpi-v26"):
        for filename in ("ic_launcher.xml", "ic_launcher_round.xml"):
            icon_xml = folder / filename
            if icon_xml.exists():
                icon_xml.unlink()

    manifest = engine / "app" / "src" / "main" / "AndroidManifest.xml"
    text = manifest.read_text(encoding="utf-8")
    text = re.sub(r'android:icon="[^"]+"', 'android:icon="@mipmap/ic_launcher"', text, count=1)
    text = re.sub(
        r'android:roundIcon="[^"]+"',
        'android:roundIcon="@mipmap/ic_launcher_round"',
        text,
        count=1,
    )
    manifest.write_text(text, encoding="utf-8")
    print(f"Original launcher artwork: {source}")
    print(f"Original artwork size: {original.width}x{original.height}")
    print("Icon processing: proportional mipmap resize only; no crop/redraw/recolor")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Galaxy S10 NOM 2 UI/input/icon fixes")
    parser.add_argument("--engine", default="engine")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    engine = (root / args.engine).resolve() if not Path(args.engine).is_absolute() else Path(args.engine)

    patch_build_identity(engine)
    patch_canvas(engine)
    patch_icon(root, engine)

    print(f"NOM 2 port build: {PORT_VERSION_NAME} (versionCode {PORT_VERSION_CODE})")
    print("Applied Galaxy S10 UI fixes: state-aware buttons, touchable softkeys, native name input")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
