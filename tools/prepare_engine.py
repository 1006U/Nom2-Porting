#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path


EXPECTED_MAIN_CLASS = "Nom2"
EXPECTED_VERSION = "1.0.43"
EXPECTED_VENDOR = "GAMEVIL Inc./BiNPDA"


def read_manifest(jar_path: Path) -> dict[str, str]:
    with zipfile.ZipFile(jar_path) as zf:
        raw = zf.read("META-INF/MANIFEST.MF").decode("utf-8", errors="replace")

    unfolded: list[str] = []
    for line in raw.replace("\r\n", "\n").split("\n"):
        if line.startswith(" ") and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)

    result: dict[str, str] = {}
    for line in unfolded:
        if ": " in line:
            key, value = line.split(": ", 1)
            result[key.strip()] = value.strip()
    return result


def validate_jar(jar_path: Path) -> dict[str, str]:
    if not jar_path.is_file():
        raise FileNotFoundError(f"NOM 2 JAR not found: {jar_path}")

    with zipfile.ZipFile(jar_path) as zf:
        if "META-INF/MANIFEST.MF" not in zf.namelist():
            raise RuntimeError("The supplied file is not a normal MIDP JAR: manifest is missing")

        native_3d_refs: list[str] = []
        for name in zf.namelist():
            if not name.endswith(".class"):
                continue
            data = zf.read(name)
            if b"javax/microedition/m3g" in data:
                native_3d_refs.append(f"{name}: javax.microedition.m3g")
            if b"com/mascotcapsule/micro3d" in data:
                native_3d_refs.append(f"{name}: com.mascotcapsule.micro3d")

        if native_3d_refs:
            raise RuntimeError(
                "This NOM 2 JAR uses native 3D APIs, but this dedicated port disables "
                "J2ME Loader's M3G/Micro3D NDK build:\n- " + "\n- ".join(native_3d_refs[:10])
            )

    manifest = read_manifest(jar_path)
    midlet_1 = manifest.get("MIDlet-1", "")
    main_class = midlet_1.rsplit(",", 1)[-1].strip() if midlet_1 else ""

    errors: list[str] = []
    if main_class != EXPECTED_MAIN_CLASS:
        errors.append(f"MIDlet main class is {main_class!r}, expected {EXPECTED_MAIN_CLASS!r}")
    if manifest.get("MIDlet-Vendor") != EXPECTED_VENDOR:
        errors.append(
            f"MIDlet vendor is {manifest.get('MIDlet-Vendor')!r}, expected {EXPECTED_VENDOR!r}"
        )
    if errors:
        raise RuntimeError(
            "The supplied JAR does not look like the analyzed NOM 2 build:\n- "
            + "\n- ".join(errors)
        )

    version = manifest.get("MIDlet-Version")
    if version != EXPECTED_VERSION:
        print(
            f"warning: JAR version is {version!r}; reference port was made for "
            f"{EXPECTED_VERSION!r}",
            file=sys.stderr,
        )

    return manifest


