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

#ifdef KERNEL_MODE

#include <rtl/mini_printf.h>
#include <stdarg.h>
#include <sys/irq.h>

void dbg_vprintf(const char* fmt, va_list args) {
  char temp[80];
  mini_vsnprintf(temp, sizeof(temp), fmt, args);

  irq_key_t irq_key = irq_lock();
  for (size_t i = 0; i < sizeof(temp); i++) {
    if (temp[i] == '\0') {
      break;
    }
    ITM_SendChar(temp[i]);
  }
  irq_unlock(irq_key);
}

void dbg_printf(const char* fmt, ...) {
  va_list args;
  va_start(args, fmt);
  dbg_vprintf(fmt, args);
  va_end(args);
}

#endif  // KERNEL_MODE
