#!/bin/bash

# run emulator
cd ../src
../build/unix/micropython -O0 main.py >/dev/null &
upy_pid=$!
sleep 1

# run tests
cd ../tests
TREZOR_TRANSPORT_V1=0 ./run_tests_device.sh
error=$?

kill $upy_pid
exit $error
