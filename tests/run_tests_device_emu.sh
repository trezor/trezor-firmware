#!/bin/bash

# run emulator
cd ../src
../build/unix/micropython -O0 main.py >/dev/null &
upy_pid=$!
sleep 1

# run tests
cd ../tests
error=0
if ! TREZOR_TRANSPORT_V1=0 ./run_tests_device.sh; then
    error=1
fi
if ! TREZOR_TRANSPORT_V1=1 ./run_tests_device.sh; then
    error=1
fi
kill $upy_pid
exit $error
