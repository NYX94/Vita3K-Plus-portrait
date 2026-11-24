from pathlib import Path
import re
import shutil

ROOT = Path.cwd()
EMU = ROOT / "android/app/src/main/java/org/vita3k/emulator/Emulator.java"
SURFACE = ROOT / "android/app/src/main/java/org/vita3k/emulator/EmuSurface.java"
OVERLAY = ROOT / "android/app/src/main/java/org/vita3k/emulator/overlay/InputOverlay.java"
MENU = ROOT / "android/app/src/main/java/org/vita3k/emulator/ui/screens/emulation/EmulationPauseMenu.kt"
MANIFEST = ROOT / "android/app/src/main/AndroidManifest.xml"
VULKAN_SHADER_SOURCE = ROOT / "vita3k/shaders-builtin/vulkan"
VULKAN_ASSET_DEST = ROOT / "android/app/assets/shaders-builtin/vulkan"

for p in (EMU, SURFACE, OVERLAY, MENU, MANIFEST, VULKAN_SHADER_SOURCE):
    if not p.exists():
        raise SystemExit(f"Missing expected source file: {p}")

# Preserve the original source files on the first run so the patch is reversible.
backup_root = ROOT / ".portrait-toggle-backup"
for p in (EMU, SURFACE, OVERLAY, MENU, MANIFEST):
    backup = backup_root / p.relative_to(ROOT)
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(p, backup)

# Include the Vulkan SPIR-V binaries in the Android APK. This is the fix that
# resolved the missing shader modules seen in the Redmi crash report.
VULKAN_ASSET_DEST.mkdir(parents=True, exist_ok=True)
shader_files = sorted(VULKAN_SHADER_SOURCE.glob("*.spv"))
if not shader_files:
    raise SystemExit(f"No Vulkan .spv files found in {VULKAN_SHADER_SOURCE}")
for shader in shader_files:
    shutil.copy2(shader, VULKAN_ASSET_DEST / shader.name)
required_shaders = {"render_main.vert.spv", "render_main.frag.spv"}
missing_shaders = required_shaders - {p.name for p in shader_files}
if missing_shaders:
    raise SystemExit(f"Required Vulkan shaders are missing from source: {sorted(missing_shaders)}")
print(f"Copied {len(shader_files)} Vulkan shader binaries into Android assets.")


def replace_method(src: str, signature: str, replacement: str):
    """Replace a Java method body by matching balanced braces from its signature."""
    idx = src.find(signature)
    if idx < 0:
        return src, False
    brace = src.find("{", idx)
    if brace < 0:
        raise SystemExit(f"Could not find method body for: {signature}")
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
    raise SystemExit(f"Unbalanced braces while replacing: {signature}")

# --- Emulator.java: persistent mode + SDL orientation interception + dynamic split layout ---
s = EMU.read_text()
if "import android.content.pm.ActivityInfo;" not in s:
    anchor = "import android.content.Intent;"
    if anchor not in s:
        raise SystemExit("Could not find Android imports in Emulator.java")
    s = s.replace(anchor, anchor + "\nimport android.content.pm.ActivityInfo;", 1)

# Remove the earlier compile-time switch; layout is now controlled by a saved preference.
s = re.sub(r"^\s*private static final boolean PORTRAIT_SPLIT_LAYOUT\s*=\s*true;\s*\n", "", s, flags=re.M)
if "private static final float VITA_DISPLAY_ASPECT_RATIO" not in s:
    anchor = "    private static final long IME_RESTORE_DELAY_MS = 250L;"
    if anchor not in s:
        raise SystemExit("Could not find Emulator constants insertion point")
    s = s.replace(anchor, anchor + "\n    private static final float VITA_DISPLAY_ASPECT_RATIO = 960f / 544f;", 1)

field_anchor = "    private ImagePathResultCallback pendingImagePathCallback;"
if "private RelativeLayout portraitSplitRoot;" not in s:
    if field_anchor not in s:
        raise SystemExit("Could not find Emulator fields insertion point")
    s = s.replace(field_anchor, field_anchor + "\n    private RelativeLayout portraitSplitRoot;\n    private final View.OnLayoutChangeListener portraitSplitLayoutListener =\n            (view, left, top, right, bottom, oldLeft, oldTop, oldRight, oldBottom) ->\n                    applyPortraitSplitLayout();", 1)

