#
# Copyright (c) 2020 Nordic Semiconductor
#
# SPDX-License-Identifier: LicenseRef-Nordic-5-Clause
#

cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(NONE)

# Application sources
FILE(GLOB app_sources src/*.c)

# NORDIC SDK APP START
target_sources(app PRIVATE
	${app_sources}
)
# NORDIC SDK APP END
