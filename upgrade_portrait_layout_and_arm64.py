#!/usr/bin/env python3
"""Upgrade the existing Vita3K+ combined portrait/landscape build.

Run from the repository root after apply_portrait_layout_and_orientation_toggle.py.
This patch adds orientation-specific controller layouts, a portrait editor preview,
portrait display scale/position controls in main Settings, full-height pause menu
visibility, and an ARM64-only Android build.
"""
from pathlib import Path
import re
import shutil
import sys

ROOT = Path.cwd()
MARKER = ROOT / ".portrait-layout-upgrade-v1.done"
if MARKER.exists():
    raise SystemExit("This upgrade has already been applied in this workspace. Do not run it twice.")
BASE = Path("android/app/src/main")
FILES = [
    BASE / "java/org/vita3k/emulator/Emulator.java",
    BASE / "java/org/vita3k/emulator/overlay/InputOverlay.java",
    BASE / "java/org/vita3k/emulator/overlay/OverlayStore.kt",
    BASE / "java/org/vita3k/emulator/ui/viewmodel/EmulationSessionViewModel.kt",
    BASE / "java/org/vita3k/emulator/ui/screens/emulation/EmulationPauseMenu.kt",
    BASE / "java/org/vita3k/emulator/ui/screens/settings/OverlayLayoutEditorDialog.kt",
    BASE / "java/org/vita3k/emulator/ui/screens/settings/SettingsModels.kt",
    BASE / "java/org/vita3k/emulator/ui/screens/settings/SettingsSections.kt",
    BASE / "java/org/vita3k/emulator/ui/screens/settings/SettingsRoute.kt",
    BASE / "java/org/vita3k/emulator/ui/screens/settings/SettingsSearch.kt",
    BASE / "res/values/strings.xml",
    Path("android/app/build.gradle"),
]
for rel in FILES:
    if not (ROOT / rel).is_file():
        raise SystemExit(f"Missing expected source file: {rel}. Run this from the repository root.")

VULKAN_SHADER_SOURCE = ROOT / "vita3k/shaders-builtin/vulkan"
VULKAN_ASSET_DEST = ROOT / "android/app/assets/shaders-builtin/vulkan"
if not VULKAN_SHADER_SOURCE.is_dir():
    raise SystemExit(f"Missing Vulkan shader source directory: {VULKAN_SHADER_SOURCE}")
shader_files = sorted(VULKAN_SHADER_SOURCE.glob("*.spv"))
required_shaders = {"render_main.vert.spv", "render_main.frag.spv"}
missing_shaders = required_shaders - {item.name for item in shader_files}
if not shader_files or missing_shaders:
    raise SystemExit(f"Vulkan shader sources are incomplete: {sorted(missing_shaders)}")
VULKAN_ASSET_DEST.mkdir(parents=True, exist_ok=True)
for shader in shader_files:
    shutil.copy2(shader, VULKAN_ASSET_DEST / shader.name)
print(f"Copied {len(shader_files)} Vulkan SPIR-V assets into android/app/assets.")

EMU, INPUT, STORE, SESSION_VM, PAUSE_MENU, EDITOR, SETTINGS_MODELS, SETTINGS_SECTIONS, SETTINGS_ROUTE, SETTINGS_SEARCH, STRINGS, APP_GRADLE = [ROOT / p for p in FILES]

# Do not overwrite a previous backup. This makes rollback straightforward.
BACKUP = ROOT / ".portrait-layout-upgrade-backup"
for rel in FILES:
    dest = BACKUP / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(ROOT / rel, dest)


def replace_braced_function(src: str, signature: str, replacement: str):
    """Replace a function declaration/body by scanning balanced braces."""
    idx = src.find(signature)
    if idx < 0:
        return src, False
    brace = src.find("{", idx)
    if brace < 0:
        raise SystemExit(f"Could not find body for {signature!r}")
    depth = 0
    in_string = False
    in_char = False
    escaped = False
    line_comment = False
    block_comment = False
    i = brace
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ""
        if line_comment:
            if ch == "\n":
                line_comment = False
        elif block_comment:
            if ch == "*" and nxt == "/":
                block_comment = False
                i += 1
        elif in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        elif in_char:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == "'":
                in_char = False
        elif ch == "/" and nxt == "/":
            line_comment = True
            i += 1
        elif ch == "/" and nxt == "*":
            block_comment = True
            i += 1
        elif ch == '"':
            in_string = True
        elif ch == "'":
            in_char = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[:idx] + replacement + src[i + 1:], True
        i += 1
    raise SystemExit(f"Unbalanced braces while replacing {signature!r}")


def replace_once(src: str, old: str, new: str, label: str):
    if old not in src:
        if new in src:
            return src
        raise SystemExit(f"Could not locate expected code for {label}")
    return src.replace(old, new, 1)


def add_jvm_overloads(src: str, function_name: str):
    pattern = rf"(@JvmStatic\s*)(fun {re.escape(function_name)}\()"
    return re.sub(pattern, r"\1@JvmOverloads\n    \2", src, count=1)


# ---------------------------------------------------------------------------
# OverlayStore.kt: independent layout coordinates for portrait and landscape.
# ---------------------------------------------------------------------------
s = STORE.read_text()

# Replace default layout with preserved landscape defaults and dedicated portrait defaults.
new_default_layout = '''fun defaultLayout(context: Context, portrait: Boolean = false): OverlayLayout {
        if (portrait) {
            val portraitPositions = mapOf(
                InputOverlay.ButtonType.BUTTON_CROSS to OverlayPosition(0.78f, 0.57f),
                InputOverlay.ButtonType.BUTTON_CIRCLE to OverlayPosition(0.88f, 0.45f),
                InputOverlay.ButtonType.BUTTON_SQUARE to OverlayPosition(0.68f, 0.45f),
                InputOverlay.ButtonType.BUTTON_TRIANGLE to OverlayPosition(0.78f, 0.33f),
                InputOverlay.ButtonType.BUTTON_SELECT to OverlayPosition(0.22f, 0.87f),
                InputOverlay.ButtonType.BUTTON_START to OverlayPosition(0.66f, 0.87f),
                InputOverlay.ButtonType.BUTTON_PS to OverlayPosition(0.47f, 0.94f),
                InputOverlay.ButtonType.DPAD_UP to OverlayPosition(0.04f, 0.31f),
                InputOverlay.ButtonType.STICK_LEFT to OverlayPosition(0.04f, 0.69f),
                InputOverlay.ButtonType.STICK_RIGHT to OverlayPosition(0.76f, 0.72f),
                InputOverlay.ButtonType.TRIGGER_L to OverlayPosition(0.02f, 0.01f),
                InputOverlay.ButtonType.TRIGGER_R to OverlayPosition(0.80f, 0.01f),
                InputOverlay.ButtonType.TRIGGER_L2 to OverlayPosition(0.22f, 0.01f),
                InputOverlay.ButtonType.TRIGGER_R2 to OverlayPosition(0.58f, 0.01f),
                InputOverlay.ButtonType.TRIGGER_L3 to OverlayPosition(0.29f, 0.13f),
                InputOverlay.ButtonType.TRIGGER_R3 to OverlayPosition(0.56f, 0.13f),
                InputOverlay.ButtonType.BUTTON_TOUCH_HIDE to OverlayPosition(0.73f, 0.89f),
                InputOverlay.ButtonType.BUTTON_TOUCH_SWITCH to OverlayPosition(0.45f, 0.08f)
            )
            return OverlayLayout(portraitPositions).normalized()
        }

        val resources = context.resources
        val positions = defaultEntries.associate { entry ->
            entry.buttonType to OverlayPosition(
                normalizedX = (resources.getInteger(entry.xResId) / 1000f).coerceNormalizedCoordinate(),
                normalizedY = (resources.getInteger(entry.yResId) / 1000f).coerceNormalizedCoordinate()
            )
        }
        return OverlayLayout(positions).normalized()
    }'''
