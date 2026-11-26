# Vita3K+ portrait

An Android-focused portrait edition of Vita3K+, based on the open-source Vita3K emulator. It retains the original Vita3K+ game compatibility and rendering enhancements while adding a portrait-oriented Android interface and usability improvements.

This is an independent community fork. Credit for the original emulator and Vita3K+ enhancements belongs to their respective projects and contributors.

Note: this fork was created with the help of ChatGPT
## Android portrait edition

- **Portrait split layout:** arrange the Vita display and on-screen controls for portrait gameplay.
- **Display adjustment:** configure portrait display scale and vertical position.
- **Orientation-aware system UI:** show the Android status bar in portrait mode and use immersive presentation in landscape.
- **Persistent game-list layout:** List and Grid preferences survive app restarts.
- **Responsive game library:** filtering and sorting are moved away from the UI thread.
- **In-game pause menu:** Android Back is designed to open the pause menu and pause the running game; Back from the menu closes it and resumes gameplay.
- **Controller overlay improvements:** configurable touch controls, layout editing, and saved overlay settings.
- **Game lifecycle improvements:** more reliable shutdown, relaunch, and switching between games.
- **Native cheat support:** native cheat database parsing, loading, and runtime integration. A dedicated cheat-management screen is not yet included.
- **Build identification:** scripted APKs receive unique build numbers shown on the main screen and included in their filenames.
- **Optimized Android build:** the `relperf` variant uses native Release optimization and Android code/resource shrinking.

## Android notes

> [!IMPORTANT]
> **Snapdragon / Adreno:** Use Turnip drivers for the best compatibility.

> [!IMPORTANT]
> **Mali Users:** There are things that will definitely not work and most likely never work with Mali. Very little I can (or want) to do about that I'm afraid.

> [!IMPORTANT]
> **Freezing or hangs:** Enable **Accurate Thread Scheduling** in Graphics settings (which is the new default).  
> This is needed for games such as *Dead or Alive 5 Plus*, *Sonic*, *Samurai Warriors 3*, etc.
> Sonic might require you set Guest Cores to 1 to start up

## Build an Android APK

In GitHub Codespaces, run the following command from the repository root:

```bash
./scripts/build-android-relperf.sh
```

The script builds the optimized Android `relperf` variant, automatically assigns the next available portrait build number, and saves the APK in the repository root.

The build number is displayed on the app's main screen and included in the APK filename.

Example filename: `Vita3K-Plus-portrait-build-001-relperf.apk`

## Enhancements

