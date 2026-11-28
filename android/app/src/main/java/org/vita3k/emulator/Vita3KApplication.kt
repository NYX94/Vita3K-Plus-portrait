package org.vita3k.emulator

import android.app.Application
import android.content.ComponentCallbacks2
import org.libsdl.app.SDLActivity
import org.vita3k.emulator.data.UiLanguages

class Vita3KApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        System.loadLibrary("Vita3K")
        SDLActivity.nativeSetenv("SDL_ANDROID_ALLOW_RECREATE_ACTIVITY", "1")
        UiLanguages.applyStored(this)
    }

    override fun onTrimMemory(level: Int) {
        super.onTrimMemory(level)
        if (level >= ComponentCallbacks2.TRIM_MEMORY_RUNNING_LOW) {
            NativeLib.notifyMemoryPressure(level)
        }
    }

    override fun onLowMemory() {
        super.onLowMemory()
        NativeLib.notifyMemoryPressure(ComponentCallbacks2.TRIM_MEMORY_COMPLETE)
    }
}
