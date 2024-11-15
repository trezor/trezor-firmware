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

#include <util/flash_otp.h>

#define OTP_BLOCK_SIZE 32
#define FLASH_SECTOR_OTP (FLASH_SECTOR_COUNT)

static uint8_t OTP_BUFFER[OTP_BLOCK_SIZE * 64];

void flash_otp_init(void) {
  // fill OTP buffer with ones
  memset(OTP_BUFFER, 0xFF, sizeof(OTP_BUFFER));
}

secbool flash_otp_read(uint8_t block, uint8_t offset, uint8_t *data,
                       uint8_t datalen) {
  if (offset + datalen > OTP_BLOCK_SIZE) {
    return secfalse;
  }
  uint32_t offset_in_sector = block * OTP_BLOCK_SIZE + offset;
  memcpy(data, OTP_BUFFER + offset_in_sector, datalen);
  return sectrue;
}

secbool flash_otp_write(uint8_t block, uint8_t offset, const uint8_t *data,
                        uint8_t datalen) {
  if (offset + datalen > OTP_BLOCK_SIZE) {
    return secfalse;
  }
  uint32_t offset_in_sector = block * OTP_BLOCK_SIZE + offset;
  uint8_t *flash = OTP_BUFFER + offset_in_sector;
  for (int i = 0; i < datalen; i++) {
    if ((flash[i] & data[i]) != data[i]) {
      return secfalse;  // we cannot change zeroes to ones
    }
    flash[i] = data[i];
  }
  return sectrue;
}

secbool flash_otp_lock(uint8_t block) { return secfalse; }

secbool flash_otp_is_locked(uint8_t block) { return secfalse; }
