/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#pragma once

#include <sys/logging.h>
#include <sys/sysevent.h>
#include "trezor_api_v1.h"

const uint32_t LOG_LEVEL_ERROR = LOG_LEVEL_ERR;
const uint32_t LOG_LEVEL_WRN = LOG_LEVEL_WARN;
const uint32_t LOG_LEVEL_INFO = LOG_LEVEL_INF;
const uint32_t LOG_LEVEL_DEBUG = LOG_LEVEL_DBG;

#ifdef USE_IPC
const uint32_t SYS_HANDLE_IPC0 = SYSHANDLE_IPC0;
#endif

// Each application is expected to implement applet_main() function, which is
// the entry point of the application. The function is called by the system when
// the application is started.
//
// void applet_main(trezor_api_getter_t api_getter);

/**
 * @brief Type of the function that retrieves the Trezor API for a given
 * version.
 *
 * @param version The version of the Trezor API to retrieve.
 * @return A pointer to the Trezor API structure corresponding to the requested
 * version.
 */
typedef void* (*trezor_api_getter_t)(uint32_t version);
