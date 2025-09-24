/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <libopencm3/cm3/common.h>
#include <libopencm3/stm32/f2/rng.h>
#include <libopencm3/stm32/memorymap.h>

#include "rng.h"

#if !EMULATOR
static uint32_t rng_get_u32(void) {
  static uint32_t last = 0, new = 0;
  while (new == last) {
    if ((RNG_SR & (RNG_SR_SECS | RNG_SR_CECS | RNG_SR_DRDY)) == RNG_SR_DRDY) {
      new = RNG_DR;
    }
  }
  last = new;
  return new;
}

void random_buffer(uint8_t *buf, size_t len) {
  uint32_t r = 0;
  for (size_t i = 0; i < len; i++) {
    if (i % 4 == 0) {
      r = rng_get_u32();
    }
    buf[i] = (r >> ((i % 4) * 8)) & 0xFF;
  }
}
#endif
