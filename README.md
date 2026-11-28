# Vita3K+ portrait

An Android-focused portrait edition of [Vita3K+](https://github.com/nckstwrt/Vita3K-Plus), based on the open-source [Vita3K emulator](https://github.com/Vita3K/Vita3K).

Vita3K+ portrait brings a more comfortable portrait gameplay experience to Android, with customizable display positioning, touch controls, and an integrated cheat manager.

## Features

- **Portrait gameplay layout:** arrange the Vita display and on-screen controls for portrait play.
- **Display scale and positioning:** adjust the size and vertical placement of the game display to suit your screen and preferred layout.
- **Custom touch controls:** reposition and configure on-screen controller buttons, then save your layout.
- **Cheat Manager:** browse available cheats and enable or disable them for supported games.
- **Game library preferences:** filter and sort your game library and retain your preferred presentation.
- **Universal Android APK:** supports both `arm64-v8a` and `x86_64` in a single APK.

Game compatibility and performance depend on the title, Android device, GPU, and graphics driver.

## Download

Get the latest Android APK from the [GitHub Releases page](https://github.com/NYX94/Vita3K-Plus-portrait/releases).

The release APK includes both supported Android architectures.

## Build an Android APK

From the repository root in GitHub Codespaces, run:

```bash
bash scripts/build-android-relperf.sh
```

The script builds the Android `relperf` variant, increments `.portrait-build-number`, and places the numbered APK in the repository root.

A release build requires a signing key. Keep the keystore and its password private and never commit them to the repository.

## Android notes

- Compatibility and performance vary by game, device, GPU, and driver.
- On supported Adreno devices, a compatible Turnip driver may improve compatibility.
- Mali behavior is driver- and game-dependent, and some titles may still have rendering or performance issues.
- For games that freeze or hang, try enabling **Accurate Thread Scheduling** in the game's graphics settings. Some titles may also require a lower guest-core count.

## AI-assisted development

AI tools, including ChatGPT, have assisted with code exploration, implementation suggestions, debugging, and documentation. AI-assisted changes are reviewed and tested as part of development.

## Report a problem

Please report issues in the [GitHub issue tracker](https://github.com/NYX94/Vita3K-Plus-portrait/issues). Include your device model, Android version, GPU and driver, game title and ID, relevant settings, and a log when possible.

## Credits and license

Vita3K+ portrait is based on the [Vita3K emulator](https://github.com/Vita3K/Vita3K) and incorporates enhancements from the [Vita3K+ project](https://github.com/nckstwrt/Vita3K-Plus).

Credit for the original emulator and upstream enhancements belongs to their respective projects and contributors. This project is licensed under the GNU General Public License v2.0; see [COPYING.txt](./COPYING.txt) for details.
