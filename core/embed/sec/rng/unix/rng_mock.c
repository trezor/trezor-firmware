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

#include <sec/rng_mock.h>

#include "sha2.h"

void rng_mock_reseed(rng_mock_stream_t* stream, uint32_t seed) {
  stream->seed = seed;
  stream->counter = 0;
}

void rng_mock_fill(rng_mock_stream_t* stream, uint8_t* dest, size_t size) {
  while (size > 0) {
    uint8_t block[SHA256_DIGEST_LENGTH] = {0};
    SHA256_CTX ctx = {0};
    sha256_Init(&ctx);
    sha256_Update(&ctx, (const uint8_t*)stream->tag, strlen(stream->tag));
    sha256_Update(&ctx, (const uint8_t*)&stream->seed, sizeof(stream->seed));
    sha256_Update(&ctx, (const uint8_t*)&stream->counter,
                  sizeof(stream->counter));
    sha256_Final(&ctx, block);
    stream->counter++;

    size_t chunk = MIN(size, sizeof(block));
    memcpy(dest, block, chunk);
    dest += chunk;
    size -= chunk;
  }
}
