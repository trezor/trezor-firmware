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

#pragma GCC optimize( \
    "no-stack-protector")  // applies to all functions in this file

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sys/rng.h>

#include "rand.h"

#ifdef SECURE_MODE

void rng_init(void) {
  // enable TRNG peripheral clock
  // use the HAL version due to section 2.1.6 of STM32F42xx Errata sheet
  // "Delay after an RCC peripheral clock enabling"
  __HAL_RCC_RNG_CLK_ENABLE();
  RNG->CR = RNG_CR_RNGEN;  // enable TRNG
}

static uint32_t rng_read_u32(const uint32_t previous,
                             const uint32_t compare_previous) {
  uint32_t temp = previous;
  do {
    while ((RNG->SR & (RNG_SR_SECS | RNG_SR_CECS | RNG_SR_DRDY)) != RNG_SR_DRDY)
      ;              // wait until TRNG is ready
    temp = RNG->DR;  // read the data from the TRNG
  } while (compare_previous &&
           (temp == previous));  // RM0090 section 24.3.1 FIPS continuous random
                                 // number generator test
  return temp;
}

static uint32_t rng_get_u32(void) {
  // reason for keeping history: RM0090 section 24.3.1 FIPS continuous random
  // number generator test
  static uint32_t previous = 0, current = 0;
  if (previous == current) {
    previous = rng_read_u32(previous, 0);
  } else {
    previous = current;
  }
  current = rng_read_u32(previous, 1);
  return current;
}

void rng_fill_buffer(void* buffer, size_t buffer_size) {
  uint32_t* dst = (uint32_t*)buffer;
  size_t remaining = buffer_size;

  while (remaining >= sizeof(uint32_t)) {
    *dst++ = rng_get_u32();
    remaining -= sizeof(uint32_t);
  }

  if (remaining > 0) {
    uint32_t r = rng_get_u32();
    memcpy(dst, &r, remaining);
  }
}

#endif  // SECURE_MODE

// Implements random_buffer() function declared in crypto/rand.h
// as a wrapper for rng_fill_buffer().
void random_buffer(uint8_t* buf, size_t len) { rng_fill_buffer(buf, len); }
