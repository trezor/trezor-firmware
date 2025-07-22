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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sec/entropy.h>
#include <sys/mpu.h>
#include <util/flash_otp.h>
#include "rand.h"

#include "stm32f4xx_ll_utils.h"

#ifdef SECURE_MODE

static entropy_data_t g_entropy = {0};

void entropy_init(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);

  entropy_data_t* ent = &g_entropy;

  // collect entropy from UUID
  uint32_t w = LL_GetUID_Word0();
  memcpy(&ent->bytes[0], &w, 4);
  w = LL_GetUID_Word1();
  memcpy(&ent->bytes[4], &w, 4);
  w = LL_GetUID_Word2();
  memcpy(&ent->bytes[8], &w, 4);

  mpu_restore(mpu_mode);

  // set entropy in the OTP randomness block
  if (secfalse == flash_otp_is_locked(FLASH_OTP_BLOCK_RANDOMNESS)) {
    uint8_t rnd_bytes[FLASH_OTP_BLOCK_SIZE];
    random_buffer(rnd_bytes, FLASH_OTP_BLOCK_SIZE);
    ensure(flash_otp_write(FLASH_OTP_BLOCK_RANDOMNESS, 0, rnd_bytes,
                           FLASH_OTP_BLOCK_SIZE),
           NULL);
    ensure(flash_otp_lock(FLASH_OTP_BLOCK_RANDOMNESS), NULL);
  }
  // collect entropy from OTP randomness block
  ensure(flash_otp_read(FLASH_OTP_BLOCK_RANDOMNESS, 0, &ent->bytes[12],
                        FLASH_OTP_BLOCK_SIZE),
         NULL);

  ent->size = 12 + FLASH_OTP_BLOCK_SIZE;
}

void entropy_get(entropy_data_t* entropy) { *entropy = g_entropy; }

#endif  // SECURE_MODE
