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

#include <sys/rng.h>

#include "rand.h"

void rng_fill_buffer(void* buffer, size_t buffer_size) {
#ifdef USE_INSECURE_PRNG

  // Use PRNG implemented in crypto/rand_insecure.c
  random_buffer((uint8_t*)buffer, buffer_size);

#else

  static FILE* frand = NULL;
  if (!frand) {
    frand = fopen("/dev/urandom", "r");
  }
  ensure(sectrue * (frand != NULL), "fopen failed");
  ensure(sectrue * (buffer_size == fread(buffer, 1, buffer_size, frand)),
         "fread failed");

#endif
}
