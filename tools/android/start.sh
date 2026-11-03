#!/usr/bin/env bash
# Boot an Android virtual device if needed, then run the emulator firmware on
# it. Stop with Ctrl-C, or with tools/android/stop.sh, which also stops the
# virtual device.
set -euo pipefail

repo_dir=$(cd "$(dirname "$0")/../.." && pwd)
usage() {
    cat >&2 <<EOF
Usage: $0 [--apk] [--disable-animation] [--no-window] [--avd NAME]
          [--console-port N] [--port N]

  --apk             show the Trezor screen (default: headless firmware)
  --disable-animation
                    disable the APK's animations, as device tests need
  --no-window       do not show the Android virtual device's window
  --avd NAME        virtual device, created if missing (default: trezor-android)
  --console-port N  Android emulator console port (default: 5580)
  --port N          UDP base port for clients (default: 31344)

Build first with tools/android/build.sh x86_64 [model].
EOF
    exit 2
}

args=("$@")
runner_args=()
window=()
avd=trezor-android
console_port=5580
port=31344
while [ $# -gt 0 ]; do
    case "$1" in
        --apk | --disable-animation) runner_args+=("$1") ;;
        --no-window) window=(-no-window) ;;
        --avd) avd=${2:?}; shift ;;
        --console-port) console_port=${2:?}; shift ;;
        --port) port=${2:?}; shift ;;
        *) usage ;;
    esac
    shift
done

if ! command -v emulator >/dev/null; then
    exec nix-shell "$repo_dir/tools/android/shell.nix" --arg withEmulator true \
        --run "$(printf '%q ' "$0" "${args[@]}")"
fi

serial="emulator-$console_port"
if ! adb devices | grep -q "^$serial\b"; then
    if ! emulator -list-avds | grep -qx "$avd"; then
        echo "Creating $avd"
        echo no | avdmanager create avd --name "$avd" --device pixel \
            --package 'system-images;android-28;default;x86_64'
    fi
    log="$repo_dir/core/build/android/$avd.log"
    mkdir -p "$(dirname "$log")"
    echo "Booting $avd as $serial, log in $log"
    setsid nohup emulator -avd "$avd" -port "$console_port" "${window[@]}" \
        -no-audio -no-metrics -no-boot-anim -no-snapshot -gpu swiftshader \
        -memory 1024 -cores 2 >"$log" 2>&1 </dev/null &
    timeout 300 adb -s "$serial" wait-for-device
    until [ "$(adb -s "$serial" shell getprop sys.boot_completed | tr -d '\r')" = 1 ]; do
        sleep 2
    done
fi

cd "$repo_dir"
exec uv run python tools/android/run.py --serial "$serial" --port "$port" \
    "${runner_args[@]}"
