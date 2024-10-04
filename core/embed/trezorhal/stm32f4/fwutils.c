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

#ifndef TREZOR_EMULATOR
#include STM32_HAL_H
#endif

#include <string.h>

#include "blake2s.h"
#include "error_handling.h"
#include "flash.h"
#include "flash_area.h"
#include "fwutils.h"
#include "image.h"
#include "model.h"

#ifdef KERNEL_MODE

#define FW_HASHING_CHUNK_SIZE 1024

secbool firmware_calc_hash(const uint8_t* challenge, size_t challenge_len,
                           uint8_t* hash, size_t hash_len,
                           firmware_hash_callback_t callback,
                           void* callback_context) {
  BLAKE2S_CTX ctx;

  if (challenge_len != 0) {
    if (blake2s_InitKey(&ctx, BLAKE2S_DIGEST_LENGTH, challenge,
                        challenge_len) != 0) {
      return secfalse;
    }
  } else {
    blake2s_Init(&ctx, BLAKE2S_DIGEST_LENGTH);
  }

  uint32_t firmware_size = flash_area_get_size(&FIRMWARE_AREA);
  uint32_t chunks = firmware_size / FW_HASHING_CHUNK_SIZE;

  ensure((firmware_size % FW_HASHING_CHUNK_SIZE == 0) * sectrue,
         "Cannot compute FW hash.");

  for (int i = 0; i < chunks; i++) {
    if (callback != NULL && (i % 128 == 0)) {
      callback(callback_context, i, chunks);
    }

    const void* data = flash_area_get_address(
        &FIRMWARE_AREA, i * FW_HASHING_CHUNK_SIZE, FW_HASHING_CHUNK_SIZE);

    if (data == NULL) {
      return secfalse;
    }

    blake2s_Update(&ctx, data, FW_HASHING_CHUNK_SIZE);
  }

  if (callback != NULL) {
    callback(callback_context, chunks, chunks);
  }

  if (blake2s_Final(&ctx, hash, hash_len) != 0) {
    return secfalse;
  }

  return sectrue;
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

#endif  // KERNEL_MODE
