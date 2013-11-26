#!/bin/bash

cd `dirname $0`/../../trezor-common/protob

protoc --python_out=../../trezor-emu/trezor/ -I/usr/include -I. types.proto
protoc --python_out=../../trezor-emu/trezor/ -I/usr/include -I. messages.proto
