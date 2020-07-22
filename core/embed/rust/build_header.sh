#!/bin/sh

cbindgen \
    --config cbindgen.toml \
    --crate trezor_lib \
    --output librust.h