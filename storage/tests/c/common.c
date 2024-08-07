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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "common.h"

static uint32_t ticks_ms = 0;

void __shutdown(void) {
  printf("SHUTDOWN\n");
  exit(3);
}

void __fatal_error(const char *msg, const char *file, int line) {
  printf("\nFATAL ERROR:\n");
  if (msg) {
    printf("msg : %s\n", msg);
  }
  if (file) {
    printf("file: %s:%d\n", file, line);
  }
  __shutdown();
}

void show_wipe_code_screen(void) {}
void show_pin_too_many_screen(void) {}

void hal_delay(uint32_t delay_ms) { ticks_ms += delay_ms; }
uint32_t hal_ticks_ms(void) { return ticks_ms; }
