#!/bin/bash

APP=funnycoin_rust
TARGET=thumbv7em-none-eabihf

DEBUG_DIR=target/$TARGET/debug
RELEASE_DIR=target/$TARGET/release

cargo build -Z build-std=core,alloc --target $TARGET
cargo build -Z build-std=core,alloc --target $TARGET --release

readelf --all $DEBUG_DIR/$APP > $DEBUG_DIR/$APP.readelf.txt
readelf --all $RELEASE_DIR/$APP > $RELEASE_DIR/$APP.readelf.txt

arm-none-eabi-objcopy --strip-debug --remove-section .rel.text --discard-locals $RELEASE_DIR/$APP $RELEASE_DIR/$APP.min
arm-none-eabi-objcopy --strip-unneeded $RELEASE_DIR/$APP.min $RELEASE_DIR/$APP.min

readelf --all $RELEASE_DIR/$APP.min > $RELEASE_DIR/$APP.min.readelf.txt
arm-none-eabi-objdump -d $RELEASE_DIR/$APP $RELEASE_DIR/$APP.min > $RELEASE_DIR/$APP.min.objdump.txt

arm-none-eabi-objcopy --strip-debug --remove-section .rel.text --discard-locals $DEBUG_DIR/$APP $DEBUG_DIR/$APP.min
arm-none-eabi-objcopy --strip-unneeded $DEBUG_DIR/$APP.min $DEBUG_DIR/$APP.min

readelf --all $DEBUG_DIR/$APP.min > $DEBUG_DIR/$APP.min.readelf.txt
arm-none-eabi-objdump -d $DEBUG_DIR/$APP $DEBUG_DIR/$APP.min > $DEBUG_DIR/$APP.min.objdump.txt