s, found = replace_braced_function(s, "fun defaultLayout(context: Context)", new_default_layout)
if not found:
    raise SystemExit("Could not update OverlayStore.defaultLayout")

# Preserve the old one-argument Java call signatures while adding the portrait flag.
for fn in ("defaultLayout", "defaultState", "loadGlobalState", "loadGameOverride", "resolveState", "saveGlobalState", "saveGameOverride", "loadLayout"):
    s = add_jvm_overloads(s, fn)

# Replace expression-bodied defaultState explicitly.
s = replace_once(
    s,
    '''fun defaultState(context: Context): OverlayState =
        OverlayState(
            config = OverlayConfig().normalized(),
            layout = defaultLayout(context)
        )''',
    '''fun defaultState(context: Context, portrait: Boolean = false): OverlayState =
        OverlayState(
            config = OverlayConfig().normalized(),
            layout = defaultLayout(context, portrait)
        )''',
    "OverlayStore.defaultState"
)

replacements = [
    (
        "fun loadGlobalState(context: Context): OverlayState",
        '''fun loadGlobalState(context: Context, portrait: Boolean = false): OverlayState {
        val prefs = preferences(context)
        val fallback = legacyGlobalState(context, portrait)
        return loadScopeState(prefs, scopeId = null, fallback = fallback, portrait = portrait)
    }'''
    ),
    (
        "fun loadGameOverride(context: Context, scopeId: String?): OverlayState?",
        '''fun loadGameOverride(context: Context, scopeId: String?, portrait: Boolean = false): OverlayState? {
        val normalizedScopeId = normalizeScopeId(scopeId)
        if (normalizedScopeId.isEmpty() || !hasGameOverride(context, normalizedScopeId)) {
            return null
        }
        val globalState = loadGlobalState(context, portrait)
        return loadScopeState(preferences(context), normalizedScopeId, globalState, portrait)
    }'''
    ),
    (
        "fun resolveState(context: Context, scopeId: String?, allowGameOverride: Boolean): OverlayState",
        '''fun resolveState(
        context: Context,
        scopeId: String?,
        allowGameOverride: Boolean,
        portrait: Boolean = false
    ): OverlayState {
        val normalizedScopeId = normalizeScopeId(scopeId)
        val globalState = loadGlobalState(context, portrait)
        if (!allowGameOverride || normalizedScopeId.isEmpty() || !hasGameOverride(context, normalizedScopeId)) {
            return globalState
        }
        return loadScopeState(preferences(context), normalizedScopeId, globalState, portrait)
    }'''
    ),
    (
        "fun saveGlobalState(context: Context, state: OverlayState)",
        '''fun saveGlobalState(context: Context, state: OverlayState, portrait: Boolean = false) {
        saveScopeState(context, scopeId = null, state = state, markOverride = false, portrait = portrait)
    }'''
    ),
    (
        "fun saveGameOverride(context: Context, scopeId: String?, state: OverlayState)",
        '''fun saveGameOverride(context: Context, scopeId: String?, state: OverlayState, portrait: Boolean = false) {
        val normalizedScopeId = normalizeScopeId(scopeId)
        if (normalizedScopeId.isEmpty()) {
            saveGlobalState(context, state, portrait)
            return
        }
        saveScopeState(context, normalizedScopeId, state, markOverride = true, portrait = portrait)
    }'''
    ),
    (
        "private fun loadScopeState(",
        '''private fun loadScopeState(
        prefs: SharedPreferences,
        scopeId: String?,
        fallback: OverlayState,
        portrait: Boolean
    ): OverlayState {
        val normalizedScopeId = normalizeScopeId(scopeId)
        val layout = loadStoredLayout(prefs, normalizedScopeId, fallback.layout, portrait)
        return OverlayState(
            config = loadStoredConfig(prefs, normalizedScopeId, fallback.config),
            layout = layout
        )
    }'''
    ),
    (
        "private fun saveScopeState(",
        '''private fun saveScopeState(
        context: Context,
        scopeId: String?,
        state: OverlayState,
        markOverride: Boolean,
        portrait: Boolean
    ) {
        val normalizedScopeId = normalizeScopeId(scopeId)
        val normalizedState = OverlayState(
            config = state.config.normalized(),
            layout = state.layout.normalized()
        )

        preferences(context).edit().apply {
            putInt(configKey(normalizedScopeId, KEY_OVERLAY_MASK), normalizedState.config.overlayMask)
            putInt(configKey(normalizedScopeId, KEY_OVERLAY_SCALE), normalizedState.config.overlayScale)
            putInt(configKey(normalizedScopeId, KEY_OVERLAY_OPACITY), normalizedState.config.overlayOpacity)
            putBoolean(
                configKey(normalizedScopeId, KEY_HIDE_ON_CONTROLLER),
                normalizedState.config.hideOverlayWhenControllerConnected
            )
            saveLayoutEntries(this, normalizedScopeId, normalizedState.layout, portrait)
            if (markOverride && normalizedScopeId.isNotEmpty()) {
                putBoolean(overrideEnabledKey(normalizedScopeId), true)
            }
            apply()
        }
    }'''
    ),
    (
        "private fun loadStoredLayout(",
        '''private fun loadStoredLayout(
        prefs: SharedPreferences,
        scopeId: String,
        fallback: OverlayLayout,
        portrait: Boolean
    ): OverlayLayout {
        val anyEntryPresent = defaultEntries.any { entry ->
            prefs.contains(positionKey(scopeId, entry.buttonType, KEY_POSITION_X_SUFFIX, portrait)) &&
                prefs.contains(positionKey(scopeId, entry.buttonType, KEY_POSITION_Y_SUFFIX, portrait))
        }
        if (!anyEntryPresent) {
            return fallback
        }

        val positions = defaultEntries.associate { entry ->
            val fallbackPosition = fallback.positionFor(entry.buttonType) ?: OverlayPosition(0f, 0f)
            entry.buttonType to OverlayPosition(
                normalizedX = prefs.getFloat(
                    positionKey(scopeId, entry.buttonType, KEY_POSITION_X_SUFFIX, portrait),
                    fallbackPosition.normalizedX
                ).coerceNormalizedCoordinate(),
                normalizedY = prefs.getFloat(
                    positionKey(scopeId, entry.buttonType, KEY_POSITION_Y_SUFFIX, portrait),
                    fallbackPosition.normalizedY
                ).coerceNormalizedCoordinate()
            )
        }
        return OverlayLayout(positions).normalized()
    }'''
    ),
    (
        "private fun legacyGlobalState(context: Context): OverlayState",
        '''private fun legacyGlobalState(context: Context, portrait: Boolean): OverlayState {
        val defaultState = defaultState(context, portrait)
        val legacyConfigPrefs = context.applicationContext.getSharedPreferences("emulation_session", Context.MODE_PRIVATE)
        val config = if (legacyConfigPrefs.contains(KEY_OVERLAY_MASK)) {
            OverlayConfig(
                overlayMask = legacyConfigPrefs.getInt(KEY_OVERLAY_MASK, defaultState.config.overlayMask),
                overlayScale = legacyConfigPrefs.getInt(KEY_OVERLAY_SCALE, defaultState.config.overlayScale),
                overlayOpacity = legacyConfigPrefs.getInt(KEY_OVERLAY_OPACITY, defaultState.config.overlayOpacity),
                hideOverlayWhenControllerConnected = legacyConfigPrefs.getBoolean(
                    KEY_HIDE_ON_CONTROLLER,
                    defaultState.config.hideOverlayWhenControllerConnected
                )
            ).normalized()
        } else {
            defaultState.config
        }

        // The legacy coordinate format was landscape-only. Give portrait its own safe defaults.
        val legacyLayout = if (portrait) defaultState.layout else loadLegacyGlobalLayout(context, defaultState.layout)
        return OverlayState(config = config, layout = legacyLayout)
    }'''
    ),
    (
        "private fun saveLayoutEntries(",
        '''private fun saveLayoutEntries(
        editor: SharedPreferences.Editor,
        scopeId: String,
        layout: OverlayLayout,
        portrait: Boolean
    ) {
        defaultEntries.forEach { entry ->
            val position = layout.positionFor(entry.buttonType) ?: OverlayPosition(0f, 0f)
            editor.putFloat(positionKey(scopeId, entry.buttonType, KEY_POSITION_X_SUFFIX, portrait), position.normalizedX)
            editor.putFloat(positionKey(scopeId, entry.buttonType, KEY_POSITION_Y_SUFFIX, portrait), position.normalizedY)
        }
    }'''
    ),
    (
        "private fun removeScopePayload(",
        '''private fun removeScopePayload(editor: SharedPreferences.Editor, scopeId: String) {
        editor.remove(configKey(scopeId, KEY_OVERLAY_MASK))
        editor.remove(configKey(scopeId, KEY_OVERLAY_SCALE))
        editor.remove(configKey(scopeId, KEY_OVERLAY_OPACITY))
        editor.remove(configKey(scopeId, KEY_HIDE_ON_CONTROLLER))
        defaultEntries.forEach { entry ->
            listOf(false, true).forEach { portrait ->
                editor.remove(positionKey(scopeId, entry.buttonType, KEY_POSITION_X_SUFFIX, portrait))
                editor.remove(positionKey(scopeId, entry.buttonType, KEY_POSITION_Y_SUFFIX, portrait))
            }
        }
    }'''
    ),
]

