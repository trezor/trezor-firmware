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

#include <sys/systick.h>

#ifdef USE_DBG_CONSOLE
#include <sys/dbg_console.h>
#endif

int mp_hal_stdin_rx_chr(void) {
#ifdef USE_DBG_CONSOLE
  uint8_t c = 0;
  dbg_console_read(&c, sizeof(c));
  return c;
#else
  return 0;
#endif
}

// The last bytes MicroPython printed, kept so that an uncaught exception's
// traceback can be shown on the error screen when the main script exits
// (see main.c); the debug console may be absent or too slow to attach.
#define STDOUT_TAIL_SIZE 768
static char g_stdout_tail[STDOUT_TAIL_SIZE];
static size_t g_stdout_tail_head = 0;
static size_t g_stdout_tail_len = 0;

mp_uint_t mp_hal_stdout_tx_strn(const char *str, size_t len) {
  for (size_t i = 0; i < len; i++) {
    g_stdout_tail[g_stdout_tail_head] = str[i];
    g_stdout_tail_head = (g_stdout_tail_head + 1) % STDOUT_TAIL_SIZE;
    if (g_stdout_tail_len < STDOUT_TAIL_SIZE) {
      g_stdout_tail_len++;
    }
  }
#ifdef USE_DBG_CONSOLE
  ssize_t written = dbg_console_write(str, len);
  return (written > 0 ? written : 0);
#else
  return (mp_uint_t)len;
#endif
}

// Copies the kept stdout tail into `buf` as a NUL-terminated string.
void mp_hal_stdout_tail(char *buf, size_t buf_size) {
  size_t n = g_stdout_tail_len;
  if (n > buf_size - 1) {
    n = buf_size - 1;
  }
  size_t start = (g_stdout_tail_head + STDOUT_TAIL_SIZE - n) % STDOUT_TAIL_SIZE;
  for (size_t i = 0; i < n; i++) {
    buf[i] = g_stdout_tail[(start + i) % STDOUT_TAIL_SIZE];
  }
  buf[n] = '\0';
}

// Dummy implementation required by ports/stm32/gccollect.c.
// The normal version requires MICROPY_ENABLE_SCHEDULER which we don't use.
void soft_timer_gc_mark_all(void) {}

void mp_hal_delay_ms(mp_uint_t Delay) { systick_delay_ms(Delay); }

void mp_hal_delay_us(mp_uint_t usec) { systick_delay_us(usec); }

mp_uint_t mp_hal_ticks_ms(void) { return systick_ms(); }

mp_uint_t mp_hal_ticks_us(void) { return systick_us(); }

mp_uint_t mp_hal_ticks_cpu(void) { return systick_us(); }
