# Vita3K+ portrait

An Android-focused, portrait-oriented community fork of [Vita3K+](https://github.com/nckstwrt/Vita3K-Plus), built on the open-source [Vita3K emulator](https://github.com/Vita3K/Vita3K).

The project focuses on making Vita3K+ more comfortable to use on portrait Android devices while retaining upstream emulator functionality and compatibility improvements.

## Project focus

- **Portrait gameplay layout:** arrange the Vita display and touch controls for portrait use.
- **Display controls:** adjust the portrait display scale and vertical position.
- **Touch controls:** configure, position, and save the on-screen controller layout.
- **Android navigation:** integrate the status bar, system UI, pause menu, and app lifecycle with gameplay.
- **Game library:** provide responsive filtering, sorting, and persistent list/grid preferences.
- **Cheat support:** load and use the emulator's native cheat database and runtime integration.
- **Build identification:** show a unique build number in the app and APK filename.
- **Android tuning:** ongoing work on memory use, responsiveness, and device resource management.

This is an experimental community project. Compatibility and performance vary by game, Android device, GPU, and driver.

## AI-assisted development

AI tools, including ChatGPT, have been used to assist with code exploration, implementation suggestions, debugging, and documentation. AI-generated suggestions are reviewed and tested as part of the development process; AI assistance does not replace maintainer review or device testing.

## Build an Android APK

The current Android build target is **64-bit ARM (`arm64-v8a`)**.

In GitHub Codespaces, run this command from the repository root:

```bash
bash scripts/build-android-relperf.sh
```

The script builds the optimized Android `relperf` variant, increments `.portrait-build-number`, and places the numbered APK in the repository root.

## Android notes

- Game compatibility is experimental and can differ between devices and graphics drivers.
- On supported Adreno devices, a compatible Turnip driver may improve compatibility.
- Mali behavior is driver- and game-dependent; some titles may still have rendering or performance issues.
- For games that freeze or hang, try enabling **Accurate Thread Scheduling** in the game's graphics settings. Some titles may also require a lower guest-core count.

## Upstream project and compatibility

This fork builds on work from the Vita3K and Vita3K+ projects. Upstream compatibility and gameplay improvements are reviewed for selective integration while preserving the Android portrait-specific changes.

## Report a problem

Please report issues in the [GitHub issue tracker](https://github.com/NYX94/Vita3K-Plus-portrait/issues). Include your device model, Android version, GPU/driver, game title and ID, relevant settings, and a log when possible.

## Credits and license

Vita3K+ portrait is based on the [Vita3K emulator](https://github.com/Vita3K/Vita3K) and incorporates enhancements from the [Vita3K+ project](https://github.com/nckstwrt/Vita3K-Plus).

Credit for the original emulator and upstream enhancements belongs to their respective projects and contributors. This project is licensed under the GNU General Public License v2.0; see [COPYING.txt](./COPYING.txt) for details.
