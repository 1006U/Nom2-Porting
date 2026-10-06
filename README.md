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
- Touch controls:
  - Tap on the game surface -> J2ME `5` / OK / action
  - Swipe up/down/left/right -> J2ME `2/8/4/6`
  - Bottom-left letterbox -> left soft key `-6`
  - Bottom-right letterbox -> right soft key `-7`
- Gamepad controls:
  - D-pad / left stick -> `2/4/6/8`
  - A / X / Y / R1 / R2 / stick click -> `5`
  - B / Android Back -> right soft key `-7`
  - Start / Menu / Select -> left soft key `-6`

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
- JDK compatible with the pinned J2ME Loader/Gradle project

Place your game file here:

```text
Nom2-Porting/
  game/
    nom2.jar
```

Prepare the Android project:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
```

Build an APK without ADB/USB debugging:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\one-click.ps1
```

The resulting APK is copied to:

```text
dist/NOM2-debug.apk
```

You can also build from Android Studio by opening the generated `engine` directory, or from PowerShell:

```powershell
cd engine
.\gradlew.bat :app:assembleOpenDebug
```

## Current port stage

This first NOM 2 port establishes a runnable Galaxy S10 baseline: launcher, local bundled JAR install, private runtime storage, fullscreen aspect-fit rendering, tap/swipe controls, gamepad controls, app naming, and APK-only build flow.

NOM 1's exact direct-menu-touch implementation depends on NOM 1-specific obfuscated fields/methods and is intentionally **not copied blindly**. After Galaxy S10 device testing, NOM 2 menu state can be mapped separately for exact direct-item touch and context-sensitive bottom buttons.

## Upstream

Runtime base: J2ME Loader by nikita36078, release 1.8.2. Upstream Apache-2.0 notices remain in the generated engine checkout.