for signature, replacement in replacements:
    s, found = replace_braced_function(s, signature, replacement)
    if not found:
        raise SystemExit(f"Could not update OverlayStore function: {signature}")

s = replace_once(
    s,
    "fun loadLayout(context: Context, scopeId: String? = null, allowGameOverride: Boolean = false): OverlayLayout =\n        resolveState(context, scopeId, allowGameOverride).layout",
    "fun loadLayout(context: Context, scopeId: String? = null, allowGameOverride: Boolean = false, portrait: Boolean = false): OverlayLayout =\n        resolveState(context, scopeId, allowGameOverride, portrait).layout",
    "orientation-aware loadLayout"
)

s = replace_once(
    s,
    '''private fun positionKey(scopeId: String?, buttonType: Int, suffix: String): String =
        scopePrefix(scopeId) + ":" + KEY_LAYOUT_PREFIX + ":landscape:" + buttonType + suffix''',
    '''private fun positionKey(scopeId: String?, buttonType: Int, suffix: String, portrait: Boolean = false): String =
        scopePrefix(scopeId) + ":" + KEY_LAYOUT_PREFIX + ":" + (if (portrait) "portrait" else "landscape") + ":" + buttonType + suffix''',
    "orientation-specific positionKey"
)
# Overload Java-facing APIs; annotations are harmless for Kotlin callers.
STORE.write_text(s)


# ---------------------------------------------------------------------------
# InputOverlay.java: load/edit/save the layout belonging to the active mode.
# ---------------------------------------------------------------------------
s = INPUT.read_text()
if "private boolean mPortraitLayout;" not in s:
    s = replace_once(s, "  private OverlayLayout mLayout;", "  private OverlayLayout mLayout;\n  private boolean mPortraitLayout;\n  private String mOverlayScopeId = \"\";", "InputOverlay orientation fields")
if "import android.content.res.Configuration;" not in s:
    s = replace_once(s, "import android.content.Context;", "import android.content.Context;\nimport android.content.res.Configuration;", "InputOverlay Configuration import")

s = replace_once(
    s,
    "    applyResolvedState(OverlayStore.loadGlobalState(getContext()), false);",
    "    mPortraitLayout = getResources().getConfiguration().orientation == Configuration.ORIENTATION_PORTRAIT;\n    applyResolvedState(OverlayStore.loadGlobalState(getContext(), mPortraitLayout), false);",
    "orientation-aware InputOverlay initialization"
)

s = replace_braced_function(
    s,
    "public void refreshOverlayScope(String scopeId)",
    '''public void refreshOverlayScope(String scopeId)
  {
    mOverlayScopeId = scopeId != null ? scopeId : "";
    boolean allowGameOverride = OverlayStore.hasGameOverride(getContext(), mOverlayScopeId);
    OverlayState state = OverlayStore.resolveState(getContext(), mOverlayScopeId, allowGameOverride, mPortraitLayout);
    applyResolvedState(state, true);
  }'''
)[0]

if "public void setLayoutOrientation(boolean portrait)" not in s:
    anchor = "  public void rebindController()"
    method = '''  public void setLayoutOrientation(boolean portrait)
  {
    if (mPortraitLayout == portrait)
      return;
    mPortraitLayout = portrait;
    refreshOverlayScope(mOverlayScopeId);
  }

  public boolean isPortraitLayout()
  {
    return mPortraitLayout;
  }

'''
    s = replace_once(s, anchor, method + anchor, "InputOverlay.setLayoutOrientation insertion")

s = s.replace("OverlayStore.defaultLayout(getContext())", "OverlayStore.defaultLayout(getContext(), mPortraitLayout)")
s = replace_once(s, "OverlayStore.defaultState(getContext())", "OverlayStore.defaultState(getContext(), mPortraitLayout)", "InputOverlay default state orientation")
INPUT.write_text(s)


