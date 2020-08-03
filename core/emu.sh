#!/bin/sh
PYOPT="${PYOPT:-1}"

if [ -n "$1" ]; then
    echo "This is just a compatibility wrapper. Use emu.py if you want features."
    exit 1
fi

cd src
../build/unix/trezor-emu-core -O$PYOPT -X heapsize=20M
