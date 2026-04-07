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
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sec/fwutils.h>
#include <sec/image.h>
#include <sys/flash.h>
#include <sys/systask.h>

#include "blake2s.h"

#define FW_HASHING_CHUNK_SIZE 1024

typedef struct {
  bool initialized;
  BLAKE2S_CTX blake;
  uint32_t fw_offset;
  uint32_t fw_size;

} firmware_hash_context_t;

static firmware_hash_context_t g_hash_context[SYSTASK_MAX_TASKS];

int firmware_hash_start(const uint8_t* challenge, size_t challenge_len) {
  firmware_hash_context_t* ctx = &g_hash_context[systask_id(systask_active())];

  int err;

  if (challenge_len != 0) {
    err = blake2s_InitKey(&ctx->blake, BLAKE2S_DIGEST_LENGTH, challenge,
                          challenge_len);
  } else {
    err = blake2s_Init(&ctx->blake, BLAKE2S_DIGEST_LENGTH);
  }

  if (err != 0) {
    return -1;
  }

  ctx->fw_offset = 0;
  ctx->fw_size = flash_area_get_size(&FIRMWARE_AREA);

  ensure((ctx->fw_size % FW_HASHING_CHUNK_SIZE == 0) * sectrue,
         "Cannot compute FW hash.");

  ctx->initialized = true;
  return 0;
}

int firmware_hash_continue(uint8_t* hash, size_t hash_len) {
  firmware_hash_context_t* ctx = &g_hash_context[systask_id(systask_active())];

  memset(hash, 0, hash_len);

  if (!ctx->initialized) {
    return -1;
  }

  int n_chunks = 128;

  while (ctx->fw_offset < ctx->fw_size && n_chunks > 0) {
    const void* chunk_ptr = flash_area_get_address(
        &FIRMWARE_AREA, ctx->fw_offset, FW_HASHING_CHUNK_SIZE);

    int err = blake2s_Update(&ctx->blake, chunk_ptr, FW_HASHING_CHUNK_SIZE);
    if (err != 0) {
      ctx->initialized = false;
      return -1;
    }

    ctx->fw_offset += FW_HASHING_CHUNK_SIZE;
    --n_chunks;
  }

  if (ctx->fw_offset >= ctx->fw_size) {
    ctx->initialized = false;
    int err = blake2s_Final(&ctx->blake, hash, hash_len);
    if (err != 0) {
      return -1;
    }
  }

  return (100 * ctx->fw_offset) / ctx->fw_size;
}

secbool firmware_get_vendor(char* buff, size_t buff_size) {
  const void* data = flash_area_get_address(&FIRMWARE_AREA, 0, 0);

  vendor_header vhdr = {0};

  memset(buff, 0, buff_size);

  if (data == NULL || sectrue != read_vendor_header(data, &vhdr)) {
    return secfalse;
  }

  if (buff_size < vhdr.vstr_len + 1) {
    return secfalse;
  }

  memcpy(buff, vhdr.vstr, vhdr.vstr_len);

  return sectrue;
}

void firmware_invalidate_header(void) {
#ifdef STM32U5
  // on stm32u5, we need to disable the instruction cache before erasing the
  // firmware - otherwise, the write check will fail
  ICACHE->CR &= ~ICACHE_CR_EN;
#endif

  // erase start of the firmware (metadata) -> invalidate FW
  ensure(flash_unlock_write(), NULL);
  for (int i = 0; i < (1024 / FLASH_BLOCK_SIZE); i++) {
    flash_block_t data = {0};
    ensure(flash_area_write_block(&FIRMWARE_AREA, i * FLASH_BLOCK_SIZE, data),
           NULL);
  }
  ensure(flash_lock_write(), NULL);
}

#endif  // SECURE_MODE
