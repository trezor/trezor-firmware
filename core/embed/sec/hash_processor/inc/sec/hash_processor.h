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

#ifdef SECURE_MODE

#include <trezor_types.h>

#define HASH_SHA256_BUFFER_SIZE 4

typedef struct {
  uint32_t length;                         /*!< nb bytes in buffer */
  uint8_t buffer[HASH_SHA256_BUFFER_SIZE]; /*!< data being processed */
} hash_sha256_context_t;

// Initialize the hash processor
void hash_processor_init(void);

// Calculate SHA256 hash of data
// for best performance, data should be 32-bit aligned - as this allows DMA to
// be used
void hash_processor_sha256_calc(const uint8_t *data, uint32_t len,
                                uint8_t *hash);

// Initialize the hash context
// This serves for calculating hashes of multiple data blocks
void hash_processor_sha256_init(hash_sha256_context_t *ctx);

// Feed the hash next chunk of data
void hash_processor_sha256_update(hash_sha256_context_t *ctx,
                                  const uint8_t *data, uint32_t len);

// Finalize the hash calculation, retrieve the digest
void hash_processor_sha256_final(hash_sha256_context_t *ctx, uint8_t *output);

#endif  // SECURE_MODE
