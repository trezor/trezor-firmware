#!/bin/bash
set -e

cd "$(dirname $0)/.."

BOOTLOADER_COMMIT=${1:-HEAD}
FIRMWARE_COMMIT=${2:-HEAD}
IMAGE=trezor-mcu-build

USER=$(ls -lnd . | awk '{ print $3 }')
GROUP=$(ls -lnd . | awk '{ print $4 }')

docker build -t "$IMAGE" ci/
docker run -it -v $(pwd):/src:z --user="$USER:$GROUP" "$IMAGE" \
    /src/legacy/script/fullbuild "$BOOTLOADER_COMMIT" "$FIRMWARE_COMMIT"
