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

typedef enum {
  LOG_LEVEL_OFF = 0,
  LOG_LEVEL_ERR = 1,
  LOG_LEVEL_WARN = 2,
  LOG_LEVEL_INF = 3,
  LOG_LEVEL_DBG = 4,
} log_level_t;

/** Information about a source module */
typedef struct {
  /** Source module name shown in the logs */
  const char* name;
  /** Length of the module name in characters */
  size_t name_len;
} log_source_t;

#ifdef USE_DBG_CONSOLE

#include <sys/syslog.h>

#define LOG_DECLARE(source_name) SYSLOG_LOG_DECLARE(source_name)

#define LOG_MODULE_MAX_LEVEL (SYSLOG_MODULE_MAX_LEVEL)

#define LOG_ERR(fmt, ...) SYSLOG_LOG_ERR(fmt, ##__VA_ARGS__)
#define LOG_WARN(fmt, ...) SYSLOG_LOG_WARN(fmt, ##__VA_ARGS__)
#define LOG_INF(fmt, ...) SYSLOG_LOG_INF(fmt, ##__VA_ARGS__)
#define LOG_DBG(fmt, ...) SYSLOG_LOG_DBG(fmt, ##__VA_ARGS__)

#define LOG_HEXDUMP_DBG(prefix, data, data_size) \
  SYSLOG_LOG_HEXDUMP_DBG(prefix, data, data_size)

#else

#define LOG_DECLARE(source_name)

#define LOG_MODULE_MAX_LEVEL (LOG_LEVEL_OFF)

#define LOG_ERR(fmt, ...)
#define LOG_WARN(fmt, ...)
#define LOG_INF(fmt, ...)
#define LOG_DBG(fmt, ...)

#define LOG_HEXDUMP_DBG(prefix, data, data_size)

#endif  // USE_DBG_CONSOLE
