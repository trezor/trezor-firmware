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

#ifdef KERNEL_MODE

/**
 * @brief Initialize the debugging console.
 *
 * Called when system starts up, during `system_init()`.
 */
void dbg_console_init(void);

#endif

/**
 * @brief Read data from the debugging console.
 *
 * Not all platforms support reading from the debugging console.
 *
 * @param buffer Pointer to the buffer where data will be stored.
 * @param buffer_size Size of the buffer in bytes.
 *
 * @return Number of bytes read, or a negative error code on failure.
 */
ssize_t dbg_console_read(void* buffer, size_t buffer_size);

/**
 * @brief Write data to the debugging console.
 *
 * The function may be blocking, depending on the backend implementation
 * and its configuration. If called from interrupt context, the function
 * is always non-blocking.
 *
 * @param data Pointer to the data to write.
 * @param data_size Size of the data in bytes.
 * @return Number of bytes written, or a negative error code on failure.
 */
ssize_t dbg_console_write(const void* data, size_t data_size);

/**
 * @brief vprintf-like function for debugging.
 *
 * @param fmt Format string.
 * @param args Variable argument list.
 */
void dbg_console_vprintf(const char* fmt, va_list args);

/**
 * @brief printf-like function for debugging.
 *
 * If possible, consider using `LOG_xxx()` macro instead of this function.
 * These macros provide standardized message formatting and filtering.
 *
 * @param fmt Format string.
 * @param ... Variable arguments.
 */
void dbg_console_printf(const char* fmt, ...);

/**
 * @brief Short alias for `dbg_console_printf()`.
 */
#define dbg_printf dbg_console_printf
