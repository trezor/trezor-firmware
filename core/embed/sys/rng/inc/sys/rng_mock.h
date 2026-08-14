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

#ifdef TREZOR_EMULATOR

#include <trezor_types.h>

/**
 * Deterministic, source-unique random stream for emulated entropy sources.
 *
 * On real hardware each entropy source of rng_fill_buffer_strong() is an
 * independent chip. The emulator mirrors that with one deterministic stream
 * per source, so tests can verify every source's contribution to the strong
 * RNG output.
 *
 * The stream is SHA256(tag || seed || counter) consumed in 32-byte blocks,
 * with the diversification tag naming the source.
 */
typedef struct {
  const char* tag;   // diversification string, e.g. "Optiga"
  uint32_t seed;     // set by rng_mock_reseed()
  uint32_t counter;  // advances by one per 32-byte block
} rng_mock_stream_t;

/**
 * @brief Resets the stream to the beginning of the sequence for `seed`.
 */
void rng_mock_reseed(rng_mock_stream_t* stream, uint32_t seed);

/**
 * @brief Fills a buffer from the stream.
 */
void rng_mock_fill(rng_mock_stream_t* stream, uint8_t* dest, size_t size);

#endif  // TREZOR_EMULATOR
