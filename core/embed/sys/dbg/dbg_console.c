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

#include <trezor_rtl.h>

#include <rtl/mini_printf.h>
#include <sys/dbg_console.h>

void dbg_console_vprintf(const char *fmt, va_list args) {
  char temp[80];
  mini_vsnprintf(temp, sizeof(temp), fmt, args);
  dbg_console_write(temp, strnlen(temp, sizeof(temp)));
}

void dbg_console_printf(const char *fmt, ...) {
  va_list args;
  va_start(args, fmt);
  dbg_console_vprintf(fmt, args);
  va_end(args);
}
