#!/bin/bash

cd `dirname $0`

protoc --python_out=../trezorlib/ -I/usr/include -I. trezor.proto
