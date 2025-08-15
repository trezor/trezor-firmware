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

#include "py/mphal.h"

#include <io/usb_config.h>
#include <sys/systick.h>

int mp_hal_stdin_rx_chr(void) {
  uint8_t c = 0;
  int r = syshandle_read(SYSHANDLE_USB_VCP, &c, sizeof(c));
  (void)r;
  return c;
}

void mp_hal_stdout_tx_strn(const char *str, size_t len) {
  // The write timeout defaults to 0, because otherwise when the VCP receive
  // buffer on the host gets full, the timeout will block device operation.
  int r = syshandle_write_blocking(SYSHANDLE_USB_VCP, (const uint8_t *)str, len,
                                   BLOCK_ON_VCP ? 1000 : 0);
  (void)r;
}

// Dummy implementation required by ports/stm32/gccollect.c.
// The normal version requires MICROPY_ENABLE_SCHEDULER which we don't use.
void soft_timer_gc_mark_all(void) {}

void mp_hal_delay_ms(mp_uint_t Delay) { systick_delay_ms(Delay); }

void mp_hal_delay_us(mp_uint_t usec) { systick_delay_us(usec); }

mp_uint_t mp_hal_ticks_ms(void) { return systick_ms(); }

mp_uint_t mp_hal_ticks_us(void) { return systick_us(); }
