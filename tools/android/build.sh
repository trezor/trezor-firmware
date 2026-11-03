#!/usr/bin/env bash
# Run inside nix-shell tools/android/shell.nix, with Python dependencies from uv.
set -euo pipefail

repo_dir=$(cd "$(dirname "$0")/../.." && pwd)
abi=${1:-arm64-v8a}
case "$abi" in
    arm64-v8a) target=aarch64-linux-android; compiler=aarch64-linux-android ;;
    x86_64) target=x86_64-linux-android; compiler=x86_64-linux-android ;;
    *) echo "Usage: $0 [arm64-v8a|x86_64]" >&2; exit 2 ;;
esac

: "${ANDROID_NDK_HOME:?Use nix-shell tools/android/shell.nix}"
: "${SDL3_SOURCE:?SDL3 source directory is required}"
: "${SDL3_IMAGE_SOURCE:?SDL3_image source directory is required}"
: "${ANDROID_PKG_CONFIG:?Unwrapped pkg-config is required}"
android_api=28
build_dir="$repo_dir/core/build/android/$abi"
prefix="$build_dir/prefix"
toolchain="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64"
cmake_args=(
    -G Ninja
    "-DCMAKE_TOOLCHAIN_FILE=$ANDROID_NDK_HOME/build/cmake/android.toolchain.cmake"
    "-DANDROID_ABI=$abi"
    "-DANDROID_PLATFORM=android-$android_api"
    -DCMAKE_BUILD_TYPE=Release
    "-DCMAKE_INSTALL_PREFIX=$prefix"
    -DCMAKE_INSTALL_LIBDIR=lib
)

cmake -S "$SDL3_SOURCE" -B "$build_dir/sdl" "${cmake_args[@]}" \
    -DSDL_SHARED=ON -DSDL_STATIC=OFF -DSDL_TEST_LIBRARY=OFF -DSDL_TESTS=OFF
cmake --build "$build_dir/sdl" --parallel "${CARGO_BUILD_JOBS:-4}"
cmake --install "$build_dir/sdl"

cmake -S "$SDL3_IMAGE_SOURCE" -B "$build_dir/sdl-image" "${cmake_args[@]}" \
    "-DCMAKE_FIND_ROOT_PATH=$prefix" "-DSDL3_DIR=$prefix/lib/cmake/SDL3" \
    -DBUILD_SHARED_LIBS=ON \
    -DSDLIMAGE_SAMPLES=OFF -DSDLIMAGE_TESTS=OFF -DSDLIMAGE_BACKEND_STB=ON \
    -DSDLIMAGE_PNG_LIBPNG=OFF \
    -DSDLIMAGE_AVIF=OFF -DSDLIMAGE_JXL=OFF -DSDLIMAGE_TIF=OFF -DSDLIMAGE_WEBP=OFF
cmake --build "$build_dir/sdl-image" --parallel "${CARGO_BUILD_JOBS:-4}"
cmake --install "$build_dir/sdl-image"
# Only target dependencies may be discovered by pkg-config. Host tools such as
# mpy-cross must continue to use the host compiler.
target_key=${target//-/_}
target_upper=${target_key^^}
export "CC_$target_key=$toolchain/bin/$compiler$android_api-clang"
export "AR_$target_key=$toolchain/bin/llvm-ar"
export "CARGO_TARGET_${target_upper}_LINKER=$toolchain/bin/$compiler$android_api-clang"
export "PKG_CONFIG_LIBDIR_$target_key=$prefix/lib/pkgconfig"
export "PKG_CONFIG_PATH_$target_key=$prefix/lib/pkgconfig"
export "PKG_CONFIG_$target_key=$ANDROID_PKG_CONFIG"
export "BINDGEN_EXTRA_CLANG_ARGS_$target_key=--sysroot=$toolchain/sysroot --target=$compiler$android_api"
export PKG_CONFIG_ALLOW_CROSS=1
export CARGO_BUILD_JOBS=${CARGO_BUILD_JOBS:-4}
export CARGO_PROFILE_DEV_DEBUG=${CARGO_PROFILE_DEV_DEBUG:-0}

cd "$repo_dir"
uv run xtask build firmware --emulator -m T2T1 -p test \
    --emulator-target "$target" --btc-only

# On Android, the firmware is linked as a shared library for SDLActivity. The
# launcher runs it as an executable for adb shell.
dist="$build_dir/dist"
cc="$toolchain/bin/$compiler$android_api-clang"
rm -rf "$dist"
mkdir -p "$dist"
cp "$repo_dir/core/build/artifacts/T2T1/firmware-emu" "$dist/libmain.so"
cp -L "$prefix"/lib/*.so* "$dist/"
"$cc" -O2 -Wall -Wextra -Werror -o "$dist/firmware-emu" \
    "$repo_dir/tools/android/launcher.c"
"$cc" -O2 -Wall -Wextra -Werror -o "$dist/udp-relay" \
    "$repo_dir/tools/android/udp_relay.c"
printf 'Android binaries: %s\n' "$dist"

# Build the APK with the SDK tools directly, from SDL's pinned Java sources.
platform="$ANDROID_HOME/platforms/android-35/android.jar"
build_tools="$ANDROID_HOME/build-tools/35.0.0"
apk_dir="$build_dir/apk"
apk="$build_dir/trezor-emulator.apk"
rm -rf "$apk_dir"
mkdir -p "$apk_dir/classes" "$apk_dir/lib/$abi"
javac -source 8 -target 8 -Xlint:-options -nowarn -bootclasspath "$platform" \
    -d "$apk_dir/classes" \
    "$SDL3_SOURCE"/android-project/app/src/main/java/org/libsdl/app/*.java \
    "$repo_dir/tools/android/apk/TrezorActivity.java"
find "$apk_dir/classes" -name '*.class' -print0 |
    xargs -0 "$build_tools/d8" --release --min-api "$android_api" \
        --lib "$platform" --output "$apk_dir"
"$build_tools/aapt2" link -o "$apk_dir/unsigned.apk" -I "$platform" \
    --manifest "$repo_dir/tools/android/apk/AndroidManifest.xml" \
    --min-sdk-version "$android_api" --target-sdk-version 35
cp "$dist"/lib*.so "$apk_dir/lib/$abi/"
(cd "$apk_dir" && zip -q unsigned.apk classes.dex lib/"$abi"/*.so)
"$build_tools/zipalign" -f 4 "$apk_dir/unsigned.apk" "$apk_dir/aligned.apk"
keystore="$repo_dir/core/build/android/debug.keystore"
if [ ! -f "$keystore" ]; then
    keytool -genkeypair -keystore "$keystore" -storepass android \
        -keypass android -alias androiddebugkey -keyalg RSA -keysize 2048 \
        -validity 10000 -dname "CN=Trezor Emulator Debug"
fi
"$build_tools/apksigner" sign --ks "$keystore" --ks-pass pass:android \
    --out "$apk" "$apk_dir/aligned.apk"
printf 'Android APK: %s\n' "$apk"
