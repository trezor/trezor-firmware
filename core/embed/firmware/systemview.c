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

#ifdef SYSTEM_VIEW

#include "systemview.h"
#include <string.h>
#include "mpconfigport.h"

#include "SEGGER_SYSVIEW.h"
#include "SEGGER_SYSVIEW_Conf.h"

void enable_systemview() {
  SEGGER_SYSVIEW_Conf();
  SEGGER_SYSVIEW_Start();
}

#ifdef SYSTEMVIEW_DEST_RTT
size_t _write(int file, const void *ptr, size_t len);
#endif

size_t segger_print(const char *str, size_t len) {
#ifdef SYSTEMVIEW_DEST_SYSTEMVIEW
  static char str_copy[1024];
  size_t copylen = len > 1023 ? 1023 : len;
  memcpy(str_copy, str, copylen);
  str_copy[copylen] = 0;
  SEGGER_SYSVIEW_Print(str_copy);
  return len;
#endif
#ifdef SYSTEMVIEW_DEST_RTT
  _write(0, str, len);
  return len;
#endif
}
#endif
