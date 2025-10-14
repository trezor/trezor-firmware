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

#include <sec/time_estimate.h>

// The number of CPU cycles required to execute one iteration of PBKDF2.
#define PIN_PBKDF2_CYCLES_PER_ITER 11100

// The number of CPU cycles required to execute hash_to_curve_optiga()
#define HASH_TO_CURVE_CYCLES_PER_ITER 9450000

uint32_t time_estimate_clock_cycles_ms(uint32_t cycles) {
  extern uint32_t SystemCoreClock;
  return cycles / (SystemCoreClock / 1000);
}

uint32_t time_estimate_pbkdf2_ms(uint32_t iterations) {
  return time_estimate_clock_cycles_ms(PIN_PBKDF2_CYCLES_PER_ITER * iterations);
}

uint32_t time_estimate_hash_to_curve_ms() {
  return time_estimate_clock_cycles_ms(HASH_TO_CURVE_CYCLES_PER_ITER);
}
