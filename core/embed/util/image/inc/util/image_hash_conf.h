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

#include <trezor_model.h>
#include <trezor_types.h>

#ifdef IMAGE_HASH_SHA256
#include "sha2.h"
#define IMAGE_HASH_DIGEST_LENGTH SHA256_DIGEST_LENGTH
#if defined(USE_HASH_PROCESSOR) && defined(SECURE_MODE)
#include <sec/hash_processor.h>
#define IMAGE_HASH_CTX hash_sha256_context_t
#define IMAGE_HASH_INIT(ctx) hash_processor_sha256_init(ctx)
#define IMAGE_HASH_UPDATE(ctx, data, len) \
  hash_processor_sha256_update(ctx, data, len)
#define IMAGE_HASH_FINAL(ctx, output) hash_processor_sha256_final(ctx, output)
#define IMAGE_HASH_CALC(data, len, output) \
  hash_processor_sha256_calc(data, len, output)
#else
#define IMAGE_HASH_CTX SHA256_CTX
#define IMAGE_HASH_INIT(ctx) sha256_Init(ctx)
#define IMAGE_HASH_UPDATE(ctx, data, len) sha256_Update(ctx, data, len)
#define IMAGE_HASH_FINAL(ctx, output) sha256_Final(ctx, output)
#define IMAGE_HASH_CALC(data, len, output) sha256_Raw(data, len, output)
#endif

#elif defined IMAGE_HASH_BLAKE2S
#include "blake2s.h"
#define IMAGE_HASH_DIGEST_LENGTH BLAKE2S_DIGEST_LENGTH
#define IMAGE_HASH_CTX BLAKE2S_CTX
#define IMAGE_HASH_INIT(ctx) blake2s_Init(ctx, BLAKE2S_DIGEST_LENGTH)
#define IMAGE_HASH_UPDATE(ctx, data, len) blake2s_Update(ctx, data, len)
#define IMAGE_HASH_FINAL(ctx, output) \
  blake2s_Final(ctx, output, BLAKE2S_DIGEST_LENGTH)
#define IMAGE_HASH_CALC(data, len, output) \
  blake2s(data, len, output, BLAKE2S_DIGEST_LENGTH)
#else
#error "IMAGE_HASH_SHA256 or IMAGE_HASH_BLAKE2S must be defined"
#endif