# ---------------------------------------------------------------------------
# Emulator.java: display scale/position preferences, menu layering, orientation.
# ---------------------------------------------------------------------------
s = EMU.read_text()
if "public int getPortraitGameScale()" not in s:
    anchor = "    private void applyRequestedDisplayOrientation() {"
    methods = '''    private static final String KEY_PORTRAIT_GAME_SCALE = "portrait_game_scale";
    private static final String KEY_PORTRAIT_GAME_OFFSET = "portrait_game_offset";

    public int getPortraitGameScale() {
        return getSharedPreferences(DISPLAY_PREFERENCES, MODE_PRIVATE)
                .getInt(KEY_PORTRAIT_GAME_SCALE, 100);
    }

    public int getPortraitGameOffset() {
        return getSharedPreferences(DISPLAY_PREFERENCES, MODE_PRIVATE)
                .getInt(KEY_PORTRAIT_GAME_OFFSET, 0);
    }

    public void setPortraitDisplaySettings(int scalePercent, int offsetPercent) {
        getSharedPreferences(DISPLAY_PREFERENCES, MODE_PRIVATE).edit()
                .putInt(KEY_PORTRAIT_GAME_SCALE, Math.max(70, Math.min(100, scalePercent)))
                .putInt(KEY_PORTRAIT_GAME_OFFSET, Math.max(0, Math.min(100, offsetPercent)))
                .apply();
        runOnUiThread(this::applyPortraitSplitLayout);
    }

'''
    s = replace_once(s, anchor, methods + anchor, "Emulator display preference methods")

# Ensure SDL calls into the Android orientation setter on the UI thread.
s, found = replace_braced_function(
    s,
    "public void setOrientationBis(int w, int h, boolean resizable, String hint)",
    '''public void setOrientationBis(int w, int h, boolean resizable, String hint) {
        runOnUiThread(this::applyRequestedDisplayOrientation);
    }'''
)
if not found:
    raise SystemExit("Combined patch's SDL setOrientationBis override was not found")

# Let the controller view choose the corresponding saved control layout.
if "overlay.setLayoutOrientation(enabled);" not in s:
    s = replace_once(
        s,
        "            if (mSurface != null) {\n                mSurface.setPortraitSplitMode(enabled);\n            }",
        "            if (mSurface != null) {\n                mSurface.setPortraitSplitMode(enabled);\n                if (mSurface.getmOverlay() != null) {\n                    mSurface.getmOverlay().setLayoutOrientation(enabled);\n                }\n            }",
        "Emulator orientation preference overlay update"
    )

# Replace the split layout routine with adjustable game size/vertical placement.
s, found = replace_braced_function(
    s,
    "private void applyPortraitSplitLayout()",
    '''private void applyPortraitSplitLayout() {
        if (portraitSplitRoot == null || mSurface == null) {
            return;
        }
        InputOverlay overlay = getmOverlay();
        if (overlay == null) {
            return;
        }
        int rootWidth = portraitSplitRoot.getWidth();
        int rootHeight = portraitSplitRoot.getHeight();
        if (rootWidth <= 0 || rootHeight <= 1) {
            return;
        }

        boolean portrait = isPortraitLayoutEnabled();
        mSurface.setPortraitSplitMode(portrait);
        overlay.setLayoutOrientation(portrait);

        int gameWidth;
        int gameHeight;
        int gameTop;
        int controlsHeight;
        RelativeLayout.LayoutParams surfaceParams;
        RelativeLayout.LayoutParams overlayParams;

        if (portrait) {
            int scale = getPortraitGameScale();
            int offset = getPortraitGameOffset();
            gameWidth = Math.max(1, Math.min(rootWidth, Math.round(rootWidth * (scale / 100f))));
            gameHeight = Math.max(1, Math.round(gameWidth / VITA_DISPLAY_ASPECT_RATIO));
            int minimumControlsHeight = Math.max(1, Math.round(rootWidth * 0.70f));
            int maxTop = Math.max(0, rootHeight - gameHeight - minimumControlsHeight);
            gameTop = Math.round(maxTop * (offset / 100f));
            controlsHeight = Math.max(1, rootHeight - gameTop - gameHeight);

            surfaceParams = new RelativeLayout.LayoutParams(gameWidth, gameHeight);
            surfaceParams.addRule(RelativeLayout.CENTER_HORIZONTAL);
            surfaceParams.addRule(RelativeLayout.ALIGN_PARENT_TOP);
            surfaceParams.topMargin = gameTop;

            overlayParams = new RelativeLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, controlsHeight);
            overlayParams.addRule(RelativeLayout.ALIGN_PARENT_BOTTOM);
        } else {
            gameWidth = rootWidth;
            gameHeight = rootHeight;
            gameTop = 0;
            controlsHeight = rootHeight;
            surfaceParams = new RelativeLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
            overlayParams = new RelativeLayout.LayoutParams(
                    ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
            overlayParams.addRule(RelativeLayout.ALIGN_PARENT_TOP);
        }

        surfaceParams.addRule(RelativeLayout.ALIGN_PARENT_LEFT, 0);
        ViewGroup.LayoutParams oldSurfaceParams = mSurface.getLayoutParams();
        if (!(oldSurfaceParams instanceof RelativeLayout.LayoutParams)
                || oldSurfaceParams.width != surfaceParams.width
                || oldSurfaceParams.height != surfaceParams.height
                || ((RelativeLayout.LayoutParams) oldSurfaceParams).topMargin != surfaceParams.topMargin) {
            mSurface.setLayoutParams(surfaceParams);
        }

        overlayParams.addRule(RelativeLayout.ALIGN_PARENT_LEFT);
        ViewGroup.LayoutParams oldOverlayParams = overlay.getLayoutParams();
        if (!(oldOverlayParams instanceof RelativeLayout.LayoutParams)
                || oldOverlayParams.width != overlayParams.width
                || oldOverlayParams.height != overlayParams.height) {
            overlay.setLayoutParams(overlayParams);
        }
        overlay.bringToFront();
    }'''
)
if not found:
    raise SystemExit("Combined patch's applyPortraitSplitLayout method was not found")

# Hide the SurfaceView when the pause menu disables controls. This allows the full-screen
# Compose pause menu to render over the whole phone rather than beneath the controller surface.
s, found = replace_braced_function(
    s,
    "public void setControllerOverlayState(int overlay_mask, boolean edit, boolean reset)",
    '''public void setControllerOverlayState(int overlay_mask, boolean edit, boolean reset){
        InputOverlay overlay = getmOverlay();
        if (overlay == null)
            return;

        overlay.setState(overlay_mask);
        overlay.setIsInEditMode(edit);
        overlay.setVisibility((overlay_mask == 0 && !edit) ? View.GONE : View.VISIBLE);

        if(reset)
            overlay.resetButtonPlacement();
    }'''
)
if not found:
    raise SystemExit("Could not update setControllerOverlayState for pause-menu layering")