def replace_once(path: Path, old: str, new: str, description: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise RuntimeError(f"Could not apply {description}: expected text not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def patch_build_files(engine: Path) -> None:
    root_gradle = engine / "build.gradle"
    app_gradle = engine / "app" / "build.gradle"

    text = root_gradle.read_text(encoding="utf-8")
    text2 = re.sub(r"MIN_SDK\s*=\s*\d+", "MIN_SDK = 24", text, count=1)
    if text2 == text and "MIN_SDK = 24" not in text:
        raise RuntimeError("Could not set Android minimum SDK to 24")
    root_gradle.write_text(text2, encoding="utf-8")

    open_start = """        open {
            buildConfigField 'boolean', 'FULL_EMULATOR', 'true'
"""
    open_replacement = """        open {
            applicationId "com.u1006.nom2"
            versionName "1.0.43-port1"
            resValue 'string', 'app_name', '놈2'
            buildConfigField 'boolean', 'FULL_EMULATOR', 'true'
"""
    replace_once(app_gradle, open_start, open_replacement, "NOM 2 open flavor configuration")

    debug_name_old = """    applicationVariants.all {
        if (buildType.name == 'debug' && flavorName != 'midlet') {
            resValue 'string', 'app_name', 'JL-Debug'
        }
"""
    debug_name_new = """    applicationVariants.all {
        if (buildType.name == 'debug' && flavorName != 'midlet') {
            resValue 'string', 'app_name', '놈2'
        }
"""
    replace_once(app_gradle, debug_name_old, debug_name_new, "NOM 2 debug application label")

    signing_else_old = """            } else {
                Properties keystoreProps = new Properties()
                keystoreProps.load(new FileInputStream(rootProject.file("keystore.properties")))
"""
    signing_else_new = """            } else if (rootProject.file("keystore.properties").exists()) {
                Properties keystoreProps = new Properties()
                keystoreProps.load(new FileInputStream(rootProject.file("keystore.properties")))
"""
    replace_once(app_gradle, signing_else_old, signing_else_new, "optional release keystore loading")

    release_old = """        release {
            minifyEnabled true
            shrinkResources true
            signingConfig signingConfigs.release
        }
"""
    release_new = """        release {
            minifyEnabled true
            shrinkResources true
            if (System.getenv()['BITRISE_IO'] || rootProject.file("keystore.properties").exists()) {
                signingConfig signingConfigs.release
            }
        }
"""
    replace_once(app_gradle, release_old, release_new, "optional release signing configuration")

    app_text = app_gradle.read_text(encoding="utf-8")
    native_block = """    externalNativeBuild {
        ndkBuild {
            path 'src/main/cpp/Android.mk'
        }
    }

"""
    if native_block in app_text:
        app_text = app_text.replace(native_block, "", 1)
        app_gradle.write_text(app_text, encoding="utf-8")
    elif "externalNativeBuild" in app_text:
        raise RuntimeError(
            "J2ME Loader externalNativeBuild block changed; refusing to remove it blindly"
        )


def patch_storage(engine: Path) -> None:
    path = (
        engine
        / "app"
        / "src"
        / "main"
        / "java"
        / "ru"
        / "playsoftware"
        / "j2meloader"
        / "config"
        / "Config.java"
    )

    old = """\t\tSharedPreferences preferences = PreferenceManager.getDefaultSharedPreferences(context);
\t\tString path = FileUtils.isExternalStorageLegacy() ?
\t\t\t\tpreferences.getString(PREF_EMULATOR_DIR, null) :
\t\t\t\tcontext.getExternalFilesDir(null).getPath();
\t\tif (path == null) {
\t\t\tpath = Environment.getExternalStorageDirectory() + "/" + appName;
\t\t}
\t\tinitDirs(path);
"""

    new = """\t\tSharedPreferences preferences = PreferenceManager.getDefaultSharedPreferences(context);

\t\t// Dedicated NOM 2 port: keep emulator/runtime data in app-private storage.
\t\t// This avoids legacy external-storage behavior across Galaxy S8/S9/S10 and
\t\t// later Android releases.
\t\tString path = new File(context.getFilesDir(), "nom2-runtime").getPath();
\t\tFile runtimeDir = new File(path);
\t\tif (!runtimeDir.isDirectory() && !runtimeDir.mkdirs()) {
\t\t\tthrow new IllegalStateException("Cannot create NOM 2 runtime directory: " + path);
\t\t}
\t\tinitDirs(path);
"""
    replace_once(path, old, new, "NOM 2 app-private runtime storage")


def patch_installer(engine: Path) -> None:
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
        / "AppInstaller.java"
    )
    old = """\tDescriptor getNewDescriptor() {
\t\treturn newDesc;
\t}
"""
    new = """\tAppItem getCurrentApp() {
\t\treturn currentApp;
\t}

\tDescriptor getNewDescriptor() {
\t\treturn newDesc;
\t}
"""
    replace_once(path, old, new, "AppInstaller current app accessor")


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

    fields_old = """\tprivate class ViewCallbacks implements View.OnTouchListener, SurfaceHolder.Callback, View.OnKeyListener {
\t\tprivate final View mView;
\t\tOverlayView overlayView;

\t\tpublic ViewCallbacks(View view) {
"""

    fields_new = """\tprivate class ViewCallbacks implements View.OnTouchListener, SurfaceHolder.Callback, View.OnKeyListener, View.OnGenericMotionListener {
\t\tprivate final View mView;
\t\tOverlayView overlayView;

\t\tprivate float nom2TouchX;
\t\tprivate float nom2TouchY;
\t\tprivate boolean nom2TouchActive;
\t\tprivate int nom2SoftKey;
\t\tprivate int nom2GamepadXKey;
\t\tprivate int nom2GamepadYKey;

\t\tprivate void fireNom2Key(int keyCode) {
\t\t\tpostKeyPressed(keyCode);
\t\t\tpostKeyReleased(keyCode);
\t\t}

\t\tprivate boolean isNom2GamepadEvent(android.view.InputEvent event) {
\t\t\tint source = event.getSource();
\t\t\treturn (source & android.view.InputDevice.SOURCE_GAMEPAD)
\t\t\t\t\t== android.view.InputDevice.SOURCE_GAMEPAD
\t\t\t\t\t|| (source & android.view.InputDevice.SOURCE_JOYSTICK)
\t\t\t\t\t== android.view.InputDevice.SOURCE_JOYSTICK;
\t\t}

\t\tprivate int nom2GamepadKey(int androidKeyCode) {
\t\t\tswitch (androidKeyCode) {
\t\t\t\tcase KeyEvent.KEYCODE_DPAD_UP:
\t\t\t\t\treturn KEY_NUM2;
\t\t\t\tcase KeyEvent.KEYCODE_DPAD_LEFT:
\t\t\t\t\treturn KEY_NUM4;
\t\t\t\tcase KeyEvent.KEYCODE_DPAD_RIGHT:
\t\t\t\t\treturn KEY_NUM6;
\t\t\t\tcase KeyEvent.KEYCODE_DPAD_DOWN:
\t\t\t\t\treturn KEY_NUM8;

\t\t\t\tcase KeyEvent.KEYCODE_BUTTON_A:
\t\t\t\tcase KeyEvent.KEYCODE_BUTTON_X:
\t\t\t\tcase KeyEvent.KEYCODE_BUTTON_Y:
\t\t\t\tcase KeyEvent.KEYCODE_BUTTON_R1:
\t\t\t\tcase KeyEvent.KEYCODE_BUTTON_R2:
\t\t\t\tcase KeyEvent.KEYCODE_BUTTON_THUMBL:
\t\t\t\tcase KeyEvent.KEYCODE_BUTTON_THUMBR:
\t\t\t\t\treturn KEY_NUM5;

\t\t\t\tcase KeyEvent.KEYCODE_BUTTON_B:
\t\t\t\tcase KeyEvent.KEYCODE_BACK:
\t\t\t\t\treturn KEY_SOFT_RIGHT;

\t\t\t\tcase KeyEvent.KEYCODE_BUTTON_START:
\t\t\t\tcase KeyEvent.KEYCODE_BUTTON_MODE:
\t\t\t\tcase KeyEvent.KEYCODE_BUTTON_SELECT:
\t\t\t\t\treturn KEY_SOFT_LEFT;
\t\t\t}
\t\t\treturn 0;
\t\t}

\t\tprivate boolean handleNom2GamepadKey(int keyCode, KeyEvent event) {
\t\t\tif (!isNom2GamepadEvent(event)) {
\t\t\t\treturn false;
\t\t\t}

\t\t\tint midpKey = nom2GamepadKey(keyCode);
\t\t\tif (midpKey == 0) {
\t\t\t\treturn false;
\t\t\t}

\t\t\tif (event.getAction() == KeyEvent.ACTION_DOWN) {
\t\t\t\tif (event.getRepeatCount() == 0) {
\t\t\t\t\tpostKeyPressed(midpKey);
\t\t\t\t} else {
\t\t\t\t\tpostKeyRepeated(midpKey);
\t\t\t\t}
\t\t\t\treturn true;
\t\t\t}
\t\t\tif (event.getAction() == KeyEvent.ACTION_UP) {
\t\t\t\tpostKeyReleased(midpKey);
\t\t\t\treturn true;
\t\t\t}
\t\t\treturn false;
\t\t}

\t\tprivate void updateNom2GamepadAxis(boolean horizontal, int nextKey) {
\t\t\tint previous = horizontal ? nom2GamepadXKey : nom2GamepadYKey;
\t\t\tif (previous == nextKey) {
\t\t\t\treturn;
\t\t\t}
\t\t\tif (previous != 0) {
\t\t\t\tpostKeyReleased(previous);
\t\t\t}
\t\t\tif (nextKey != 0) {
\t\t\t\tpostKeyPressed(nextKey);
\t\t\t}
\t\t\tif (horizontal) {
\t\t\t\tnom2GamepadXKey = nextKey;
\t\t\t} else {
\t\t\t\tnom2GamepadYKey = nextKey;
\t\t\t}
\t\t}

\t\t@Override
\t\tpublic boolean onGenericMotion(View v, MotionEvent event) {
\t\t\tif (!isNom2GamepadEvent(event)
\t\t\t\t\t|| event.getAction() != MotionEvent.ACTION_MOVE) {
\t\t\t\treturn false;
\t\t\t}

\t\t\tfloat x = event.getAxisValue(MotionEvent.AXIS_HAT_X);
\t\t\tfloat y = event.getAxisValue(MotionEvent.AXIS_HAT_Y);
\t\t\tif (Math.abs(x) < 0.01f) {
\t\t\t\tx = event.getAxisValue(MotionEvent.AXIS_X);
\t\t\t}
\t\t\tif (Math.abs(y) < 0.01f) {
\t\t\t\ty = event.getAxisValue(MotionEvent.AXIS_Y);
\t\t\t}

\t\t\tfinal float deadZone = 0.45f;
\t\t\tint xKey = x <= -deadZone ? KEY_NUM4 : (x >= deadZone ? KEY_NUM6 : 0);
\t\t\tint yKey = y <= -deadZone ? KEY_NUM2 : (y >= deadZone ? KEY_NUM8 : 0);
\t\t\tupdateNom2GamepadAxis(true, xKey);
\t\t\tupdateNom2GamepadAxis(false, yKey);
\t\t\treturn true;
\t\t}

\t\tprivate boolean handleNom2Touch(MotionEvent event) {
\t\t\tint action = event.getActionMasked();

\t\t\tif (action == MotionEvent.ACTION_DOWN && event.getPointerCount() == 1) {
\t\t\t\tnom2TouchX = event.getX();
\t\t\t\tnom2TouchY = event.getY();
\t\t\t\tnom2TouchActive = true;
\t\t\t\tnom2SoftKey = 0;

\t\t\t\t// On tall Galaxy displays the preserved 176x208 image leaves a
\t\t\t\t// bottom letterbox. Reuse it as two large MIDP soft-key targets.
\t\t\t\tif (nom2TouchY > onY + onHeight) {
\t\t\t\t\tnom2SoftKey = nom2TouchX < mView.getWidth() / 2.0f
\t\t\t\t\t\t\t? KEY_SOFT_LEFT : KEY_SOFT_RIGHT;
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
\t\t\tfloat threshold = Math.max(40.0f,
\t\t\t\t\tMath.min(mView.getWidth(), mView.getHeight()) * 0.08f);

\t\t\tif (Math.abs(dx) >= threshold || Math.abs(dy) >= threshold) {
\t\t\t\tif (Math.abs(dx) > Math.abs(dy)) {
\t\t\t\t\tfireNom2Key(dx < 0 ? KEY_NUM4 : KEY_NUM6);
\t\t\t\t} else {
\t\t\t\t\tfireNom2Key(dy < 0 ? KEY_NUM2 : KEY_NUM8);
\t\t\t\t}
\t\t\t} else {
\t\t\t\t// NOM 2 converts numeric 5 into its OK/action command internally.
\t\t\t\tfireNom2Key(KEY_NUM5);
\t\t\t}
\t\t\treturn true;
\t\t}

\t\tpublic ViewCallbacks(View view) {
"""
    replace_once(path, fields_old, fields_new, "NOM 2 touch/gamepad controls")

    view_old = """\t\t\tViewCallbacks callback = new ViewCallbacks(innerView);
\t\t\tinnerView.getHolder().addCallback(callback);
\t\t\tinnerView.setOnTouchListener(callback);
\t\t\tinnerView.setOnKeyListener(callback);
\t\t\tinnerView.setFocusableInTouchMode(true);
\t\t\tlayout.addView(innerView);
\t\t\tinnerView.requestFocus();
"""
    view_new = """\t\t\tViewCallbacks callback = new ViewCallbacks(innerView);
\t\t\tinnerView.getHolder().addCallback(callback);
\t\t\tinnerView.setOnTouchListener(callback);
\t\t\tinnerView.setOnKeyListener(callback);
\t\t\tinnerView.setOnGenericMotionListener(callback);
\t\t\tinnerView.setFocusableInTouchMode(true);
\t\t\tlayout.addView(innerView);
\t\t\tinnerView.requestFocus();
"""
    replace_once(path, view_old, view_new, "NOM 2 gamepad motion listener")

    touch_old = """\t\tpublic boolean onTouch(View v, MotionEvent event) {
\t\t\tswitch (event.getActionMasked()) {
"""
    touch_new = """\t\tpublic boolean onTouch(View v, MotionEvent event) {
\t\t\tif (handleNom2Touch(event)) {
\t\t\t\treturn true;
\t\t\t}

\t\t\tswitch (event.getActionMasked()) {
"""
    replace_once(path, touch_old, touch_new, "NOM 2 touch dispatch")

    key_old = """\t\tpublic boolean onKey(View v, int keyCode, KeyEvent event) {
\t\t\tswitch (event.getAction()) {
"""
    key_new = """\t\tpublic boolean onKey(View v, int keyCode, KeyEvent event) {
\t\t\tif (handleNom2GamepadKey(keyCode, event)) {
\t\t\t\treturn true;
\t\t\t}

\t\t\tswitch (event.getAction()) {
"""
    replace_once(path, key_old, key_new, "NOM 2 gamepad key mapping")


def patch_manifest(engine: Path) -> None:
    path = engine / "app" / "src" / "main" / "AndroidManifest.xml"
    text = path.read_text(encoding="utf-8")

    launcher_filter = """            <intent-filter>
                <action android:name="android.intent.action.MAIN" />

                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
"""
    if launcher_filter in text:
        text = text.replace(launcher_filter, "", 1)

    launcher_activity = """        <activity
            android:name="ru.woesss.j2me.installer.Nom2LauncherActivity"
            android:exported="true"
            android:screenOrientation="sensor"
            android:theme="@style/AppTheme.NoActionBar">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
"""
    main_activity_marker = """        <activity
            android:name=".MainActivity"
"""
    if launcher_activity not in text:
        if main_activity_marker not in text:
            raise RuntimeError("Could not find MainActivity in AndroidManifest.xml")
        text = text.replace(main_activity_marker, launcher_activity + main_activity_marker, 1)

    micro_old = """        <activity
            android:name="javax.microedition.shell.MicroActivity"
            android:exported="false"
            android:theme="@style/AppTheme.NoActionBar"
"""
    micro_new = """        <activity
            android:name="javax.microedition.shell.MicroActivity"
            android:exported="false"
            android:screenOrientation="sensor"
            android:theme="@style/AppTheme.NoActionBar"
"""
    if micro_new not in text:
        if micro_old not in text:
            raise RuntimeError("Could not patch MicroActivity sensor orientation")
        text = text.replace(micro_old, micro_new, 1)

    path.write_text(text, encoding="utf-8")


def copy_overlay(root: Path, engine: Path, jar_path: Path) -> None:
    launcher_src = root / "overlay" / "Nom2LauncherActivity.java"
    launcher_dst = (
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
    launcher_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(launcher_src, launcher_dst)

    jar_dst = engine / "app" / "src" / "main" / "assets" / "nom2" / "nom2.jar"
    jar_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(jar_path, jar_dst)

    old_launcher = (
        engine
        / "app"
        / "src"
        / "open"
        / "java"
        / "ru"
        / "woesss"
        / "j2me"
        / "installer"
        / "Nom2LauncherActivity.java"
    )
    old_jar = engine / "app" / "src" / "open" / "assets" / "nom2" / "nom2.jar"
    if old_launcher.exists():
        old_launcher.unlink()
    if old_jar.exists():
        old_jar.unlink()


def patch_app_icon(engine: Path, jar_path: Path) -> None:
    res_dir = engine / "app" / "src" / "main" / "res"
    drawable_dir = res_dir / "drawable-nodpi"
    drawable_dir.mkdir(parents=True, exist_ok=True)
    icon_dst = drawable_dir / "nom2_icon.png"

    with zipfile.ZipFile(jar_path) as zf:
        icon_name = "icon.png"
        if icon_name not in zf.namelist():
            print("warning: icon.png not found in NOM 2 JAR; keeping J2ME Loader icon", file=sys.stderr)
            return
        icon_dst.write_bytes(zf.read(icon_name))

    manifest = engine / "app" / "src" / "main" / "AndroidManifest.xml"
    text = manifest.read_text(encoding="utf-8")
    text = re.sub(
        r'android:icon="[^"]+"',
        'android:icon="@drawable/nom2_icon"',
        text,
        count=1,
    )
    if 'android:roundIcon=' in text:
        text = re.sub(
            r'android:roundIcon="[^"]+"',
            'android:roundIcon="@drawable/nom2_icon"',
            text,
            count=1,
        )
    manifest.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare J2ME Loader as the NOM 2 Android port")
    parser.add_argument("--engine", default="engine", help="J2ME Loader checkout")
    parser.add_argument("--jar", default="game/nom2.jar", help="Local NOM 2 JAR")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    engine = (root / args.engine).resolve() if not Path(args.engine).is_absolute() else Path(args.engine)
    jar_path = (root / args.jar).resolve() if not Path(args.jar).is_absolute() else Path(args.jar)

    manifest = validate_jar(jar_path)

    required = [
        engine / "build.gradle",
        engine / "app" / "build.gradle",
        engine / "app" / "src" / "main" / "AndroidManifest.xml",
        engine / "app" / "src" / "main" / "java" / "javax" / "microedition" / "lcdui" / "Canvas.java",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError(
            "J2ME Loader checkout is incomplete. Missing:\n- " + "\n- ".join(missing)
        )

    copy_overlay(root, engine, jar_path)
    patch_build_files(engine)
    patch_storage(engine)
    patch_installer(engine)
    patch_canvas(engine)
    patch_manifest(engine)
    patch_app_icon(engine, jar_path)

    print("Prepared NOM 2 Android port")
    print(f"  MIDlet: {manifest.get('MIDlet-Name')}")
    print(f"  version: {manifest.get('MIDlet-Version')}")
    print(f"  build id: {manifest.get('BUILD_ID')}")
    print(f"  engine: {engine}")
    print("  primary device: Samsung Galaxy S10")
    print("  compatibility: API 24+ / Galaxy S8 and newer")
    print("  display: 176x208, fullscreen aspect-fit, sensor rotation")
    print("  controls: tap=5, swipe=2/4/6/8, bottom soft keys, gamepad")
    print("  native 3D: disabled (reference JAR does not use M3G/Micro3D)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
