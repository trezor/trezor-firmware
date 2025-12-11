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

#include <trezor_types.h>

#include <stdarg.h>

#include "syslog_config.h"

/**
 * Starts a new log record and verifies whether it should be logged
 *
 * If the record should be logged, it prepares internal context for
 * subsequent `syslog_write_chunk()` calls.
 *
 * The function is safe to call from interrupt context.
 *
 * @param source Source module information
 * @param level Log level of the message
 * @return true if the record should be logged, false otherwise
 *
 */
bool syslog_start_record(const log_source_t* source, log_level_t level);

/**
 * Writes a message (or a part of it) to the log
 *
 * Should be called only after a successful `syslog_start_record()` call.
 * Multiple calls to `syslog_write_chunk()` may be used to write
 * a single log record in smaller parts. The `end_record` parameter
 * indicates whether this is the last chunk of the message
 *
 * The function is safe to call from interrupt context.
 *
 * @param text       Text chunk to write
 * @param text_len   Length of the text chunk
 * @param end_record true if this is the last chunk of the record
 * @return Number of bytes written, or negative value on error
 */

ssize_t syslog_write_chunk(const char* text, size_t text_len, bool end_record);

/**
 * Sets the logging filter string
 *
 * Filter string is processed left to right, each part modifies the logging
 * configuration. Each part starts with '+' (enable) or '-' (disable), followed
 * by optional log level digit (1-4), followed by optional module name pattern
 * (with '*' wildcard support at the end). Examples:
 *
 * `+*`            Enable all modules up to DBG level
 * `+1*`           Enable logging for all modules up to ERR level
 * `-*`            Disable all logging for all modules
 * `+4power*`      Enable DBG level for power modules (starting with 'power')
 * `-3*`           Disable DBG for all modules, keep WRN level and below
 * `+py.*          Enable all python modules (py.*) up to DBG level
 * `+3* -py.core*` Enable all modules up to INF level, except 'py.core*'
 *
 * Note: space before or after parts is ignored.
 *
 * Despite other functions in this file being safe to call from interrupt
 * context, `syslog_set_filter()` must not be called from interrupt context.
 *
 * @param filter Filter string
 * @param filter_len Length of the filter string
 * @return true if the filter was successfully set, false otherwise
 */
bool syslog_set_filter(const char* filter, size_t filter_len);

/**
 * Logs a messagge (printf-style with va_list)
 *
 * Message is logged if it passes the current logging filter (
 * see `syslog_set_filter()`).
 *
 * @param source Source module information
 * @param level Log level of the message
 * @param fmt   Format string (printf-style)
 * @param args  Variable arguments list
 */
void syslog_vprintf(const log_source_t* source, log_level_t level,
                    const char* fmt, va_list args)
    __attribute__((format(printf, 3, 0)));

/**
 * Logs a message (printf-style)
 *
 * Message is logged if it passes the current logging filter (
 * see `syslog_set_filter()`).
 *
 * @param source Source module information
 * @param level Log level of the message
 * @param fmt   Format string (printf-style)
 * @param ...   Variable arguments
 */
void syslog_printf(const log_source_t* source, log_level_t level,
                   const char* fmt, ...) __attribute__((format(printf, 3, 4)));

/**
 * Logs a hex dump of binary data and an optional prefix string
 *
 * Message is logged if it passes the current logging filter (
 * see `syslog_set_filter()`).
 *
 * @param source Source module information
 * @param level Log level of the message
 * @param prefix Optional prefix string to log before the hex data
 * @param data   Binary data to log
 * @param data_size Size of the binary data
 */

void syslog_print_hex(const log_source_t* source, log_level_t level,
                      const char* prefix, const uint8_t* data,
                      size_t data_size);

/**
 * Enables logging in the current compilation unit.
 *
 * All subsequent SYSLOG_LOG_*() calls will use this module information.
 *
 * It's expected that SYSLOG_<module_name>_LOG_LEVEL is defined
 * to one of LOG_LEVEL_* values.
 */
#define SYSLOG_LOG_DECLARE(module_name)                               \
  static const log_source_t g_syslog_source __attribute__((used)) = { \
      .name = #module_name,                                           \
      .name_len = sizeof(#module_name) - 1,                           \
  };                                                                  \
  static const log_level_t g_syslog_max_level __attribute__((used)) = \
      SYSLOG_##module_name##_MAX_LOG_LEVEL;

/**
 * Gets the maximum log level of the current module
 */
#define SYSLOG_MODULE_MAX_LEVEL g_syslog_max_level

/**
 * Logs an error message
 *
 * Message is logged if it passes the current logging filter (
 * see `syslog_set_filter()`).
 *
 * @param fmt   Format string (printf-style)
 * @param ...   Variable arguments
 */
#define SYSLOG_LOG_ERR(fmt, ...)                                          \
  do {                                                                    \
    if (g_syslog_max_level >= LOG_LEVEL_ERR) {                            \
      syslog_printf(&g_syslog_source, LOG_LEVEL_ERR, fmt, ##__VA_ARGS__); \
    }                                                                     \
  } while (0)

/**
 * Logs a warning message
 *
 * Message is logged if it passes the current logging filter (
 * see `syslog_set_filter()`).
 *
 * @param fmt   Format string (printf-style)
 * @param ...   Variable arguments
 */
#define SYSLOG_LOG_WARN(fmt, ...)                                          \
  do {                                                                     \
    if (g_syslog_max_level >= LOG_LEVEL_WARN) {                            \
      syslog_printf(&g_syslog_source, LOG_LEVEL_WARN, fmt, ##__VA_ARGS__); \
    }                                                                      \
  } while (0)

/**
 * Logs an informational message
 *
 * Message is logged if it passes the current logging filter (
 * see `syslog_set_filter()`).
 *
 * @param fmt   Format string (printf-style)
 * @param ...   Variable arguments
 */
#define SYSLOG_LOG_INF(fmt, ...)                                          \
  do {                                                                    \
    if (g_syslog_max_level >= LOG_LEVEL_INF) {                            \
      syslog_printf(&g_syslog_source, LOG_LEVEL_INF, fmt, ##__VA_ARGS__); \
    }                                                                     \
  } while (0)

/**
 * Logs a debug message
 *
 * Message is logged if it passes the current logging filter (
 * see `syslog_set_filter()`).
 *
 * @param fmt   Format string (printf-style)
 * @param ...   Variable arguments
 */
#define SYSLOG_LOG_DBG(fmt, ...)                                          \
  do {                                                                    \
    if (g_syslog_max_level >= LOG_LEVEL_DBG) {                            \
      syslog_printf(&g_syslog_source, LOG_LEVEL_DBG, fmt, ##__VA_ARGS__); \
    }                                                                     \
  } while (0)

/**
 * Logs a hex dump of binary data with an optional prefix string
 *
 * Message is logged if it passes the current logging filter (
 * see `syslog_set_filter()`).
 *
 * @param prefix Optional prefix string to log before the hex data
 * @param data   Binary data to log
 * @param data_size Size of the binary data
 */
#define SYSLOG_LOG_HEXDUMP_DBG(prefix, data, data_size)               \
  do {                                                                \
    if (g_syslog_max_level >= LOG_LEVEL_DBG) {                        \
      syslog_print_hex(&g_syslog_source, LOG_LEVEL_DBG, prefix, data, \
                       data_size);                                    \
    }                                                                 \
  } while (0)
