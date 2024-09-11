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

#include STM32_HAL_H

#include "flash_otp.h"
#include "common.h"
#include "flash.h"
#include "mpu.h"

#ifdef KERNEL_MODE

void flash_otp_init() {
  // intentionally left empty
}

secbool flash_otp_read(uint8_t block, uint8_t offset, uint8_t *data,
                       uint8_t datalen) {
  if (block >= FLASH_OTP_NUM_BLOCKS ||
      offset + datalen > FLASH_OTP_BLOCK_SIZE) {
    return secfalse;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);

  for (uint8_t i = 0; i < datalen; i++) {
    data[i] = *(__IO uint8_t *)(FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE +
                                offset + i);
  }

  mpu_restore(mpu_mode);

  return sectrue;
}

secbool flash_otp_write(uint8_t block, uint8_t offset, const uint8_t *data,
                        uint8_t datalen) {
  if (datalen % 16 != 0) {
    return secfalse;
  }
  if (block >= FLASH_OTP_NUM_BLOCKS ||
      offset + datalen > FLASH_OTP_BLOCK_SIZE) {
    return secfalse;
  }

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);

  ensure(flash_unlock_write(), NULL);
  for (uint8_t i = 0; i < datalen; i += 16) {
    uint32_t address =
        FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE + offset + i;
    ensure(sectrue * (HAL_OK == HAL_FLASH_Program(FLASH_TYPEPROGRAM_QUADWORD_NS,
                                                  address, (uint32_t)&data[i])),
           NULL);
  }
  ensure(flash_lock_write(), NULL);

  mpu_restore(mpu_mode);

  return sectrue;
}

secbool flash_otp_lock(uint8_t block) {
  if (block >= FLASH_OTP_NUM_BLOCKS) {
    return secfalse;
  }

  // check that all quadwords in the block have been written to
  volatile uint8_t *addr =
      (__IO uint8_t *)(FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE);

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);

  secbool qw_locked = secfalse;
  for (uint8_t i = 0; i < FLASH_OTP_BLOCK_SIZE; i++) {
    if (addr[i] != 0xFF) {
      qw_locked = sectrue;
    }
    if (i % 16 == 15 && qw_locked == secfalse) {
      mpu_restore(mpu_mode);
      return secfalse;
    }
  }

  mpu_restore(mpu_mode);

  return sectrue;
}

secbool flash_otp_is_locked(uint8_t block) {
  if (block >= FLASH_OTP_NUM_BLOCKS) {
    return secfalse;
  }

  secbool is_locked = secfalse;

  // considering block locked if any quadword in the block is non-0xFF
  volatile uint8_t *addr =
      (__IO uint8_t *)(FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE);

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_OTP);

  for (uint8_t i = 0; i < FLASH_OTP_BLOCK_SIZE; i++) {
    if (addr[i] != 0xFF) {
      is_locked = sectrue;
      break;
    }
  }

  mpu_restore(mpu_mode);

  return is_locked;
}

#endif  // KERNEL_MODE