# v1.4 - Released 6th November 2026
- **Battle Pentagram** - Now working with Mali
- **UPPERS** - Was freezing in v1.3, now fixed again
- **Call of Duty** - Shadows fixed on Turnip for Adreno 6xx devices
- **WRC 3** - Now working on Mali + Double Buffer memory mapping options
- **Epic Mickey** - Now working on Mali (Fixes graphics issues)
- **J-Stars** - Now working on Mali (Fixes graphics issues)
- **Killzone** - Haze/Mist/Fog now drawing correctly, FPS Hack now works to play at 60fps
- **Grim Fandango** - Fixes videos playing at double speed
- **FIFA 13 + FIFA Football** - Automatically applies the Flie Loading Delay required for the game to start
- **Uncharted** - Fix Camera use so Chapter 13 is easier to get past
- **No Heroes Allowed: No Puzzles Either!** - Fixed colours/graphics
- **Zero Escape: Zero Time Dilemma** - Loading and graphics fixed
- **God Eater 2: Rage Burst** - Attempted fix for Rage Burst locking
- **Mali Vertex Improvements** - Fixes vertex issues on Mali games (Don't expect Miracles!)
- **Low Memory Device Improvements** - Now can run games like Killzone on low memory devices (like Retroid Flip 1 (4GB RAM))
- **Lots of little additions** - Gamepad improvements, upstream additions (cheat db + home screen shortcuts), etc

# v1.3 - Released 18th October 2026
- **Pixeljunk Shooter ultimate** - Sound glitches fixed
- **UNDER NIGHT IN-BIRTH** - Fixed flickering
- **Madoka Magica - The Battle Pentagram** - Graphics fixes
- **Ratchet & Clank** - Vertex renderering fixes
- **Samurai Warriors 4** - Fix for freezing
- **Samurai Warriors 3** - Fix for freezing
- **Rayman Legends** - Fix for level end freeze
- **MotoGP 14** - Fix for audio stuttering on Android
- **Killzone** - Fix for crashing on some Android devices
- **DariusBurst CS** - Graphics fix
- **WRC 3** - Car Graphics Fix
- **MLB 15** - Fix startup crash (still has minor flickering before reaching title screen but otherwise fine)
- **Epic Mickey 2** - Fix for Turnip devices. Still will have some graphics issues on most Mali devices.
- **Jak & Daxter Trilogy** - Start up and Graphics fixed
- **One Piece** - Graphics issues (black blocks/lines) fixed
- **Hatsune Miku** - Broken song's video crashes fixed
- **The Amazing Spider-Man** - Fix shadows (flickering)
- **Metal Gear Solid 3** - Subtitles and Audio no longer out of sync
- **Android 17** - Fix for Turnip to work on Android 17/OneUI 9 devices
- **Audio Fixes** - cubeb and SDL audio should no longer crackle/stutter/pop/cut out/etc
- **Mali Fixes** - Don't expect miracles! But now DOA5 works fine on my Mali S21 :)

# v1.2 - Released 30th Sept 2026
- **Soul Sacrifice Delta** - Outline missing regression + floor textures fixed (Thanks doctorthoss and NaGaa95!)
- **Madden 13** - Commentary + Crowd sounds working + Load/Save Fixes
- **Mortal Kombat** - Broken video colours fixed
- **Ridge Racer** - Reflections fixed
- **Resistance** - Fixed level not fully loading on slower devices
- **Ragnarok Odyssey ACE** - Graphics now working correctly on Android
- **Demon Gaze** - Now loads into game
- **Super Hero Nation** - Cloud Graphics Fixed
- **Dragon Quest Heroes II** - No longer crashes when in game
- **Ys VIII** - Lacrimosa of Dana - regression issue fixed
- **Need For Speed** - Fixed Anisotropic Filtering + Crash sounds
- **Gundam Breaker 3** - Corrected minor mech drawing issues
- **Epic Mickey 2** - Fixed the broken white parts of the graphics
- **Fifa 15** - Commentary audio working + Crowd graphics fixed
- **Skullgirls 2nd Encore** - Fix background and character graphics
- **Dead Or Alive Xtreme 3** - Graphics fixed
- **Ys Celcetta** - Fixed not loading on Android
- **Jet Set Radio** - Game booting and Graphics Fixed
- **Golden Time** - Game now booting and running fine
- **Shin Gundam Mosou** - Fix missing laser/effect graphics. Fix voices/dialogue. (thanks to mohawku-bit's Enhanced version which was used as a reference)
- **Injustice** - Gods Among Us - Projectiles now show
- **Uncharted** - Fix for camera pictures being green
- **MotoGP 14** - Fixed bike being black
- **Silent Hill** - Graphics fixed - Set Settings->Emulator->File Loading Delay = 3ms. Thanks to the ThePr⌀fessor!
- **Mali Vertex Issue** - Fixes some vertices appearing stretched (e.g. The title screen butterfly in Soul Sacrifice Delta)
- **Double Buffer Improvements** - Mali generally will fallback to Double Buffer (even with other memory mappings selected). So this should make Mali significantly better.
- **Adreno 6xx + Turnip** - Fix for black checkered pattern sometimes appearing in some games

# v1.1 - Released 13th Sept 2026
- **Dead Or Alive 5 Plus** - Working - On Android requires Adreno, Turnip and the new setting Thread Scheduling Accuracy On
- **Metal Gear Solid 3** - Freezes fixed/worked around. Blending graphics fixed. On-Screen Touchpad fixes.
- **Resistance** - Rendering issues fixed on Android (for Turnip devices - Mali can still have issues)
- **Assassin's Creed III: Liberation**: Sound issues resolved
- **Killzone** - Fix for the crash occurring at level 5
- **Neptunia Re;Birth1** - Fix for crash after selecting New Game and background images not showing
- **Little Big Planet** - "Vignette" shading and background images fixed
- **Ys: Memories of Celcetta** - Graphics Fixed
- **Ragnarok Odyssey ACE** - Graphics Fixed
- **Ninja Gaiden Sigma 2 Plus** - Graphics Fixed
- **ModNation: Racers Road Trip** - Regression Fixed
- **RESOGUN** - Graphics issues now fixed
- **Omega Labyrinth** - Loading fixed by nishinji
- **Dynasty Warriors 8** - Fixed text/graphics clipping
- **Samurai Warriors 3** - Use Accurate Thread Scheduling to workaround loading bugs
- **Gundam Breaker 3** - Graphics Fixed
- **SteamWorld Dig** - Loads and plays
- **UPPERS** - Graphics Fixed
- **Madden 13** - Face textures + Crowd fixed 
- **Oddworld: New'n'Tasty** - Graphics Fixed
- **God Eater 2 Rage Burst** - Graphics Fixed
- **Sword Art Online** - Latest game patch now works
- **Disgaea 3** - Saving & Loading now work. liblocation implemented to hopefully stop the 50 min crashes.
- **Borderlands 2** - Shorten time it checks for PSN
- **Evil Corps From Hell** - Loading and graphics fixed
- **Tearaway** - Graphics Fixed
- **Ultimate Marvel vs Capcom 3** - Graphics Fixed
<!-- -->
- Defaults now to External Host for Windows and Page Table on Android. **Use these Memory Mapping options for the best compatibility**
- Lots of memory, timing, stability, IME and sound improvements
- Thanks to Reyes for all his help testing!

# v1.0
- **Killzone** Plays well and looks amazing
- **Resistance** Colours are now all good. Intermittent freezing has been fixed.
- **Assassin's Creed III: Liberation**: Graphical issues fixed
- **LittleBigPlanet**: Missing backgrounds, starting sounds and other graphics fixed
- **Need for Speed: Most Wanted**: floating badges fixed, headlights through the road fixed, sound fixed (mostly).
- **Call of Duty: Declassified** Boots and plays well now
- **Uncharted** Now plays at any resolution plus minor fixes
- **Devious Dungeon** Now launches fine
- **Sonic Transformed** Plays well and looks amazing (new per game thread accuracy setting to ensure a good startup)
- **Spider-Man** No longer sometimes hangs on load.
- **Helldivers** No longer sometimes crashes at startup
- **Soul Sacrifice Delta**: Graphical issues fixed
- **Minecraft** was a white screen in Vulkan, now fixed
- **Kancolle Kai** Now plays without getting stuck at the difficulty selection screen
  
Hopefully a lot of crash bugs and freezing have been fixed by these changes. Other games may now be a lot better or possibly worse with this version.

## Notes

- The settings now default to High Quality
- These updates were designed with higher-end devices in mind. Although I have attempted to make them work and tested on Mali based devices (i.e. Killzone works fine on a Mali-G78 MP14 device I have) that is not the goal of this fork.
- For better character shadows in Killzone use a memory mapping of External Host on Windows or Native Buffer on Android. Double Buffer works well but makes the shadows flicker annonyingly.

## New Screenshots

See the **[Screenshots page](./Screenshots.md)** for the games above running in Vita3K+.

[![Vita3K+ screenshots](./screenshots/KZ.jpg)](./Screenshots.md)

## Report Issues and Problems

https://github.com/NYX94/Vita3K-Plus-portrait/issues

## Code Changes
The Android portrait edition is maintained in this repository. The original Vita3K+ compatibility work is credited to the upstream Vita3K+ project.

## Credits and license

Vita3K+ portrait builds on the original [Vita3K emulator](https://github.com/Vita3K/Vita3K) and [Vita3K+ project](https://github.com/nckstwrt/Vita3K-Plus).

Credit for the original emulator and upstream enhancements belongs to their respective projects and contributors. See the repository license for licensing details.
