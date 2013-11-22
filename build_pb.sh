#!/bin/bash
cd ./trezor-common/protob
protoc --python_out=../../trezorlib/ -I/usr/include -I. -I. trezor.proto
