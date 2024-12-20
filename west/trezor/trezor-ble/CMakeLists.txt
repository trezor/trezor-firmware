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
    src/connection.c
    src/advertising.c
    src/events.c
    src/uart.c
    src/spi.c
    src/int_comm.c
    src/trz_nus.c
)


# NORDIC SDK APP END

zephyr_library_include_directories(.)
