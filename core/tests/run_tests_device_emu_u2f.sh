#!/usr/bin/env bash

: "${RUN_TEST_EMU:=1}"

CORE_DIR="$(SHELL_SESSION_FILE='' && cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
MICROPYTHON="${MICROPYTHON:-$CORE_DIR/build/unix/micropython}"
TREZOR_SRC="${CORE_DIR}/src"

DISABLE_FADE=1
PYOPT="${PYOPT:-0}"
upy_pid=""

# run emulator if RUN_TEST_EMU
if [[ $RUN_TEST_EMU > 0 ]]; then
  source ../trezor_cmd.sh

  # remove flash before run to prevent inconsistent states
  mv "${TREZOR_PROFILE_DIR}/trezor.flash" "${TREZOR_PROFILE_DIR}/trezor.flash.bkp" 2>/dev/null

  cd "${TREZOR_SRC}"
  echo "Starting emulator: $MICROPYTHON $ARGS ${MAIN}"

  TREZOR_TEST=1 \
  TREZOR_DISABLE_FADE=$DISABLE_FADE \
    $MICROPYTHON $ARGS "${MAIN}" &> "${TREZOR_LOGFILE}" &
  upy_pid=$!
  cd -
  sleep 1
fi

# run tests
error=0
# missuse loaddevice test to initialize the device
if ! pytest ../../tests/device_tests -k "test_msg_loaddevice" "$@"; then
  error=1
fi
if ! ../../tests/fido_tests/u2f-tests-hid/HIDTest 21328 "$@"; then
  error=1
fi
if ! ../../tests/fido_tests/u2f-tests-hid/U2FTest 21328 "$@"; then
  error=1
fi
kill $upy_pid
exit $error
