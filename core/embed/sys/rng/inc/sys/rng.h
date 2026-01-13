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

#pragma once

#include <trezor_types.h>

#ifdef SECURE_MODE

/**
 * @brief Initializes the hardware random number generator.
 *
 */
void rng_init(void);

#endif

/**
 * @brief Fills a buffer with random bytes using the hardware RNG
 *
 * This function uses only single source of entropy - the hardware RNG
 * available on the microcontroller. It is fast but less suitable for
 * generating critical secrets.
 *
 * @param buffer Buffer to fill with random bytes.
 * @param buffer_size Size of the buffer in bytes.
 */
void rng_fill_buffer(void* buffer, size_t buffer_size);

/**
 * @brief Gets 32 bits of random data using from the hardware RNG.
 *
 * @return uint32_t Random data.
 */
static inline uint32_t rng_get(void) {
  uint32_t r = 0;
  rng_fill_buffer((uint8_t*)&r, sizeof(r));
  return r;
}
