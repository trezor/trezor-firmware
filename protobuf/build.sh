#!/bin/bash

cd `dirname $0`

protoc --python_out=../trezorlib/ trezor.proto
