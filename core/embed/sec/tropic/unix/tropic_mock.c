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

// Guard against this file ever being compiled into a production build. Every
// build that includes it must explicitly declare itself non-production, so
// that a build system which loses the PRODUCTION define fails loudly here
// instead of silently shipping the insecure PRNG.
#ifndef PRODUCTION
#error "PRODUCTION must be defined as 0 or 1 when compiling tropic_mock.c"
#elif PRODUCTION
#error "Mock RNG must not be compiled into a production build"
#endif

#ifndef USE_INSECURE_PRNG
#error "Mock RNG requires USE_INSECURE_PRNG"
#endif

#pragma message( \
    "NOT SUITABLE FOR PRODUCTION USE! Tropic entropy source is mocked with a deterministic stream.")

#include <trezor_rtl.h>

#include <sec/rng_mock.h>
#include <sec/tropic.h>

// Deterministic, Tropic-unique random stream.
static rng_mock_stream_t random_stream = {.tag = "Tropic"};

void tropic_random_reseed(uint32_t seed) {
  rng_mock_reseed(&random_stream, seed);
}

bool tropic_random_buffer(void* buffer, size_t length) {
  rng_mock_fill(&random_stream, (uint8_t*)buffer, length);
  return true;
}
