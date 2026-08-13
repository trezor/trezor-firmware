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
#include <sys/rng_use_flags.h>

#ifdef SECURE_MODE

#ifdef USE_OPTIGA
#include <sec/optiga.h>
#endif

#ifdef USE_TROPIC
#include <sec/tropic.h>
#endif

#include "memzero.h"
#include "rand.h"

void rng_fill_buffer_strong(void* buffer, size_t buffer_size) {
  rng_use_flags_clear();

  rng_fill_buffer(buffer, buffer_size);

#if defined(USE_OPTIGA) || defined(USE_TROPIC)
  uint8_t* dst = (uint8_t*)buffer;
  size_t remaining = buffer_size;

  while (remaining > 0) {
    uint8_t block[32] = {0};
    size_t block_size = MIN(remaining, sizeof(block));
    // A failed entropy source halts the device with a fatal error to ensure
    // that the error cannot be accidentally ignored.
#ifdef USE_OPTIGA
    ensure(sectrue * optiga_random_buffer(block, block_size),
           "Optiga entropy source failed");

    for (size_t i = 0; i < block_size; i++) {
      dst[i] ^= block[i];
    }
    memzero(block, sizeof(block));  // clear entropy from Optiga
#endif
#ifdef USE_TROPIC
    ensure(sectrue * tropic_random_buffer(block, block_size),
           "Tropic entropy source failed");

    for (size_t i = 0; i < block_size; i++) {
      dst[i] ^= block[i];
    }
    memzero(block, sizeof(block));  // clear entropy from Tropic
#endif
    dst += block_size;
    remaining -= block_size;
  }
#endif  // defined(USE_OPTIGA) || defined(USE_TROPIC)

  ensure_true(rng_use_flag_is_set(RNG_TYPE_MCU), "MCU entropy source not used");
#ifdef USE_OPTIGA
  ensure_true(rng_use_flag_is_set(RNG_TYPE_OPTIGA),
              "Optiga entropy source not used");
#endif
#ifdef USE_TROPIC
  ensure_true(rng_use_flag_is_set(RNG_TYPE_TROPIC),
              "Tropic entropy source not used");
#endif
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
