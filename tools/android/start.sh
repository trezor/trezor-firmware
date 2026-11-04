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
          [--card] [--card-port N] [--card-delay MS] [--card-hold MS]

  --apk             show the Trezor screen (default: headless firmware)
  --disable-animation
                    disable the APK's animations, as device tests need
  --no-window       do not show the Android virtual device's window
  --avd NAME        virtual device, created if missing (default: trezor-android)
  --console-port N  Android emulator console port (default: 5580)
  --port N          UDP base port for clients (default: 31344)
  --card            run the card model on the host for a firmware built with
                    build.sh --card; it stops with the runner
  --card-port N     card model TCP port on the host (default: 28993)
  --card-delay MS   the simulated user presents the card MS after the
                    firmware asks for it (default: 0)
  --card-hold MS    the card leaves after MS without a command, so the next
                    operation needs a new tap (default: never)

Build first with tools/android/build.sh x86_64 [model] [--card].
EOF
    exit 2
}

args=("$@")
runner_args=()
window=()
avd=trezor-android
console_port=5580
port=31344
card=0
card_port=28993
card_args=()
while [ $# -gt 0 ]; do
    case "$1" in
        --apk | --disable-animation) runner_args+=("$1") ;;
        --no-window) window=(-no-window) ;;
        --avd) avd=${2:?}; shift ;;
        --console-port) console_port=${2:?}; shift ;;
        --port) port=${2:?}; shift ;;
        --card) card=1 ;;
        --card-port) card_port=${2:?}; shift ;;
        --card-delay) card_args+=(-t "${2:?}"); shift ;;
        --card-hold) card_args+=(-k "${2:?}"); shift ;;
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
if [ "$card" = 0 ]; then
    exec uv run python tools/android/run.py --serial "$serial" --port "$port" \
        "${runner_args[@]}"
fi

# The card model holds the seed on the host; the runner lets the firmware reach
# it through adb reverse. Ctrl-C and stop.sh end the runner, then the model.
make -s -C tests/card_model build/card_model_server
card_log="$repo_dir/core/build/android/card-model-$card_port.log"
tests/card_model/build/card_model_server -p "$card_port" "${card_args[@]}" -v \
    >"$card_log" 2>&1 &
card_pid=$!
trap 'kill "$card_pid" 2>/dev/null || true' EXIT
for _ in $(seq 50); do
    grep -q ready "$card_log" && break
    kill -0 "$card_pid" 2>/dev/null || { cat "$card_log" >&2; exit 1; }
    sleep 0.1
done
echo "Card model on 127.0.0.1:$card_port, log in $card_log"
uv run python tools/android/run.py --serial "$serial" --port "$port" \
    --card-port "$card_port" "${runner_args[@]}"
