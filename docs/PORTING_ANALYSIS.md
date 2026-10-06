# NOM 2 Porting Analysis

## Reference JAR

Analyzed local game build:

- MIDlet-Name: `NOM2 FREE RUNNER`
- MIDlet-Version: `1.0.43`
- MIDlet-Vendor: `GAMEVIL Inc./BiNPDA`
- Main class: `Nom2`
- MicroEdition-Profile: `MIDP-2.0`
- MicroEdition-Configuration: `CLDC-1.0`
- BUILD_ID: `NOM2_ATT_NK_6682`
- Class count: 50
- M3G references: none
- Mascot Capsule Micro3D references: none

The game is therefore suitable for the same J2ME Loader 2D runtime strategy used by the NOM 1 port, without the native 3D/NDK path.

## Game classes

`Nom2` is the MIDlet entry point and keeps the main game canvas in a static field of type `e`.

The obfuscated class `e` extends `javax.microedition.lcdui.Canvas` and implements the game's rendering/input loop. The game contains the classic 176-pixel-width layout constants and is configured by the Android launcher as a 176x208 virtual display.

## Input findings

Disassembly of `e.keyPressed(int)` shows that the game stores the incoming MIDP key code and has a helper that normalizes either numeric `5` (`53`) or FIRE (`-5`) into its internal OK/action command (`1003`).

This makes the following Android mapping safe for the baseline port:

- Tap -> `KEY_NUM5`
- Swipe up -> `KEY_NUM2`
- Swipe down -> `KEY_NUM8`
- Swipe left -> `KEY_NUM4`
- Swipe right -> `KEY_NUM6`
- Bottom-left letterbox -> `KEY_SOFT_LEFT`
- Bottom-right letterbox -> `KEY_SOFT_RIGHT`

Gamepad mapping mirrors those MIDP keys.

## Galaxy S10 display strategy

Primary real-device test target: **Samsung Galaxy S10**.

The Galaxy S10 is much taller than the original 176x208 MIDP aspect ratio. The port therefore intentionally uses:

- fullscreen mode
- maximum aspect-fit scaling
- original aspect ratio preserved
- no cropping
- no stretching
- black unused area
- nearest-neighbor style rendering (`screenFilter = false`)
- sensor orientation support

The unused lower letterbox area is also useful as a large touch target for the two MIDP soft keys without covering the game artwork.

## Why NOM 1 direct-menu reflection is not copied yet

The current NOM 1 port contains reflection logic tied to NOM 1's exact obfuscated class/field/method names. NOM 2 uses a different obfuscation layout (`e` is the main Canvas and its state fields differ substantially), so copying those field names would create fragile or incorrect menu behavior.

The first NOM 2 milestone therefore focuses on a stable runnable baseline using normal MIDP navigation: swipe to move selection and tap to confirm. Once the Galaxy S10 build is running, the next reverse-engineering step is to identify NOM 2's menu state, selection index, menu row calculation, pause state, and confirmation-dialog state. Those can then be used to add exact direct-item touch and dynamic bottom controls in the same style as the mature NOM 1 port.

## Runtime base

The generated Android project uses J2ME Loader 1.8.2. The preparation script verifies its expected source layout before applying patches and fails instead of silently patching an unknown structure.
