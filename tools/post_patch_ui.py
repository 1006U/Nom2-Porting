#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


def replace_once(path: Path, old: str, new: str, description: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Could not apply {description}: expected text not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


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
\t\tprivate Button nom2LeftButton;
\t\tprivate Button nom2RightButton;

\t\tprivate int nom2Dp(float value) {
\t\t\treturn Math.round(TypedValue.applyDimension(
\t\t\t\t\tTypedValue.COMPLEX_UNIT_DIP,
\t\t\t\t\tvalue,
\t\t\t\t\tmView.getResources().getDisplayMetrics()));
\t\t}

\t\tprivate void styleNom2Button(Button button) {
\t\t\tbutton.setAllCaps(false);
\t\t\tbutton.setTextColor(android.graphics.Color.WHITE);
\t\t\tbutton.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15);
\t\t\tbutton.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
\t\t\tbutton.setGravity(Gravity.CENTER);
\t\t\tbutton.setPadding(nom2Dp(8), 0, nom2Dp(8), 0);
\t\t\tbutton.setMinHeight(0);
\t\t\tbutton.setMinimumHeight(0);
\t\t\tbutton.setFocusable(false);
\t\t\tbutton.setFocusableInTouchMode(false);
\t\t\tbutton.setBackgroundColor(android.graphics.Color.rgb(44, 44, 44));
\t\t}

\t\tprivate void attachNom2ButtonBar(LinearLayout parent) {
\t\t\tif (nom2ButtonBar != null) {
\t\t\t\treturn;
\t\t\t}
\t\t\tnom2ButtonBar = new LinearLayout(mView.getContext());
\t\t\tnom2ButtonBar.setOrientation(LinearLayout.HORIZONTAL);
\t\t\tnom2ButtonBar.setGravity(Gravity.CENTER);
\t\t\tnom2ButtonBar.setBackgroundColor(android.graphics.Color.BLACK);
\t\t\tnom2ButtonBar.setPadding(nom2Dp(6), nom2Dp(5), nom2Dp(6), nom2Dp(5));

\t\t\tnom2LeftButton = new Button(mView.getContext());
\t\t\tnom2RightButton = new Button(mView.getContext());
\t\t\tstyleNom2Button(nom2LeftButton);
\t\t\tstyleNom2Button(nom2RightButton);
\t\t\tnom2LeftButton.setText("확인 / 일시정지");
\t\t\tnom2RightButton.setText("뒤로");
\t\t\tnom2LeftButton.setOnClickListener(v -> fireNom2Key(KEY_SOFT_LEFT));
\t\t\tnom2RightButton.setOnClickListener(v -> fireNom2Key(KEY_SOFT_RIGHT));

\t\t\tLinearLayout.LayoutParams leftParams =
\t\t\t\t\tnew LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1);
\t\t\tleftParams.setMargins(0, 0, nom2Dp(3), 0);
\t\t\tLinearLayout.LayoutParams rightParams =
\t\t\t\t\tnew LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.MATCH_PARENT, 1);
\t\t\trightParams.setMargins(nom2Dp(3), 0, 0, 0);
\t\t\tnom2ButtonBar.addView(nom2LeftButton, leftParams);
\t\t\tnom2ButtonBar.addView(nom2RightButton, rightParams);

\t\t\tboolean landscape =
\t\t\t\t\tmView.getResources().getConfiguration().orientation
\t\t\t\t\t\t\t== android.content.res.Configuration.ORIENTATION_LANDSCAPE;
\t\t\tint barHeight = nom2Dp(landscape ? 44 : 56);
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
    candidates = [
        root / "branding" / "app_icon.png",
        root / "branding" / "app_icon.jpg",
        root / "branding" / "app_icon.jpeg",
        root / "branding" / "icon.png",
        root / "branding" / "icon.jpg",
        root / "overlay" / "icon.png",
        root / "app_icon.png",
        root / "icon.png",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate

    branding = root / "branding"
    if branding.is_dir():
        for candidate in sorted(branding.iterdir()):
            if candidate.is_file() and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                return candidate

    raise FileNotFoundError(
        "Original NOM 2 icon was not found. Put the untouched image at "
        "branding/app_icon.png (recommended), branding/app_icon.jpg, overlay/icon.png, "
        "or app_icon.png."
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
    print("Icon processing: aspect-ratio-preserving mipmap resize only; no crop/redraw/recolor")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Galaxy S10 NOM 2 UI/input/icon fixes")
    parser.add_argument("--engine", default="engine")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    engine = (root / args.engine).resolve() if not Path(args.engine).is_absolute() else Path(args.engine)
    patch_canvas(engine)
    patch_icon(root, engine)
    print("Applied Galaxy S10 UI fixes: visible buttons, tuned touch, original icon mipmaps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
