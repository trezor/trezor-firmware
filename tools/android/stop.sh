#!/usr/bin/env bash
# Stop the runners for an adb device, then the Android virtual device itself.
set -euo pipefail

serial=${1:-emulator-5580}

if ! command -v adb >/dev/null; then
    repo_dir=$(cd "$(dirname "$0")/../.." && pwd)
    exec nix-shell "$repo_dir/tools/android/shell.nix" \
        --run "$(printf '%q ' "$0" "$serial")"
fi

# Interrupt only the Python processes, not their `uv run` or shell wrappers,
# so that each runner's cleanup is not interrupted by a second signal.
runners() {
    local pid
    for pid in $(pgrep -f "[t]ools/android/run[.]py --serial $serial( |$)"); do
        if [[ $(cat "/proc/$pid/comm" 2>/dev/null) == python* ]]; then
            echo "$pid"
        fi
    done
}

mapfile -t pids < <(runners)
if [ ${#pids[@]} -gt 0 ]; then
    echo "Stopping runner ${pids[*]}"
    # The runner stops its device processes and removes its forwarding rules.
    kill -INT "${pids[@]}"
    for _ in $(seq 30); do
        [ -z "$(runners)" ] && break
        sleep 1
    done
    if [ -n "$(runners)" ]; then
        echo "Runner did not stop: $(runners)" >&2
        exit 1
    fi
fi

if [[ $serial == emulator-* ]] && adb devices | grep -q "^$serial\b"; then
    echo "Stopping $serial"
    adb -s "$serial" emu kill
    timeout 60 adb -s "$serial" wait-for-disconnect
fi