# Add preference and orientation APIs once. The default is Portrait (the requested split design).
if "public boolean isPortraitLayoutEnabled()" not in s:
    getter_anchor = "    public InputOverlay getmOverlay() {\n        return mSurface != null ? mSurface.getmOverlay() : null;\n    }"
    if getter_anchor not in s:
        raise SystemExit("Could not find getmOverlay() insertion point")
    methods = getter_anchor + """

    private static final String DISPLAY_PREFERENCES = "display_layout_preferences";
    private static final String KEY_PORTRAIT_LAYOUT = "portrait_layout_enabled";

    public boolean isPortraitLayoutEnabled() {
        return getSharedPreferences(DISPLAY_PREFERENCES, MODE_PRIVATE)
                .getBoolean(KEY_PORTRAIT_LAYOUT, true);
    }

    public void setPortraitLayoutEnabled(boolean enabled) {
        getSharedPreferences(DISPLAY_PREFERENCES, MODE_PRIVATE).edit()
                .putBoolean(KEY_PORTRAIT_LAYOUT, enabled)
                .apply();
        runOnUiThread(() -> {
            applyRequestedDisplayOrientation();
            if (mSurface != null) {
                mSurface.setPortraitSplitMode(enabled);
            }
            applyPortraitSplitLayout();
        });
    }

    private void applyRequestedDisplayOrientation() {
        setRequestedOrientation(isPortraitLayoutEnabled()
                ? ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
                : ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
    }
"""
    s = s.replace(getter_anchor, methods, 1)

# If a previous attempt already added SDL's override, normalize it; otherwise add it.
orientation_method = """public void setOrientationBis(int w, int h, boolean resizable, String hint) {
        runOnUiThread(this::applyRequestedDisplayOrientation);
    }"""
if "public void setOrientationBis(int w, int h, boolean resizable, String hint)" in s:
    s, _ = replace_method(s, "public void setOrientationBis(int w, int h, boolean resizable, String hint)", orientation_method)
else:
    anchor = "    @Override\n    protected String[] getLibraries() {"
    if anchor not in s:
        raise SystemExit("Could not find insertion point for SDL orientation override")
    s = s.replace(anchor, "    @Override\n    " + orientation_method + "\n\n" + anchor, 1)

# The SDL root is a RelativeLayout. Keep both child views full-screen initially;
# applyPortraitSplitLayout() then chooses full-screen landscape or a top/bottom portrait split.
create_method = """protected SDLSurface createSDLSurface(Context context) {
        mSurface = new EmuSurface(context);
        mSurface.setPortraitSplitMode(isPortraitLayoutEnabled());
        mSurface.post(() -> {
            if (mSurface == null || !(mSurface.getParent() instanceof ViewGroup)) {
                return;
            }
            ViewGroup parent = (ViewGroup) mSurface.getParent();
            InputOverlay overlay = getmOverlay();
            if (overlay != null && overlay.getParent() == null) {
                if (parent instanceof RelativeLayout) {
                    parent.addView(overlay, new RelativeLayout.LayoutParams(
                            ViewGroup.LayoutParams.MATCH_PARENT,
                            ViewGroup.LayoutParams.MATCH_PARENT));
                } else {
                    parent.addView(overlay);
                }
            }
            if (parent instanceof RelativeLayout) {
                installPortraitSplitLayout(parent);
            }
            refreshControllerOverlayScope();
            refreshUiState(true);
        });
        return mSurface;
    }"""
s, found_create = replace_method(s, "protected SDLSurface createSDLSurface(Context context)", create_method)
if not found_create:
    raise SystemExit("Could not find createSDLSurface() in Emulator.java")

