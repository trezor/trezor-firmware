#!/bin/bash
BUILD_DIR=vendor/micropython/stmhal/build-TREZORV2

gdb $BUILD_DIR/firmware.elf -ex 'target remote localhost:3333'