# Give Compose overlays a high drawing elevation and retain full-root sizing.
s = s.replace(
    "        pauseMenuView.setVisibility(View.GONE);\n        contentView.addView(pauseMenuView);",
    "        pauseMenuView.setVisibility(View.GONE);\n        pauseMenuView.setElevation(1000f);\n        contentView.addView(pauseMenuView);",
    1
)
s = s.replace(
    "        if (pauseMenuView != null) {\n            pauseMenuView.bringToFront();\n        }",
    "        if (pauseMenuView != null) {\n            pauseMenuView.bringToFront();\n            pauseMenuView.setElevation(1000f);\n        }",
    1
)
EMU.write_text(s)


# ---------------------------------------------------------------------------
# EmulationSessionViewModel.kt: persist/load the active orientation's layout.
# ---------------------------------------------------------------------------
s = SESSION_VM.read_text()
if "private fun isPortraitLayoutEnabled(): Boolean" not in s:
    anchor = "    private var initialized = false"
    helper = '''    private fun isPortraitLayoutEnabled(): Boolean =
        getApplication<Application>()
            .getSharedPreferences("display_layout_preferences", android.content.Context.MODE_PRIVATE)
            .getBoolean("portrait_layout_enabled", true)

'''
    s = replace_once(s, anchor, helper + anchor, "session VM display preference helper")
s = s.replace("OverlayStore.defaultLayout(getApplication())", "OverlayStore.defaultLayout(getApplication(), isPortraitLayoutEnabled())")
s = s.replace(
    "OverlayStore.resolveState(\n            context = getApplication(),\n            scopeId = titleId,\n            allowGameOverride = useGameOverride\n        )",
    "OverlayStore.resolveState(\n            context = getApplication(),\n            scopeId = titleId,\n            allowGameOverride = useGameOverride,\n            portrait = isPortraitLayoutEnabled()\n        )"
)
s = s.replace(
    "OverlayStore.saveGameOverride(getApplication(), titleId, captureOverlayState(emulator))",
    "OverlayStore.saveGameOverride(getApplication(), titleId, captureOverlayState(emulator), isPortraitLayoutEnabled())"
)
s = s.replace(
    "OverlayStore.saveGameOverride(getApplication(), uiState.titleId, state)",
    "OverlayStore.saveGameOverride(getApplication(), uiState.titleId, state, isPortraitLayoutEnabled())"
)
s = s.replace(
    "OverlayStore.saveGlobalState(getApplication(), state)",
    "OverlayStore.saveGlobalState(getApplication(), state, isPortraitLayoutEnabled())"
)
SESSION_VM.write_text(s)


# ---------------------------------------------------------------------------
# OverlayLayoutEditorDialog.kt: preview portrait controls only in the lower region.
# ---------------------------------------------------------------------------
s = EDITOR.read_text()
if "portraitMode: Boolean" not in s:
    s = replace_once(
        s,
        "    overlayLayout: OverlayLayout,\n    onDismiss: (OverlayLayout) -> Unit",
        "    overlayLayout: OverlayLayout,\n    portraitMode: Boolean = false,\n    onDismiss: (OverlayLayout) -> Unit",
        "portrait-aware layout editor parameter"
    )
s = s.replace("    ImmersiveLandscapeEffect(activity = activity)", "    ImmersiveLandscapeEffect(activity = activity, enabled = !portraitMode)")
# Replace the AndroidView block so portrait edit mode reserves the Vita screen area above the controls.
old_block = '''    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        AndroidView(
            factory = { viewContext ->
                InputOverlay(viewContext).apply {
                    overlayView = this
                    setLayout(overlayLayout)
                    setAllowVirtualController(false)
                    setAutoHideEnabled(false)
                    setIsInEditMode(true)
                    setScale(overlayConfig.overlayScale / 100f)
                    setOpacity(overlayConfig.overlayOpacity)
                    setState(overlayConfig.activeMask())
                }
            },
            update = { view ->
                overlayView = view
                view.setLayout(overlayLayout)
                view.setAllowVirtualController(false)
                view.setAutoHideEnabled(false)
                view.setIsInEditMode(true)
                view.setScale(overlayConfig.overlayScale / 100f)
                view.setOpacity(overlayConfig.overlayOpacity)
                view.setState(overlayConfig.activeMask())
            },
            modifier = Modifier.fillMaxSize()
        )

        OverlayEditorPalette(
            onDone = ::finishEditor,
            onReset = {
                overlayView?.setLayout(OverlayStore.defaultLayout(context))
            }
        )
    }'''
new_block = '''    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black)
    ) {
        if (portraitMode) {
            androidx.compose.foundation.layout.Column(Modifier.fillMaxSize()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(0.26f)
                        .background(Color(0xFF171C26)),
                    contentAlignment = Alignment.Center
                ) {
                    androidx.compose.material3.Text(
                        text = "GAME DISPLAY PREVIEW",
                        color = Color.White.copy(alpha = 0.72f)
                    )
                }
                AndroidView(
                    factory = { viewContext ->
                        InputOverlay(viewContext).apply {
                            setZOrderMediaOverlay(false)
                            overlayView = this
                            setLayoutOrientation(true)
                            setLayout(overlayLayout)
                            setAllowVirtualController(false)
                            setAutoHideEnabled(false)
                            setIsInEditMode(true)
                            setScale(overlayConfig.overlayScale / 100f)
                            setOpacity(overlayConfig.overlayOpacity)
                            setState(overlayConfig.activeMask())
                        }
                    },
                    update = { view ->
                        overlayView = view
                        view.setZOrderMediaOverlay(false)
                        view.setLayoutOrientation(true)
                        view.setLayout(overlayLayout)
                        view.setAllowVirtualController(false)
                        view.setAutoHideEnabled(false)
                        view.setIsInEditMode(true)
                        view.setScale(overlayConfig.overlayScale / 100f)
                        view.setOpacity(overlayConfig.overlayOpacity)
                        view.setState(overlayConfig.activeMask())
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(0.74f)
                )
            }
        } else {
            AndroidView(
                factory = { viewContext ->
                    InputOverlay(viewContext).apply {
                        setZOrderMediaOverlay(false)
                        overlayView = this
                        setLayoutOrientation(false)
                        setLayout(overlayLayout)
                        setAllowVirtualController(false)
                        setAutoHideEnabled(false)
                        setIsInEditMode(true)
                        setScale(overlayConfig.overlayScale / 100f)
                        setOpacity(overlayConfig.overlayOpacity)
                        setState(overlayConfig.activeMask())
                    }
                },
                update = { view ->
                    overlayView = view
                    view.setZOrderMediaOverlay(false)
                    view.setLayoutOrientation(false)
                    view.setLayout(overlayLayout)
                    view.setAllowVirtualController(false)
                    view.setAutoHideEnabled(false)
                    view.setIsInEditMode(true)
                    view.setScale(overlayConfig.overlayScale / 100f)
                    view.setOpacity(overlayConfig.overlayOpacity)
                    view.setState(overlayConfig.activeMask())
                },
                modifier = Modifier.fillMaxSize()
            )
        }

        OverlayEditorPalette(
            onDone = ::finishEditor,
            onReset = {
                overlayView?.setLayout(OverlayStore.defaultLayout(context, portraitMode))
            }
        )
    }'''
