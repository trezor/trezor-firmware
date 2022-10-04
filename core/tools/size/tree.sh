#!/bin/sh

CURR_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
CORE_DIR=$(realpath "${CURR_DIR}/../..")

FIRMWARE_ELF="${CORE_DIR}/build/firmware/firmware.elf"
MAP_FILE="${CORE_DIR}/build/firmware/firmware.map"

export BINSIZE_ROOT_DIR="${CORE_DIR}"
binsize tree "${FIRMWARE_ELF}" -m "${MAP_FILE}" -s ".flash" -s ".flash2"  $@
