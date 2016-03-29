#!/bin/bash
set -e

BUILD_DIR=vendor/micropython/stmhal/build-TREZORV2

st-flash write $BUILD_DIR/firmware0.bin 0x8000000
sleep 0.1
st-flash write $BUILD_DIR/firmware1.bin 0x8020000
