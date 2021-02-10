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

#include "common.h"
#include "trng.h"

void trng_random_buffer(uint8_t *buf, size_t len) {
  static FILE *frand = NULL;
  if (!frand) {
    frand = fopen("/dev/urandom", "r");
  }
  ensure(sectrue * (frand != NULL), "fopen failed");
  ensure(sectrue * (len == fread(buf, 1, len, frand)), "fread failed");
}

uint32_t trng_random32(void) {
  uint32_t value;
  trng_random_buffer((uint8_t *)&value, sizeof(value));
  return value;
}
