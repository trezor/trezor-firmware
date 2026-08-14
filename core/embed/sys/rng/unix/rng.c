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
#include <sys/rng_mock.h>

#include "rand.h"

// Guard against this file ever being compiled into a bare-metal build.

#ifndef TREZOR_EMULATOR
#error "Mock RNG must not be compiled into a non-emulator build"
#endif

_Static_assert(sizeof(void*) == 8,
               "Mock RNG compiled for a 32-bit target -- device build?");

#if !defined(__linux__) && !defined(__APPLE__) && !defined(_WIN32)
#error "Insecure PRNG is not supported on this target"
#endif

#if __STDC_HOSTED__ == 0
#error "Insecure PRNG must not be compiled for a freestanding target"
#endif

#ifdef USE_INSECURE_PRNG

// Deterministic, MCU-unique random stream.
static rng_mock_stream_t random_stream = {.tag = "<PRNG-MCU>"};

void rng_reseed(uint32_t seed) { rng_mock_reseed(&random_stream, seed); }

void rng_fill_buffer(void* buffer, size_t buffer_size) {
  rng_mock_fill(&random_stream, (uint8_t*)buffer, buffer_size);
}

// Implements random_buffer() function declared in crypto/rand.h
// as a wrapper for rng_fill_buffer().
void random_buffer(uint8_t* buf, size_t len) { rng_fill_buffer(buf, len); }

#endif  // USE_INSECURE_PRNG
