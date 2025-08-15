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
#include <sys/sysevent.h>

#ifdef USE_VCP_FOR_DEBUGGING
#define SYSHANDLE_CONSOLE SYSHANDLE_USB_VCP
#else
#define SYSHANDLE_CONSOLE SYSHANDLE_DBG_CONSOLE
#endif

ssize_t dbg_read(void *buffer, size_t buffer_size) {
  return syshandle_read(SYSHANDLE_CONSOLE, buffer, buffer_size);
}

ssize_t dbg_write(const void *data, size_t data_size) {
#ifdef BLOCK_ON_VCP
  return syshandle_write_blocking(SYSHANDLE_CONSOLE, data, data_size, 1000);
#else
  return syshandle_write(SYSHANDLE_CONSOLE, data, data_size);
#endif
}

void dbg_vprintf(const char *fmt, va_list args) {
  char temp[80];
  mini_vsnprintf(temp, sizeof(temp), fmt, args);
  dbg_write(temp, strnlen(temp, sizeof(temp)));
}

void dbg_printf(const char *fmt, ...) {
  va_list args;
  va_start(args, fmt);
  dbg_vprintf(fmt, args);
  va_end(args);
}
