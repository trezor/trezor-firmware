#!/bin/bash
CURDIR=$(pwd)
mkdir -p $CURDIR/pb2/
echo > $CURDIR/pb2/__init__.py

INDEX=../src/trezor/messages/wire_types.py
rm -f $INDEX

for i in types messages storage ; do
    # Compile .proto files to python2 modules using google protobuf library
    cd $CURDIR/../../trezor-common/protob
    protoc --python_out=$CURDIR/pb2/ -I/usr/include -I. $i.proto
done

for i in types messages storage ; do
    # Convert google protobuf library to trezor's internal format
    cd $CURDIR
    ./pb2py $i ../src/trezor/messages/ $INDEX
done

rm -rf $CURDIR/pb2/
