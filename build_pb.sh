#!/bin/bash
CURDIR=$(pwd)

cd $CURDIR/../trezor-common/protob

for i in messages types ; do
    protoc --python_out=$CURDIR/trezorlib/ -I/usr/include -I. $i.proto
done