if old_block in s:
    s = s.replace(old_block, new_block, 1)
elif "GAME DISPLAY PREVIEW" not in s:
    raise SystemExit("Could not find OverlayLayoutEditorDialog AndroidView block")
# Imports needed by the split portrait editor preview.
if "import androidx.compose.ui.Alignment" not in s:
    s = replace_once(s, "import androidx.compose.ui.Modifier", "import androidx.compose.ui.Modifier\nimport androidx.compose.ui.Alignment", "editor Alignment import")
if "import androidx.compose.foundation.layout.fillMaxWidth" not in s:
    s = replace_once(s, "import androidx.compose.foundation.layout.fillMaxSize", "import androidx.compose.foundation.layout.fillMaxSize\nimport androidx.compose.foundation.layout.fillMaxWidth", "editor fillMaxWidth import")
EDITOR.write_text(s)


# ---------------------------------------------------------------------------
# Settings model: add a Display category to global settings only.
# ---------------------------------------------------------------------------
s = SETTINGS_MODELS.read_text()
if "Display(R.string.settings_tab_display" not in s:
    s = replace_once(
        s,
        "    Controls(R.string.settings_tab_controls, Icons.Default.TouchApp),",
        "    Display(R.string.settings_tab_display, Icons.Default.Tune),\n    Controls(R.string.settings_tab_controls, Icons.Default.TouchApp),",
        "Display settings category"
    )
s = replace_once(
    s,
    "SettingsCategory.entries.filter { it != SettingsCategory.Camera && it != SettingsCategory.Interface }",
    "SettingsCategory.entries.filter { it != SettingsCategory.Camera && it != SettingsCategory.Interface && it != SettingsCategory.Display }",
    "hide Display settings from per-app configs"
)
SETTINGS_MODELS.write_text(s)


# ---------------------------------------------------------------------------
# SettingsSections.kt: Display page with orientation, game size and position.
# ---------------------------------------------------------------------------
s = SETTINGS_SECTIONS.read_text()
# Add the five display parameters to SettingsCategoryBody with safe defaults for other callers.
if "displayPortraitMode: Boolean" not in s:
    anchor = "    connectedGamepads: List<ConnectedGamepad> = emptyList(),\n    onShowHelp: (SettingsHelpEntry) -> Unit"
    repl = "    connectedGamepads: List<ConnectedGamepad> = emptyList(),\n    displayPortraitMode: Boolean = true,\n    onDisplayPortraitModeChange: (Boolean) -> Unit = {},\n    portraitDisplayScale: Int = 100,\n    onPortraitDisplayScaleChange: (Int) -> Unit = {},\n    portraitDisplayOffset: Int = 0,\n    onPortraitDisplayOffsetChange: (Int) -> Unit = {},\n    onShowHelp: (SettingsHelpEntry) -> Unit"
    s = replace_once(s, anchor, repl, "SettingsCategoryBody display arguments")

if "SettingsCategory.Display -> DisplaySettingsSection(" not in s:
    anchor = "        SettingsCategory.Controls -> OverlaySettingsSection("
    branch = '''        SettingsCategory.Display -> DisplaySettingsSection(
            portraitMode = displayPortraitMode,
            onPortraitModeChange = onDisplayPortraitModeChange,
            gameScale = portraitDisplayScale,
            onGameScaleChange = onPortraitDisplayScaleChange,
            gameOffset = portraitDisplayOffset,
            onGameOffsetChange = onPortraitDisplayOffsetChange,
            onShowHelp = onShowHelp
        )
'''
    s = replace_once(s, anchor, branch + anchor, "Display category rendering")

if "private fun DisplaySettingsSection(" not in s:
    helper = '''
@Composable
private fun DisplaySettingsSection(
    portraitMode: Boolean,
    onPortraitModeChange: (Boolean) -> Unit,
    gameScale: Int,
    onGameScaleChange: (Int) -> Unit,
    gameOffset: Int,
    onGameOffsetChange: (Int) -> Unit,
    onShowHelp: (SettingsHelpEntry) -> Unit
) {
    SettingsSectionCard(
        title = stringResource(R.string.settings_display_title),
        summary = null,
        help = null,
        onShowHelp = onShowHelp
    ) {
        SettingsChoiceField(
            title = stringResource(R.string.settings_display_orientation),
            options = listOf(
                stringResource(R.string.settings_display_portrait),
                stringResource(R.string.settings_display_landscape)
            ),
            selectedIndex = if (portraitMode) 0 else 1,
            onSelect = { onPortraitModeChange(it == 0) },
            help = SettingsHelpEntry(
                title = stringResource(R.string.settings_display_orientation),
                body = stringResource(R.string.settings_display_orientation_desc),
                scope = SettingsScope.Global
            ),
            onShowHelp = onShowHelp
        )

        if (portraitMode) {
            SettingsSliderRow(
                title = stringResource(R.string.settings_display_game_size),
                valueLabel = stringResource(R.string.settings_display_percent, gameScale),
                value = gameScale.toFloat(),
                onValueChange = { onGameScaleChange(it.toInt().coerceIn(70, 100)) },
                valueRange = 70f..100f,
                steps = 29,
                help = SettingsHelpEntry(
                    title = stringResource(R.string.settings_display_game_size),
                    body = stringResource(R.string.settings_display_game_size_desc),
                    scope = SettingsScope.Global
                ),
                onShowHelp = onShowHelp
            )
            SettingsSliderRow(
                title = stringResource(R.string.settings_display_game_position),
                valueLabel = stringResource(R.string.settings_display_percent, gameOffset),
                value = gameOffset.toFloat(),
                onValueChange = { onGameOffsetChange(it.toInt().coerceIn(0, 100)) },
                valueRange = 0f..100f,
                steps = 99,
                help = SettingsHelpEntry(
                    title = stringResource(R.string.settings_display_game_position),
                    body = stringResource(R.string.settings_display_game_position_desc),
                    scope = SettingsScope.Global
                ),
                onShowHelp = onShowHelp
            )
        }
    }
}

'''
    # Insert before the first section implementation, after SettingsCategoryBody.
    anchor = "@OptIn(ExperimentalLayoutApi::class)\n@Composable\nprivate fun CoreSettingsSection("
    s = replace_once(s, anchor, helper + anchor, "Display settings composable insertion")
SETTINGS_SECTIONS.write_text(s)


# ---------------------------------------------------------------------------
# SettingsRoute.kt: use orientation-specific layouts and wire Display settings.
# ---------------------------------------------------------------------------
s = SETTINGS_ROUTE.read_text()
if 'private const val DISPLAY_PREFERENCES' not in s:
    anchor = 'private val CUSTOM_DRIVER_MIME_TYPES = arrayOf('
    constants = '''private const val DISPLAY_PREFERENCES = "display_layout_preferences"
private const val KEY_PORTRAIT_LAYOUT = "portrait_layout_enabled"
private const val KEY_PORTRAIT_GAME_SCALE = "portrait_game_scale"
private const val KEY_PORTRAIT_GAME_OFFSET = "portrait_game_offset"

'''
    s = replace_once(s, anchor, constants + anchor, "SettingsRoute display preference constants")

