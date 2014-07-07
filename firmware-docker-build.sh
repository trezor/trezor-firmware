#!/bin/bash

dirname $0

IMAGETAG=trezor-mcu-build
docker rmi $IMAGETAG || :
docker build -t $IMAGETAG .

CONTAINERTAG=trezor-mcu-build
docker rm $CONTAINERTAG || :
docker run --name $CONTAINERTAG $IMAGETAG true

docker cp $CONTAINERTAG:/trezor-mcu/firmware/trezor.bin .

echo "---------------------"
echo "Firmware fingerprint:"

sha256sum trezor.bin
