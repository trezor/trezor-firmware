#!/bin/bash
set -e

cd "$(dirname $0)/.."

BOOTLOADER_COMMIT=${1:-HEAD}
FIRMWARE_COMMIT=${2:-HEAD}
IMAGE=trezor-mcu-build
BITCOIN_ONLY=${BITCOIN_ONLY:-0}

USER=$(ls -lnd . | awk '{ print $3 }')
GROUP=$(ls -lnd . | awk '{ print $4 }')

docker build -t "$IMAGE" ci/
docker run -it -v $(pwd):/src:z --env BITCOIN_ONLY="$BITCOIN_ONLY" --user="$USER:$GROUP" "$IMAGE" \
    /src/legacy/script/fullbuild "$BOOTLOADER_COMMIT" "$FIRMWARE_COMMIT"
