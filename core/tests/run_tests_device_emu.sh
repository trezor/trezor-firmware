#!/bin/bash

SDIR="$(SHELL_SESSION_FILE='' && cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
CORE_DIR="$SDIR/.."
MICROPYTHON="${MICROPYTHON:-$CORE_DIR/build/unix/micropython}"
RUN_TEST_EMU=1
DISABLE_FADE=1
PYOPT=0

# run emulator if RUN_TEST_EMU
if [[ $RUN_TEST_EMU > 0 ]]; then
  cd "$CORE_DIR/src"
  TREZOR_TEST=1 \
  TREZOR_DISABLE_FADE=$DISABLE_FADE \
    $MICROPYTHON -O$PYOPT main.py >/dev/null &
  upy_pid=$!
  sleep 1
  cd -
fi

export TREZOR_PATH=udp:127.0.0.1:21324

# run tests
error=0
if ! pytest ../../tests/device_tests "$@"; then
  error=1
fi
kill $upy_pid
exit $error
