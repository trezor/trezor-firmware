/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2019 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "otp.h"
#include <libopencm3/stm32/flash.h>

#define FLASH_OTP_BASE 0x1FFF7800U
#define FLASH_OTP_LOCK_BASE 0x1FFF7A00U

bool flash_otp_is_locked(uint8_t block) {
  return 0x00 == *(volatile uint8_t *)(FLASH_OTP_LOCK_BASE + block);
}

bool flash_otp_lock(uint8_t block) {
  if (block >= FLASH_OTP_NUM_BLOCKS) {
    return false;
  }
  flash_unlock();
  flash_program_byte(FLASH_OTP_LOCK_BASE + block, 0x00);
  flash_lock();
  return true;
}

bool flash_otp_read(uint8_t block, uint8_t offset, uint8_t *data,
                    uint8_t datalen) {
  if (block >= FLASH_OTP_NUM_BLOCKS ||
      offset + datalen > FLASH_OTP_BLOCK_SIZE) {
    return false;
  }
  for (uint8_t i = 0; i < datalen; i++) {
    data[i] = *(volatile uint8_t *)(FLASH_OTP_BASE +
                                    block * FLASH_OTP_BLOCK_SIZE + offset + i);
  }
  return true;
}

bool flash_otp_write(uint8_t block, uint8_t offset, const uint8_t *data,
                     uint8_t datalen) {
  if (block >= FLASH_OTP_NUM_BLOCKS ||
      offset + datalen > FLASH_OTP_BLOCK_SIZE) {
    return false;
  }
  flash_unlock();
  for (uint8_t i = 0; i < datalen; i++) {
    uint32_t address =
        FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE + offset + i;
    flash_program_byte(address, data[i]);
  }
  flash_lock();
  return true;
}