if "var portraitMode by remember" not in s:
    anchor = "    val isPerApp = titleId != null\n"
    state = '''    val isPerApp = titleId != null
    val displayPreferences = remember(context) {
        context.getSharedPreferences(DISPLAY_PREFERENCES, android.content.Context.MODE_PRIVATE)
    }
    var portraitMode by remember(displayPreferences) {
        mutableStateOf(displayPreferences.getBoolean(KEY_PORTRAIT_LAYOUT, true))
    }
    var portraitGameScale by remember(displayPreferences) {
        mutableStateOf(displayPreferences.getInt(KEY_PORTRAIT_GAME_SCALE, 100).coerceIn(70, 100))
    }
    var portraitGameOffset by remember(displayPreferences) {
        mutableStateOf(displayPreferences.getInt(KEY_PORTRAIT_GAME_OFFSET, 0).coerceIn(0, 100))
    }
'''
    s = replace_once(s, anchor, state, "SettingsRoute orientation and viewport state")

s = s.replace("var overlayState by remember(titleId) { mutableStateOf(OverlayStore.defaultState(context)) }", "var overlayState by remember(titleId, portraitMode) { mutableStateOf(OverlayStore.defaultState(context, portraitMode)) }")
s = s.replace("var originalOverlayState by remember(titleId) { mutableStateOf(overlayState) }", "var originalOverlayState by remember(titleId, portraitMode) { mutableStateOf(overlayState) }")
s = s.replace("LaunchedEffect(settingsLoaded, titleId, viewModel.hasCustomConfig) {", "LaunchedEffect(settingsLoaded, titleId, viewModel.hasCustomConfig, portraitMode) {")
s = s.replace("allowGameOverride = isPerApp && OverlayStore.hasGameOverride(context, overlayScopeId)\n            )", "allowGameOverride = isPerApp && OverlayStore.hasGameOverride(context, overlayScopeId),\n                portrait = portraitMode\n            )")
s = s.replace("allowGameOverride = isPerApp && OverlayStore.hasGameOverride(context, overlayScopeId)\n        )", "allowGameOverride = isPerApp && OverlayStore.hasGameOverride(context, overlayScopeId),\n            portrait = portraitMode\n        )")
s = s.replace("OverlayStore.saveGameOverride(context, overlayScopeId, normalized)", "OverlayStore.saveGameOverride(context, overlayScopeId, normalized, portraitMode)")
s = s.replace("OverlayStore.saveGlobalState(context, normalized)", "OverlayStore.saveGlobalState(context, normalized, portraitMode)")
s = s.replace("OverlayStore.defaultLayout(context))", "OverlayStore.defaultLayout(context, portraitMode))")
s = s.replace("overlayState = OverlayStore.defaultState(context)", "overlayState = OverlayStore.defaultState(context, portraitMode)")
s = s.replace("                overlayLayout = overlayState.layout,\n                onDismiss =", "                overlayLayout = overlayState.layout,\n                portraitMode = portraitMode,\n                onDismiss =")

# Wire new parameters into SettingsCategoryBody.
body_anchor = "                connectedGamepads = connectedGamepads,\n                onShowHelp = onShowHelp"
body_repl = '''                connectedGamepads = connectedGamepads,
                displayPortraitMode = portraitMode,
                onDisplayPortraitModeChange = { enabled ->
                    portraitMode = enabled
                    displayPreferences.edit().putBoolean(KEY_PORTRAIT_LAYOUT, enabled).apply()
                },
                portraitDisplayScale = portraitGameScale,
                onPortraitDisplayScaleChange = { value ->
                    portraitGameScale = value.coerceIn(70, 100)
                    displayPreferences.edit().putInt(KEY_PORTRAIT_GAME_SCALE, portraitGameScale).apply()
                },
                portraitDisplayOffset = portraitGameOffset,
                onPortraitDisplayOffsetChange = { value ->
                    portraitGameOffset = value.coerceIn(0, 100)
                    displayPreferences.edit().putInt(KEY_PORTRAIT_GAME_OFFSET, portraitGameOffset).apply()
                },
                onShowHelp = onShowHelp'''
if body_anchor in s:
    s = s.replace(body_anchor, body_repl, 1)
elif "displayPortraitMode = portraitMode" not in s:
    raise SystemExit("Could not wire display settings into SettingsCategoryBody")
SETTINGS_ROUTE.write_text(s)


# ---------------------------------------------------------------------------
# SettingsSearch.kt: add discoverable Display search entries.
# ---------------------------------------------------------------------------
s = SETTINGS_SEARCH.read_text()
if "SettingsCategory.Display, R.string.settings_display_orientation" not in s:
    anchor = "        add(entry(SettingsCategory.Controls, R.string.settings_controls_show,"
    entries = '''        if (!isPerApp) {
            add(entry(SettingsCategory.Display, R.string.settings_display_orientation, R.string.settings_display_orientation_desc, scope = SettingsScope.Global, keywords = "portrait landscape split screen rotation"))
            add(entry(SettingsCategory.Display, R.string.settings_display_game_size, R.string.settings_display_game_size_desc, scope = SettingsScope.Global, keywords = "viewport zoom size"))
            add(entry(SettingsCategory.Display, R.string.settings_display_game_position, R.string.settings_display_game_position_desc, scope = SettingsScope.Global, keywords = "viewport position vertical offset"))
        }
'''
    s = replace_once(s, anchor, entries + anchor, "Display search entries")
SETTINGS_SEARCH.write_text(s)


# ---------------------------------------------------------------------------
# EmulationPauseMenu.kt: add viewport controls to the existing Session orientation.
# ---------------------------------------------------------------------------
s = PAUSE_MENU.read_text()
if "import androidx.compose.material3.Slider" not in s:
    s = replace_once(s, "import androidx.compose.material3.Surface", "import androidx.compose.material3.Surface\nimport androidx.compose.material3.Slider", "pause menu Slider import")