install_method = """private void installPortraitSplitLayout(ViewGroup parent) {
        if (!(parent instanceof RelativeLayout)) {
            Log.w(TAG, "Display layout requires SDL's RelativeLayout root");
            return;
        }
        RelativeLayout root = (RelativeLayout) parent;
        if (portraitSplitRoot != root) {
            if (portraitSplitRoot != null) {
                portraitSplitRoot.removeOnLayoutChangeListener(portraitSplitLayoutListener);
            }
            portraitSplitRoot = root;
            portraitSplitRoot.addOnLayoutChangeListener(portraitSplitLayoutListener);
        }
        applyPortraitSplitLayout();
    }"""
apply_method = """private void applyPortraitSplitLayout() {
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
        int gameHeight = portrait
                ? Math.max(1, Math.min(Math.round(rootWidth / VITA_DISPLAY_ASPECT_RATIO), rootHeight - 1))
                : rootHeight;
        int controlsHeight = portrait ? rootHeight - gameHeight : rootHeight;

        RelativeLayout.LayoutParams surfaceParams = new RelativeLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, gameHeight);
        surfaceParams.addRule(RelativeLayout.ALIGN_PARENT_TOP);
        surfaceParams.addRule(RelativeLayout.ALIGN_PARENT_LEFT);
        ViewGroup.LayoutParams oldSurfaceParams = mSurface.getLayoutParams();
        if (!(oldSurfaceParams instanceof RelativeLayout.LayoutParams)
                || oldSurfaceParams.width != surfaceParams.width
                || oldSurfaceParams.height != surfaceParams.height) {
            mSurface.setLayoutParams(surfaceParams);
        }

        RelativeLayout.LayoutParams overlayParams = new RelativeLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, controlsHeight);
        overlayParams.addRule(portrait ? RelativeLayout.ALIGN_PARENT_BOTTOM : RelativeLayout.ALIGN_PARENT_TOP);
        overlayParams.addRule(RelativeLayout.ALIGN_PARENT_LEFT);
        ViewGroup.LayoutParams oldOverlayParams = overlay.getLayoutParams();
        if (!(oldOverlayParams instanceof RelativeLayout.LayoutParams)
                || oldOverlayParams.width != overlayParams.width
                || oldOverlayParams.height != overlayParams.height) {
            overlay.setLayoutParams(overlayParams);
        }
        overlay.bringToFront();
    }"""

if "private void installPortraitSplitLayout(ViewGroup parent)" in s:
    s, _ = replace_method(s, "private void installPortraitSplitLayout(ViewGroup parent)", install_method)
else:
    s = s.replace(create_method, create_method + "\n\n    " + install_method, 1)
if "private void applyPortraitSplitLayout()" in s:
    s, _ = replace_method(s, "private void applyPortraitSplitLayout()", apply_method)
else:
    s = s.replace(install_method, install_method + "\n\n    " + apply_method, 1)

# Ensure the old static split flag is no longer referenced.
if "PORTRAIT_SPLIT_LAYOUT" in s:
    raise SystemExit("A legacy PORTRAIT_SPLIT_LAYOUT reference remains; refusing to write partial changes")

# Apply the saved preference as soon as the emulator activity is created.
on_create_anchor = "        super.onCreate(savedInstanceState);"
if "applyRequestedDisplayOrientation();" not in s[s.find("protected void onCreate(Bundle savedInstanceState)"):s.find("protected void onResume()") if "protected void onResume()" in s else len(s)]:
    if on_create_anchor not in s:
        raise SystemExit("Could not find Emulator onCreate() insertion point")
    s = s.replace(on_create_anchor, on_create_anchor + "\n        applyRequestedDisplayOrientation();", 1)

# Ensure listener cleanup in onDestroy.
cleanup_anchor = "        lifecycleRegistry.handleLifecycleEvent(Lifecycle.Event.ON_DESTROY);"
if "removeOnLayoutChangeListener(portraitSplitLayoutListener)" not in s:
    if cleanup_anchor not in s:
        raise SystemExit("Could not find onDestroy cleanup insertion point")
    s = s.replace(cleanup_anchor,
        "        if (portraitSplitRoot != null) {\n"
        "            portraitSplitRoot.removeOnLayoutChangeListener(portraitSplitLayoutListener);\n"
        "            portraitSplitRoot = null;\n"
        "        }\n" + cleanup_anchor, 1)

