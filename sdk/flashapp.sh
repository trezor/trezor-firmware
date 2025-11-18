#!/usr/bin/env bash
set -euo pipefail

# Configuration files
INTERFACE_CFG="interface/stlink.cfg"
TARGET_CFG="target/stm32u5x.cfg"

# OpenOCD commands
TRANSPORT_CMD="transport select hla_swd"
INIT_CMD="init; reset halt"
FLASH_FILE=$1
FLASH_ADDR="0x08320000"
FLASH_MODE="bin"
FLASH_CMD="flash write_image erase ${FLASH_FILE} ${FLASH_ADDR} ${FLASH_MODE}"
EXIT_CMD="exit"

# Run OpenOCD
openocd \
  -f "${INTERFACE_CFG}" \
  -c "${TRANSPORT_CMD}" \
  -f "${TARGET_CFG}" \
  -c "${INIT_CMD}; ${FLASH_CMD}; ${EXIT_CMD}"
