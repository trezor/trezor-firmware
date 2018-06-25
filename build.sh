#!/bin/bash
set -e

IMAGE=trezor-mcu-build

BOOTLOADER_COMMIT=${1:-HEAD}
FIRMWARE_COMMIT=${2:-HEAD}

docker build -t "$IMAGE" .
docker run -it -v $(pwd):/src:z --user="$(stat -c "%u:%g" .)" "$IMAGE" \
  /src/script/fullbuild "$BOOTLOADER_COMMIT" "$FIRMWARE_COMMIT"
