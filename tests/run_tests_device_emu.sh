#!/bin/bash

MICROPYTHON=../build/unix/micropython
PYOPT=0

# run emulator
cd ../src
$MICROPYTHON -O$PYOPT main.py >/dev/null &
upy_pid=$!
sleep 1

export TREZOR_PATH=udp:127.0.0.1:21324

# run tests
cd ../tests
error=0
if ! pytest "$@"; then
    error=1
fi
kill $upy_pid
exit $error
