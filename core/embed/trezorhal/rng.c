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

#include STM32_HAL_H

#include "rng.h"

#pragma GCC optimize( \
    "no-stack-protector")  // applies to all functions in this file

void rng_init(void) {
  // enable TRNG peripheral clock
  // use the HAL version due to section 2.1.6 of STM32F42xx Errata sheet
  // "Delay after an RCC peripheral clock enabling"
  __HAL_RCC_RNG_CLK_ENABLE();
  RNG->CR = RNG_CR_RNGEN;  // enable TRNG
}

uint32_t rng_read(const uint32_t previous, const uint32_t compare_previous) {
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

uint32_t rng_get(void) {
  // reason for keeping history: RM0090 section 24.3.1 FIPS continuous random
  // number generator test
  static uint32_t previous = 0, current = 0;
  if (previous == current) {
    previous = rng_read(previous, 0);
  } else {
    previous = current;
  }
  current = rng_read(previous, 1);
  return current;
}
