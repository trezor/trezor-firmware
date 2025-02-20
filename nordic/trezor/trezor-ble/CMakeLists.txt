#
# Copyright (c) 2018 Nordic Semiconductor
#
# SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
#
cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(NONE)

# NORDIC SDK APP START
target_sources(app PRIVATE
        src/main.c
        src/ble/connection.c
        src/ble/advertising.c
        src/ble/ble_management.c
        src/ble/service.c
        src/ble/bonds.c
        src/ble/pairing.c
        src/ble/ble.c
        src/management/management.c
        src/prodtest/prodtest.c
        src/trz_comm/uart.c
        src/trz_comm/spi.c
        src/trz_comm/trz_comm.c
        src/signals/signals.c
)

include_directories(src/signals/inc)
include_directories(src/trz_comm/inc)
include_directories(src/ble/inc)
include_directories(src/management/inc)
include_directories(src/prodtest/inc)

# NORDIC SDK APP END

zephyr_library_include_directories(.)
