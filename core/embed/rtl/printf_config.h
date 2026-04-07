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

#define PRINTF_SUPPORT_DECIMAL_SPECIFIERS 0
#define PRINTF_SUPPORT_EXPONENTIAL_SPECIFIERS 0
#define PRINTF_SUPPORT_WRITEBACK_SPECIFIER 1
#define PRINTF_SUPPORT_MSVC_STYLE_INTEGER_SPECIFIERS 0
#define PRINTF_USE_DOUBLE_INTERNALLY 0
#define PRINTF_INTEGER_BUFFER_SIZE 32
#define PRINTF_DECIMAL_BUFFER_SIZE 0

static inline void putchar_(char c) {}
