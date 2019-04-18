#!/bin/bash
set -e

cd "$(dirname $0)/.."

BOOTLOADER_COMMIT=${1:-HEAD}
FIRMWARE_COMMIT=${2:-HEAD}

if [ "$BOOTLOADER_COMMIT" = "EMU" ]; then
    export EMULATOR=1
fi

if [ "$EMULATOR" = 1 ]; then
    IMAGE=trezor-mcu-emulator
else
    IMAGE=trezor-mcu-build
fi

USER=$(ls -lnd . | awk '{ print $3 }')
GROUP=$(ls -lnd . | awk '{ print $4 }')

docker build -t "$IMAGE" --build-arg EMULATOR=$EMULATOR legacy
docker run -it -v $(pwd):/src:z --user="$USER:$GROUP" "$IMAGE" \
    /src/legacy/script/fullbuild "$BOOTLOADER_COMMIT" "$FIRMWARE_COMMIT"