# Remove the compile-time manifest orientation lock; runtime preference now owns orientation.
m = MANIFEST.read_text()
m = re.sub(r'^\s*android:screenOrientation="portrait"\s*\n', "", m, flags=re.M)
MANIFEST.write_text(m)

EMU.write_text(s)

# --- EmuSurface.java: in portrait split mode the overlay gets its own local touch coordinates. ---
s = SURFACE.read_text()
if "private boolean mPortraitSplitMode;" not in s:
    s = s.replace("    private InputOverlay mOverlay;", "    private InputOverlay mOverlay;\n    private boolean mPortraitSplitMode;", 1)
if "public void setPortraitSplitMode(boolean enabled)" not in s:
    anchor = "    public EmuSurface(Context context){\n        super(context);\n        mOverlay = new InputOverlay(context);\n    }"
    if anchor not in s:
        raise SystemExit("Could not find EmuSurface constructor")
    s = s.replace(anchor, anchor + "\n\n    public void setPortraitSplitMode(boolean enabled) {\n        mPortraitSplitMode = enabled;\n    }", 1)
s = s.replace("if(mOverlay.onTouch(v, event)){", "if (!mPortraitSplitMode && mOverlay.onTouch(v, event)) {")
SURFACE.write_text(s)

# --- InputOverlay.java: transparent SurfaceView above the SDL game surface. ---
s = OVERLAY.read_text()
if "import android.graphics.PixelFormat;" not in s:
    anchor = "import android.graphics.Canvas;"
    if anchor not in s:
        raise SystemExit("Could not find Canvas import in InputOverlay.java")
    s = s.replace(anchor, anchor + "\nimport android.graphics.PixelFormat;", 1)
constructor_anchor = "    super(context/*, attrs*/);"
if "setZOrderMediaOverlay(true)" not in s:
    if constructor_anchor not in s:
        raise SystemExit("Could not find InputOverlay constructor")
    s = s.replace(constructor_anchor, constructor_anchor + "\n\n    // Keep virtual controls visible over the SDL SurfaceView with a transparent background.\n    getHolder().setFormat(PixelFormat.TRANSLUCENT);\n    setZOrderMediaOverlay(true);", 1)
OVERLAY.write_text(s)

# --- Pause menu: put a persisted orientation selector in the Session tab. ---
s = MENU.read_text()
session_start = s.find("private fun SessionTab(")
custom_start = s.find("private fun CustomConfigSection(", session_start)
if session_start < 0 or custom_start < 0:
    raise SystemExit("Could not locate SessionTab and CustomConfigSection in EmulationPauseMenu.kt")
session = s[session_start:custom_start]
if "DisplayOrientationSection(" not in session:
    state_anchor = "    val uiState = sessionViewModel.uiState"
    if state_anchor not in session:
        raise SystemExit("Could not find SessionTab state declaration")
    session = session.replace(state_anchor,
        state_anchor + "\n    var portraitLayout by remember(activity) { mutableStateOf(activity.isPortraitLayoutEnabled()) }", 1)
    insert_anchor = "        CustomConfigSection("
    if insert_anchor not in session:
        raise SystemExit("Could not find CustomConfigSection in SessionTab")
    selector = """        DisplayOrientationSection(
            portraitMode = portraitLayout,
            onSelect = { enabled ->
                portraitLayout = enabled
                activity.setPortraitLayoutEnabled(enabled)
            }
        )

"""
    session = session.replace(insert_anchor, selector + insert_anchor, 1)
    s = s[:session_start] + session + s[custom_start:]

if "private fun DisplayOrientationSection(" not in s:
    helper = """@Composable
private fun DisplayOrientationSection(
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
}

"""
    s = s.replace("@Composable\nprivate fun CustomConfigSection(", helper + "@Composable\nprivate fun CustomConfigSection(", 1)
MENU.write_text(s)

print("Updated successfully:")
for p in (EMU, SURFACE, OVERLAY, MENU, MANIFEST):
    print(f"  {p.relative_to(ROOT)}")
print("Portrait is the default mode. The Session tab now has Portrait and Landscape choices.")
print("Vulkan SPIR-V assets were copied for the next single APK build.")
