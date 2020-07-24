#!/bin/sh
PYOPT="${PYOPT:-1}"

if [ -n "$1" ]; then
    echo "This is just a compatibility wrapper. Use emu.py if you want features."
    exit 1
fi

TREZOR_MODEL="${TREZOR_MODEL:-T}"
if [ "$TREZOR_MODEL" = "T" ]; then
    cd src
else
    cd "src${TREZOR_MODEL}"
fi

../build/unix/micropython -O$PYOPT -X heapsize=20M
