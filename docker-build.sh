#!/bin/bash

dirname $0

# Build trezor firmware
docker build . | tee docker.log

# Parse image name
IMAGE=`grep "Successfully built" docker.log | tail -n1 | cut -d' ' -f3`
echo "IMAGE NAME: $IMAGE"

docker run -t $IMAGE true

# Parse container name
CONTAINER=`docker ps -a | grep true | head -n1 | cut -d' ' -f1`
echo "CONTAINER NAME: $CONTAINER"

docker cp $CONTAINER:/trezor-mcu/firmware/trezor.bin .

echo "-------------------------"
echo ""
echo "SHA256 hash:"

sha256sum trezor.bin
