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

#include <sec/rng.h>

#if SECURE_MODE

#ifdef USE_OPTIGA
#include <sec/optiga.h>
#endif

#ifdef USE_TROPIC
#include <sec/tropic.h>
#endif

#include "memzero.h"
#include "rand.h"

void rng_fill_buffer(void* buffer, size_t buffer_size) {
  uint32_t* dst = (uint32_t*)buffer;
  size_t remaining = buffer_size;

  while (remaining >= sizeof(uint32_t)) {
    *dst++ = rng_get();
    remaining -= sizeof(uint32_t);
  }

  if (remaining > 0) {
    uint32_t r = rng_get();
    memcpy(dst, &r, remaining);
  }
}

bool rng_fill_buffer_strong(void* buffer, size_t buffer_size) {
  rng_fill_buffer(buffer, buffer_size);

  uint8_t* dst = (uint8_t*)buffer;
  size_t remaining = buffer_size;

  static const int bumper = 4;  // !@# workaround

  uint8_t block[32 + bumper];

  while (remaining > 0) {
    size_t block_size = MIN(remaining, sizeof(block) - bumper);
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

#endif  // SECURE_MODE

#ifndef SECURE_MODE
uint32_t rng_get(void) {
  uint32_t temp = 0;
  // Note: In non-secure mode we use rng_fill_buffer() since rng_get() is not
  // available as a smcall/syscall.
  rng_fill_buffer(&temp, sizeof(temp));
  return temp;
}
#endif  // !SECURE_MODE

#ifndef USE_INSECURE_PRNG
// Re-implementation of random32() function declared in crypto/rand.h
// to use MCU TRNG instead of crypto library PRNG.
uint32_t random32(void) { return rng_get(); }
#endif

// Re-implementation of weak random_buffer() function defined in crypto/rand.c
// to be the same as rng_fill_buffer() function.
void random_buffer(uint8_t* buf, size_t len) { rng_fill_buffer(buf, len); }
