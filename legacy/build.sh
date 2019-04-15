#!/bin/bash
set -e

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

docker build -t "$IMAGE" --build-arg EMULATOR=$EMULATOR .
docker run -it -v $(pwd):/src:z --user="$(stat -c "%u:%g" .)" "$IMAGE" \
  /src/script/fullbuild "$BOOTLOADER_COMMIT" "$FIRMWARE_COMMIT"
