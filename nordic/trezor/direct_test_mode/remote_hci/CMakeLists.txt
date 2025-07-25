#
# Copyright (c) 2023 Nordic Semiconductor ASA
#
# SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
#

cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(remote_hci)

target_include_directories(app PRIVATE ./../rpc)
target_include_directories(app PRIVATE ./../src/transport)

# NORDIC SDK APP START
target_sources(app PRIVATE
  src/main.c
  ../src/transport/hci_uart.c
)
# NORDIC SDK APP END