s = s.replace(
    "        DisplayOrientationSection(\n            portraitMode = portraitLayout,",
    "        DisplayOrientationSection(\n            activity = activity,\n            portraitMode = portraitLayout,",
    1
)
if "private fun DisplayOrientationSection(\n    activity: Emulator," not in s:
    old = '''private fun DisplayOrientationSection(
    portraitMode: Boolean,
    onSelect: (Boolean) -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.36f),
        contentColor = MaterialTheme.colorScheme.onSurface,
        shape = RoundedCornerShape(20.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text(
                text = "Screen orientation",
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold)
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                FilterChip(
                    selected = portraitMode,
                    onClick = { onSelect(true) },
                    modifier = Modifier.weight(1f),
                    colors = settingsFilterChipColors(),
                    label = { Text("Portrait") }
                )
                FilterChip(
                    selected = !portraitMode,
                    onClick = { onSelect(false) },
                    modifier = Modifier.weight(1f),
                    colors = settingsFilterChipColors(),
                    label = { Text("Landscape") }
                )
            }
            Text(
                text = if (portraitMode) {
                    "Game display at the top, virtual controls below."
                } else {
                    "Landscape game display with virtual controls overlaid."
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}'''
    new = '''private fun DisplayOrientationSection(
    activity: Emulator,
    portraitMode: Boolean,
    onSelect: (Boolean) -> Unit
) {
    var gameScale by remember(activity) { mutableStateOf(activity.portraitGameScale.toFloat()) }
    var gameOffset by remember(activity) { mutableStateOf(activity.portraitGameOffset.toFloat()) }

    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.36f),
        contentColor = MaterialTheme.colorScheme.onSurface,
        shape = RoundedCornerShape(20.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text(
                text = "Screen orientation",
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.SemiBold)
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                FilterChip(
                    selected = portraitMode,
                    onClick = { onSelect(true) },
                    modifier = Modifier.weight(1f),
                    colors = settingsFilterChipColors(),
                    label = { Text("Portrait") }
                )
                FilterChip(
                    selected = !portraitMode,
                    onClick = { onSelect(false) },
                    modifier = Modifier.weight(1f),
                    colors = settingsFilterChipColors(),
                    label = { Text("Landscape") }
                )
            }
            Text(
                text = if (portraitMode) {
                    "Game display at the top, virtual controls below."
                } else {
                    "Landscape game display with virtual controls overlaid."
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            if (portraitMode) {
                Text("Game image size: ${gameScale.toInt()}%", style = MaterialTheme.typography.labelLarge)
                Slider(
                    value = gameScale,
                    onValueChange = {
                        gameScale = it
                        activity.setPortraitDisplaySettings(it.toInt(), gameOffset.toInt())
                    },
                    valueRange = 70f..100f,
                    steps = 29
                )
                Text("Vertical position: ${gameOffset.toInt()}%", style = MaterialTheme.typography.labelLarge)
                Slider(
                    value = gameOffset,
                    onValueChange = {
                        gameOffset = it
                        activity.setPortraitDisplaySettings(gameScale.toInt(), it.toInt())
                    },
                    valueRange = 0f..100f,
                    steps = 99
                )
            }
        }
    }
}'''
    if old not in s:
        raise SystemExit("Could not find existing DisplayOrientationSection helper")
    s = s.replace(old, new, 1)
PAUSE_MENU.write_text(s)


# ---------------------------------------------------------------------------
# Embedded pause-menu settings should not show the main-app-only Display page.
# ---------------------------------------------------------------------------
if "filter { it != SettingsCategory.Controls && it != SettingsCategory.Display }" not in s:
    # Apply to the source separately below.
    pass
# Update only the categories in EmbeddedSettingsTab.
s = PAUSE_MENU.read_text()
s = s.replace(
    "settingsCategories(isPerApp = true).filter { it != SettingsCategory.Controls }",
    "settingsCategories(isPerApp = true).filter { it != SettingsCategory.Controls && it != SettingsCategory.Display }"
)
s = s.replace(
    "settingsCategories(isPerApp = false).filter { it != SettingsCategory.Controls }",
    "settingsCategories(isPerApp = false).filter { it != SettingsCategory.Controls && it != SettingsCategory.Display }"
)
PAUSE_MENU.write_text(s)


# ---------------------------------------------------------------------------
# strings.xml: labels and help for the new main-menu Display category.
# ---------------------------------------------------------------------------
s = STRINGS.read_text()
if 'name="settings_tab_display"' not in s:
    strings = '''
    <string name="settings_tab_display">Display</string>
    <string name="settings_display_title">Display layout</string>
    <string name="settings_display_orientation">Screen orientation</string>
    <string name="settings_display_portrait">Portrait split</string>
    <string name="settings_display_landscape">Landscape</string>
    <string name="settings_display_orientation_desc">Portrait places the landscape game image above a separate virtual control area. Landscape uses the normal full-screen game view.</string>
    <string name="settings_display_game_size">Game image size</string>
    <string name="settings_display_game_size_desc">Adjust the width of the landscape game image in portrait mode. The image keeps the Vita aspect ratio.</string>
    <string name="settings_display_game_position">Game image vertical position</string>
    <string name="settings_display_game_position_desc">Move the game image down within the upper part of the portrait screen while keeping room for the controls.</string>
    <string name="settings_display_percent">%1$d%%</string>
'''
    s = s.replace("</resources>", strings + "\n</resources>")
STRINGS.write_text(s)


# ---------------------------------------------------------------------------
# Gradle: build only the Redmi's ARM64 ABI instead of ARM64 + x86_64.
# ---------------------------------------------------------------------------
s = APP_GRADLE.read_text()
s = s.replace('abiFilters "arm64-v8a", "x86_64"', 'abiFilters "arm64-v8a"')
if 'abiFilters "arm64-v8a", "x86_64"' in s:
    raise SystemExit("Could not remove x86_64 from app ABI filters")
if 'abiFilters "arm64-v8a"' not in s:
    raise SystemExit("ARM64 ABI filter was not found after patching")
APP_GRADLE.write_text(s)


# ---------------------------------------------------------------------------
# Final sanity checks: refuse to report success if a critical hook is absent.
# ---------------------------------------------------------------------------
checks = {
    "portrait/landscape saved layouts": "positionKey(scopeId, entry.buttonType, KEY_POSITION_X_SUFFIX, portrait)" in STORE.read_text(),
    "portrait layout editor preview": "GAME DISPLAY PREVIEW" in EDITOR.read_text(),
    "main Settings Display category": "SettingsCategory.Display -> DisplaySettingsSection" in SETTINGS_SECTIONS.read_text(),
    "main Settings orientation preference": "KEY_PORTRAIT_LAYOUT" in SETTINGS_ROUTE.read_text(),
    "ARM64-only ABI filter": 'abiFilters "arm64-v8a"' in APP_GRADLE.read_text() and 'abiFilters "arm64-v8a", "x86_64"' not in APP_GRADLE.read_text(),
    "pause menu hides controller SurfaceView": "overlay.setVisibility((overlay_mask == 0 && !edit) ? View.GONE : View.VISIBLE);" in EMU.read_text(),
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise SystemExit("Patch did not pass these checks: " + ", ".join(failed))

MARKER.write_text("Applied successfully. Backups are in .portrait-layout-upgrade-backup.\n")
print("Portrait layout upgrade applied successfully.")
print("Changes:")
print("  - Independent portrait and landscape control positions")
print("  - Portrait control editor preview in the lower control area")
print("  - Main Settings > Display: orientation, game image size and vertical position")
print("  - Pause-menu Session: orientation, game image size and vertical position")
print("  - Pause menu now hides the controller SurfaceView while open")
print("  - Android build restricted to arm64-v8a")
print(f"Backups saved under: {BACKUP}")
print("Next: run git diff --check, then ./gradlew assembleReldebug from android/.")
