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

#include <sec/rng_strong.h>

#ifdef SECURE_MODE

#ifdef USE_OPTIGA
#include <sec/optiga.h>
#endif

#ifdef USE_TROPIC
#include <sec/tropic.h>
#endif

#include "memzero.h"
#include "rand.h"

bool rng_fill_buffer_strong(void* buffer, size_t buffer_size) {
  rng_fill_buffer(buffer, buffer_size);

  uint8_t* dst = (uint8_t*)buffer;
  size_t remaining = buffer_size;

  uint8_t block[32] = {0};

  while (remaining > 0) {
    size_t block_size = MIN(remaining, sizeof(block));
#ifdef USE_OPTIGA
    if (!optiga_random_buffer(block, block_size)) {
      return false;
    }

    for (size_t i = 0; i < block_size; i++) {
      dst[i] ^= block[i];
    }
#endif
#ifdef USE_TROPIC
    if (!tropic_random_buffer(block, block_size)) {
      return false;
    }

    for (size_t i = 0; i < block_size; i++) {
      dst[i] ^= block[i];
    }
#endif
    dst += block_size;
    remaining -= block_size;
  }

  memzero(block, sizeof(block));
  return true;
}

void rng_fill_buffer_strong_time(uint32_t* time_ms) {
  // Assuming the buffer size is 32 bytes
#ifdef USE_OPTIGA
  optiga_random_buffer_time(time_ms);
#endif
#ifdef USE_TROPIC
  tropic_random_buffer_time(time_ms);
#endif
}

#endif  // SECURE_MODE
