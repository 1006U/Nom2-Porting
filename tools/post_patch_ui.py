#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


PORT_VERSION_CODE = 102
PORT_VERSION_NAME = "1.0.43-port2-ko-s10"


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

    marker = "\t\tpublic ViewCallbacks(View view) {\n"
    methods = """\t\tprivate LinearLayout nom2ButtonBar;
\t\tprivate Button nom2OkButton;
\t\tprivate Button nom2MenuButton;
\t\tprivate Button nom2BackButton;

\t\tprivate int nom2Dp(float value) {
\t\t\treturn Math.round(TypedValue.applyDimension(
\t\t\t\t\tTypedValue.COMPLEX_UNIT_DIP,
\t\t\t\t\tvalue,
\t\t\t\t\tmView.getResources().getDisplayMetrics()));
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
\t\t\tstates.addState(
\t\t\t\t\tnew int[] { android.R.attr.state_pressed },
\t\t\t\t\tnom2ButtonShape(android.graphics.Color.rgb(82, 82, 82)));
\t\t\tstates.addState(
\t\t\t\t\tnew int[] {},
\t\t\t\t\tnom2ButtonShape(android.graphics.Color.rgb(42, 42, 42)));
\t\t\treturn states;
\t\t}

\t\tprivate void styleNom2Button(Button button) {
\t\t\tbutton.setAllCaps(false);
\t\t\tbutton.setTextColor(android.graphics.Color.WHITE);
\t\t\tbutton.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
\t\t\tbutton.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
\t\t\tbutton.setGravity(Gravity.CENTER);
\t\t\tbutton.setPadding(nom2Dp(4), 0, nom2Dp(4), 0);
\t\t\tbutton.setMinHeight(0);
\t\t\tbutton.setMinimumHeight(0);
\t\t\tbutton.setFocusable(false);
\t\t\tbutton.setFocusableInTouchMode(false);
\t\t\tbutton.setBackground(nom2ButtonBackground());
\t\t}

\t\tprivate void attachNom2ButtonBar(LinearLayout parent) {
\t\t\tif (nom2ButtonBar != null) {
\t\t\t\treturn;
\t\t\t}

\t\t\tnom2ButtonBar = new LinearLayout(mView.getContext());
\t\t\tnom2ButtonBar.setOrientation(LinearLayout.HORIZONTAL);
\t\t\tnom2ButtonBar.setGravity(Gravity.CENTER);
\t\t\tnom2ButtonBar.setBackgroundColor(android.graphics.Color.BLACK);
\t\t\tnom2ButtonBar.setPadding(nom2Dp(5), nom2Dp(5), nom2Dp(5), nom2Dp(5));

\t\t\tnom2OkButton = new Button(mView.getContext());
\t\t\tnom2MenuButton = new Button(mView.getContext());
\t\t\tnom2BackButton = new Button(mView.getContext());
\t\t\tstyleNom2Button(nom2OkButton);
\t\t\tstyleNom2Button(nom2MenuButton);
\t\t\tstyleNom2Button(nom2BackButton);

\t\t\tnom2OkButton.setText("확인");
\t\t\tnom2MenuButton.setText("일시정지");
\t\t\tnom2BackButton.setText("뒤로");

\t\t\t// Keep each original MIDP control available explicitly. NOM 2 uses
\t\t\t// numeric 5 for OK/action and the two soft keys for pause/menu/back.
\t\t\tnom2OkButton.setOnClickListener(v -> fireNom2Key(KEY_NUM5));
\t\t\tnom2MenuButton.setOnClickListener(v -> fireNom2Key(KEY_SOFT_LEFT));
\t\t\tnom2BackButton.setOnClickListener(v -> fireNom2Key(KEY_SOFT_RIGHT));

\t\t\tLinearLayout.LayoutParams params =
\t\t\t\t\tnew LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1);
\t\t\tLinearLayout.LayoutParams middleParams =
\t\t\t\t\tnew LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1);
\t\t\tLinearLayout.LayoutParams rightParams =
\t\t\t\t\tnew LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1);
\t\t\tparams.setMargins(0, 0, nom2Dp(2), 0);
\t\t\tmiddleParams.setMargins(nom2Dp(2), 0, nom2Dp(2), 0);
\t\t\trightParams.setMargins(nom2Dp(2), 0, 0, 0);

\t\t\tnom2ButtonBar.addView(nom2OkButton, params);
\t\t\tnom2ButtonBar.addView(nom2MenuButton, middleParams);
\t\t\tnom2ButtonBar.addView(nom2BackButton, rightParams);

\t\t\tboolean landscape =
\t\t\t\t\tmView.getResources().getConfiguration().orientation
\t\t\t\t\t\t\t== android.content.res.Configuration.ORIENTATION_LANDSCAPE;
\t\t\tint barHeight = nom2Dp(landscape ? 42 : 54);
\t\t\tparent.addView(nom2ButtonBar,
\t\t\t\t\tnew LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, barHeight));
\t\t}

""" + marker
    replace_once(path, marker, methods, "NOM 2 visible native bottom buttons")

    replace_once(
        path,
        "\t\t\tfloat threshold = Math.max(40.0f,\n\t\t\t\t\tMath.min(mView.getWidth(), mView.getHeight()) * 0.08f);\n",
        "\t\t\tfloat threshold = nom2Dp(18);\n",
        "Galaxy S10 touch/swipe threshold",
    )

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
    replace_once(path, view_old, view_new, "NOM 2 game view plus bottom button layout")


def find_icon_source(root: Path) -> Path:
    # Exact local paths first. The user's current file is overlay/icon.jpg.
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

    # Do not crop, redraw, recolor, or alter the source composition. Only scale
    # proportionally into Android's square launcher slots and fill unavoidable
    # empty space with the source image's own corner/background color.
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
            path = folder / filename
            if path.exists():
                path.unlink()

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
    print("Applied Galaxy S10 UI fixes: 3 visible buttons, tuned touch, original icon mipmaps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
