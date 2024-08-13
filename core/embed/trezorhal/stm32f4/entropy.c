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

#include <string.h>

#include "entropy.h"

#include "entropy.h"
#include "flash_otp.h"
#include "model.h"
#include "mpu.h"
#include "rand.h"

#include "stm32f4xx_ll_utils.h"

#ifdef KERNEL_MODE

static uint8_t g_hw_entropy[HW_ENTROPY_LEN];

void entropy_init(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);

  // collect entropy from UUID
  uint32_t w = LL_GetUID_Word0();
  memcpy(g_hw_entropy, &w, 4);
  w = LL_GetUID_Word1();
  memcpy(g_hw_entropy + 4, &w, 4);
  w = LL_GetUID_Word2();
  memcpy(g_hw_entropy + 8, &w, 4);

  mpu_restore(mpu_mode);

  // set entropy in the OTP randomness block
  if (secfalse == flash_otp_is_locked(FLASH_OTP_BLOCK_RANDOMNESS)) {
    uint8_t entropy[FLASH_OTP_BLOCK_SIZE];
    random_buffer(entropy, FLASH_OTP_BLOCK_SIZE);
    ensure(flash_otp_write(FLASH_OTP_BLOCK_RANDOMNESS, 0, entropy,
                           FLASH_OTP_BLOCK_SIZE),
           NULL);
    ensure(flash_otp_lock(FLASH_OTP_BLOCK_RANDOMNESS), NULL);
  }
  // collect entropy from OTP randomness block
  ensure(flash_otp_read(FLASH_OTP_BLOCK_RANDOMNESS, 0, g_hw_entropy + 12,
                        FLASH_OTP_BLOCK_SIZE),
         NULL);
}

void entropy_get(uint8_t *buf) { memcpy(buf, g_hw_entropy, HW_ENTROPY_LEN); }

#endif  // KERNEL_MODE
