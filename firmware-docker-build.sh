#!/bin/bash
IMAGETAG=trezor-mcu-build

docker rmi $IMAGETAG || :
docker build -t $IMAGETAG .
docker run -t -v $(pwd):/output $IMAGETAG /bin/cp /trezor-mcu/firmware/trezor.bin /output

echo "---------------------"
echo "Firmware fingerprint:"

sha256sum trezor.bin
