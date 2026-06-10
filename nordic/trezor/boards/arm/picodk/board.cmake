# Copyright (c) 2025 Nordic Semiconductor ASA
# SPDX-License-Identifier: LicenseRef-Nordic-5-Clause

if(CONFIG_SOC_NRF54LS05B_CPUAPP)
  board_runner_args(jlink "--device=cortex-m33" "--speed=4000")
endif()

include(${ZEPHYR_BASE}/boards/common/nrfutil.board.cmake)
include(${ZEPHYR_BASE}/boards/common/jlink.board.cmake)
