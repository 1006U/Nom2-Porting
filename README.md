# NOM 2 Android Port

Android porting workspace for **NOM 2 / 놈2** using the open-source J2ME Loader runtime as a compatibility layer.

This repository contains only Android porting glue, configuration, and patches. The original proprietary game JAR is **not committed**. Put your legally obtained copy at `game/nom2.jar` before running setup.

## Target

- Primary real-device test target: **Samsung Galaxy S10**
- Compatibility target: Galaxy S8 and newer devices
- Android 7.0 / API 24 or newer
- Original 176x208 game aspect ratio preserved
- Fullscreen, maximum aspect-fit scaling without stretching or cropping
- Portrait/landscape sensor rotation
- No J2ME virtual keypad
- Korean patch is generated automatically as `game/generated/nom2-ko.jar`
- Original launcher artwork is used without redrawing/cropping/recoloring
- Visible native bottom buttons are shown below the game surface

## Controls

Touch controls:

- Tap on the game surface -> J2ME `5` / OK / action
- Swipe up/down/left/right -> J2ME `2/8/4/6`
- Bottom-left native button -> left soft key `-6` (OK/menu/pause depending on game state)
- Bottom-right native button -> right soft key `-7` / Back
- Galaxy S10 swipe threshold is tuned to a fixed density-aware value instead of a percentage of the full screen

Gamepad controls:

- D-pad / left stick -> `2/4/6/8`
- A / X / Y / R1 / R2 / stick click -> `5`
- B / Android Back -> right soft key `-7`
- Start / Menu / Select -> left soft key `-6`

## Korean patch

The source JAR stores its messages in `text/text.scr` and uses a custom bitmap font class (`gvl.f`). The build now:

1. translates all 88 `text.scr` entries into Korean,
2. translates important hard-coded menu labels such as `EXIT`, `MAIN MENU`, `RESULT`, `SOUND`, and `VIBRATION`,
3. preserves the original bitmap glyph renderer for ASCII,
4. replaces only the font helper with a Korean-capable bridge so Hangul is drawn through the J2ME/Android system font,
5. keeps `game/nom2.jar` untouched and creates `game/generated/nom2-ko.jar` for the APK.

## Original APK icon

Put the untouched artwork in the recommended location:

```text
branding/app_icon.png
```

The build also accepts JPG/JPEG and a few fallback filenames documented in `branding/README.md`.

The image is **not regenerated or redesigned**. The script only preserves its aspect ratio and creates the Android `mipmap-mdpi` through `mipmap-xxxhdpi` sizes. If the source artwork is not square, its complete composition is centered on a square canvas rather than cropped or stretched.

## Runtime strategy

Like the NOM 1 port, this project pins **J2ME Loader 1.8.2** and applies a dedicated patch set instead of rewriting the obfuscated MIDP game.

The analyzed NOM 2 JAR is a 2D MIDP title and contains no references to `javax.microedition.m3g` or Mascot Capsule Micro3D, so the unnecessary J2ME Loader native 3D/NDK build is disabled.

## Source JAR analyzed for this port

- MIDlet-Name: `NOM2 FREE RUNNER`
- MIDlet-Version: `1.0.43`
- MIDlet-Vendor: `GAMEVIL Inc./BiNPDA`
- Main class: `Nom2`
- MIDP: `2.0`
- CLDC: `1.0`
- Build ID: `NOM2_ATT_NK_6682`
- Game Canvas class: obfuscated class `e`
- Reference screen: 176x208

## Setup on Windows

Requirements:

- Git
- Python 3.10+
- Android Studio with Android SDK
- Android Studio bundled JDK or another JDK with `javac`

Place your original files like this:

```text
Nom2-Porting/
  game/
    nom2.jar
  branding/
    app_icon.png
```

Build an APK without ADB/USB debugging:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\one-click.ps1
```

`setup.ps1` automatically:

- detects the Android SDK and creates `engine/local.properties`,
- installs Pillow if needed,
- creates the Korean-patched JAR,
- prepares J2ME Loader,
- applies the Galaxy S10 touch/button fixes,
- generates launcher mipmaps from the untouched original artwork.

The resulting APK is copied to:

```text
dist/NOM2-debug.apk
```

You can also build from Android Studio by opening the generated `engine` directory, or from PowerShell:

```powershell
cd engine
.\gradlew.bat :app:assembleOpenDebug
```

## Upstream

Runtime base: J2ME Loader by nikita36078, release 1.8.2. Upstream Apache-2.0 notices remain in the generated engine checkout.
