package org.vita3k.emulator;

import android.content.Context;
import android.view.MotionEvent;
import android.view.SurfaceHolder;
import android.view.View;

import org.libsdl.app.SDLSurface;
import org.vita3k.emulator.overlay.InputOverlay;

public class EmuSurface extends SDLSurface {

    private InputOverlay mOverlay;
    private boolean mPortraitSplitMode;

    public InputOverlay getmOverlay() {
        return mOverlay;
    }

    public EmuSurface(Context context){
        super(context);
        mOverlay = new InputOverlay(context);
    }

    public void setPortraitSplitMode(boolean enabled) {
        mPortraitSplitMode = enabled;
    }

    @Override
    public void surfaceCreated(SurfaceHolder holder) {
        setSurfaceStatus(true);
        super.surfaceCreated(holder);
    }

    @Override
    public void surfaceDestroyed(SurfaceHolder holder) {
        setSurfaceStatus(false);
        super.surfaceDestroyed(holder);
    }

    @Override
    public boolean onTouch(View v, MotionEvent event) {
        // In split mode the overlay occupies its own view below the game surface.
        // Let InputOverlay receive its own local-coordinate events there; only forward
        // surface events to the overlay in the legacy full-screen-overlay layout.
        if (!mPortraitSplitMode && mOverlay.onTouch(v, event)) {
            // priority is given to the overlay
            return true;
        }

        return super.onTouch(v, event);
    }

    public native void setSurfaceStatus(boolean surface_present);
}
