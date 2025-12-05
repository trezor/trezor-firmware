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

// Disable float support to save space
#define PRINTF_DISABLE_SUPPORT_FLOAT

#if defined(BOARDLOADER) && defined(TREZOR_MODEL_T3T1)
// Disable long long support in the bootloader to save space
#define PRINTF_DISABLE_SUPPORT_LONG_LONG
#endif

/**
 * Tiny snprintf/vsnprintf implementation
 *
 * @param buffer A pointer to the buffer where to store the formatted string
 * @param count The maximum number of characters to store in the buffer,
 * including a terminating null character
 * @param format A string that specifies the format of the output
 * @param va A value identifying a variable arguments list
 * @return The number of characters that COULD have been written into the
 * buffer, not counting the terminating null character. A value equal or larger
 * than count indicates truncation. Only when the returned value is non-negative
 * and less than count, the string has been completely written.
 */
int snprintf_(char* buffer, size_t count, const char* format, ...)
    __attribute__((__format__(__printf__, 3, 4)));

int vsnprintf_(char* buffer, size_t count, const char* format, va_list va)
    __attribute__((__format__(__printf__, 3, 0)));

#define mini_vsnprintf vsnprintf_
#define mini_snprintf snprintf_
