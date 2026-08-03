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

#ifdef SECURE_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sec/hash_processor.h>
#include <sys/irq.h>
#include <sys/mpu.h>
#include "memzero.h"
#include "sha2.h"

// STM32H5 HASH peripheral driver.
//
// The STM32H5 uses the unified HASH HAL API: the algorithm is selected in the
// init structure and hashing is driven by the generic HAL_HASH_Start /
// HAL_HASH_Accumulate / HAL_HASH_AccumulateLast functions, unlike the
// per-algorithm HAL_HASHEx_SHA256_* functions of the STM32U5.
//
// TODO(H5): this uses the blocking (polling) API only. The DMA path
// (HAL_HASH_Start_DMA, which on the H5 takes the output buffer directly) can be
// added for performance once validated on hardware.

HASH_HandleTypeDef hhash = {0};

void hash_processor_init(void) {
  __HAL_RCC_HASH_CLK_ENABLE();

  // 8-bit (byte) input data => byte swap; SHA256 algorithm.
  hhash.Init.DataType = HASH_BYTE_SWAP;
  hhash.Init.Algorithm = HASH_ALGOSELECTION_SHA256;
  HAL_HASH_Init(&hhash);
}

void hash_processor_sha256_calc(const uint8_t *data, uint32_t len,
                                uint8_t *hash) {
  HAL_HASH_Start(&hhash, data, len, hash, HAL_MAX_DELAY);
}

void hash_processor_sha256_init(hash_sha256_context_t *ctx) {
  memzero(ctx, sizeof(hash_sha256_context_t));
}

void hash_processor_sha256_update(hash_sha256_context_t *ctx,
                                  const uint8_t *data, uint32_t len) {
  if (ctx->length > 0) {
    uint32_t chunk = HASH_SHA256_BUFFER_SIZE - ctx->length;
    if (chunk > len) {
      chunk = len;
    }
    memcpy(ctx->buffer + ctx->length, data, chunk);
    ctx->length += chunk;
    data += chunk;
    len -= chunk;
    if (ctx->length == HASH_SHA256_BUFFER_SIZE) {
      HAL_HASH_Accumulate(&hhash, (uint8_t *)ctx->buffer, HASH_SHA256_BUFFER_SIZE,
                          HAL_MAX_DELAY);
      ctx->length = 0;
      memzero(ctx->buffer, HASH_SHA256_BUFFER_SIZE);
    }
  }

  uint32_t len_aligned = len & ~(HASH_SHA256_BUFFER_SIZE - 1);
  uint32_t len_rest = len & (HASH_SHA256_BUFFER_SIZE - 1);

  while (len_aligned > 0) {
    uint32_t chunk = len_aligned > 0x8000 ? 0x8000 : len_aligned;
    HAL_HASH_Accumulate(&hhash, (uint8_t *)data, chunk, HAL_MAX_DELAY);
    data += chunk;
    len_aligned -= chunk;
  }

  if (len_rest > 0) {
    memcpy(ctx->buffer, data, len_rest);
    ctx->length = len_rest;
  }
}

void hash_processor_sha256_final(hash_sha256_context_t *ctx, uint8_t *output) {
  uint32_t tmp_out[SHA256_DIGEST_LENGTH / sizeof(uint32_t)] = {0};
  memzero(ctx->buffer + ctx->length, HASH_SHA256_BUFFER_SIZE - ctx->length);
  HAL_HASH_AccumulateLast(&hhash, (uint8_t *)ctx->buffer, ctx->length,
                          (uint8_t *)tmp_out, HAL_MAX_DELAY);
  ctx->length = 0;
  memzero(ctx->buffer, HASH_SHA256_BUFFER_SIZE);
  memcpy(output, tmp_out, SHA256_DIGEST_LENGTH);
  memzero(tmp_out, sizeof(tmp_out));
}

#endif  // SECURE_MODE
