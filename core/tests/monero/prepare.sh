#!/usr/bin/env bash
# Makes sure the trezor_tests binary at TREZOR_MONERO_TESTS_PATH (default
# core/tests/trezor_monero_tests) was built from the current inputs, see
# inputs.sh. make test_emu_monero runs it before starting the emulator.
#
# When the binary is missing or outdated, TREZOR_MONERO_TESTS_GET says what to do:
#   download  download.sh: the binary built by CI (needs gh)
#   build     build.sh (needs docker, takes about 30 minutes)
#   keep      use the outdated binary as it is
# When it is not set, prepare.sh asks on a terminal and fails otherwise.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$(cd "$HERE/../.." && pwd)"
: "${TREZOR_MONERO_TESTS_PATH:=$CORE_DIR/tests/trezor_monero_tests}"
INPUTS="$("$HERE/inputs.sh")"

if [[ ! -f "$TREZOR_MONERO_TESTS_PATH" ]]; then
  state=missing
elif [[ "$(cat "$TREZOR_MONERO_TESTS_PATH.inputs" 2>/dev/null)" != "$INPUTS" ]]; then
  state=outdated
else
  exit 0
fi
echo "Monero tests binary $TREZOR_MONERO_TESTS_PATH is $state (current inputs: $INPUTS)."

action="${TREZOR_MONERO_TESTS_GET:-}"
if [[ -z "$action" ]]; then
  if [[ ! -t 0 ]]; then
    echo "Set TREZOR_MONERO_TESTS_GET to download, build or keep, see docs/tests/monero-tests.md." >&2
    exit 1
  fi
  keep_choice=""
  if [[ $state == outdated ]]; then keep_choice=", [k]eep it"; fi
  read -r -p "[d]ownload it from CI (needs gh), [b]uild it (needs docker, ~30 min)$keep_choice or [q]uit? " answer
  case "$answer" in
    d*) action=download ;;
    b*) action=build ;;
    k*) action=keep ;;
    *) exit 1 ;;
  esac
fi

case "$action" in
  download) "$HERE/download.sh" "$TREZOR_MONERO_TESTS_PATH" ;;
  build) "$HERE/build.sh" "$TREZOR_MONERO_TESTS_PATH" ;;
  keep)
    if [[ $state == missing ]]; then
      echo "There is no binary to keep." >&2
      exit 1
    fi
    echo "Using the outdated binary."
    ;;
  *)
    echo "Unknown TREZOR_MONERO_TESTS_GET=$action, expected download, build or keep." >&2
    exit 1
    ;;
esac
