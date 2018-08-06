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
cd ..

export EC_BACKEND_FORCE=1
export EC_BACKEND=1
python3 -m unittest trezor_monero_test.test_trezor
error=$?
kill $upy_pid
exit $error
