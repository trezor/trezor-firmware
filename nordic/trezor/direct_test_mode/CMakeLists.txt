#
# Copyright (c) 2020 Nordic Semiconductor
#
# SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
#
cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(NONE)

target_include_directories(app PRIVATE ./src)

target_sources_ifndef(CONFIG_DTM_TRANSPORT_HCI app PRIVATE
  src/transport/dtm_uart_twowire.c
  src/transport/dtm_uart_wait.c
)

target_sources_ifdef(CONFIG_DTM_TRANSPORT_HCI app PRIVATE src/transport/dtm_hci.c)

if(CONFIG_DTM_TRANSPORT_HCI AND "${BOARD}" STREQUAL "nrf5340dk")
  target_sources(app PRIVATE src/transport/hci_uart_remote.c)
  target_include_directories(app PRIVATE ./rpc)
else()
  target_sources_ifdef(CONFIG_DTM_TRANSPORT_HCI app PRIVATE src/transport/hci_uart.c)
endif()

# NORDIC SDK APP START
target_sources(app PRIVATE
  src/dtm.c
  src/dtm_hw.c
  src/main.c
)
# NORDIC SDK APP END
