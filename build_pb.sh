#!/bin/bash
CURDIR=$(pwd)

cd $CURDIR/../trezor-common/protob

for i in messages types ; do
    protoc --python_out=$CURDIR/trezorlib/ -I/usr/include -I. $i.proto
done

# hack to make output python 3 compatible
sed -i 's/^import types_pb2/from . import types_pb2/g' $CURDIR/trezorlib/messages_pb2.py
