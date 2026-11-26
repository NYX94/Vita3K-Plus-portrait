
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export ANDROID_NDK_HOME="${ANDROID_NDK_HOME:-/home/codespace/android-sdk/ndk/29.0.14206865}"
export ANDROID_NDK_ROOT="$ANDROID_NDK_HOME"
export ANDROID_NDK="$ANDROID_NDK_HOME"
export CMAKE_BUILD_PARALLEL_LEVEL=1

if [[ ! -d "$ANDROID_NDK_HOME" ]]; then
    echo "ERROR: Android NDK not found: $ANDROID_NDK_HOME"
    exit 1
fi

VCPKG_CMAKE="$(find /workspaces /home/codespace /opt \
    -type f -path '*/scripts/buildsystems/vcpkg.cmake' \
    -print -quit 2>/dev/null || true)"

if [[ -z "$VCPKG_CMAKE" ]]; then
    echo "ERROR: vcpkg.cmake not found."
    exit 1
fi

export VCPKG_ROOT="${VCPKG_CMAKE%/scripts/buildsystems/vcpkg.cmake}"

LAST=0
if [[ -f .portrait-build-number ]]; then
    LAST="$(cat .portrait-build-number)"
    [[ "$LAST" =~ ^[0-9]+$ ]] || {
        echo "Invalid .portrait-build-number"
        exit 1
    }
fi

shopt -s nullglob
for apk in Vita3K-Plus-build-*.apk Vita3K-Plus-portrait-build-*.apk; do
    if [[ "$apk" =~ build-([0-9]+) ]]; then
        n=$((10#${BASH_REMATCH[1]}))
        if (( n > LAST )); then
            LAST=$n
        fi
    fi
done

NEXT=$((LAST + 1))
printf -v BUILD "%03d" "$NEXT"

APK="android/app/build/outputs/apk/relperf/app-relperf.apk"
DEST="Vita3K-Plus-portrait-build-${BUILD}-relperf.apk"

echo "Building Vita3K+ portrait #${BUILD}"

(
    cd android
    ./gradlew assembleRelperf \
        --no-daemon \
        --max-workers=1 \
        --no-parallel \
        -Dorg.gradle.jvmargs="-Xmx2g -XX:+UseParallelGC" \
        -PportraitBuildNumber="$BUILD"
) 2>&1 | tee "/tmp/vita3k-portrait-build-${BUILD}.log"

test -f "$APK" || {
    echo "APK was not generated."
    exit 1
}

cp "$APK" "$DEST"
printf '%s\n' "$NEXT" > .portrait-build-number

echo
echo "BUILD SUCCESSFUL"
echo "In-app identifier: Build #$BUILD"
ls -lh "$DEST"
sha256sum "$DEST"