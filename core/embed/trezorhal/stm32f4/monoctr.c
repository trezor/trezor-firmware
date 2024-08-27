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

#include "monoctr.h"
#include "flash_otp.h"
#include "model.h"
#include "string.h"

#if PRODUCTION
static int get_otp_block(monoctr_type_t type) {
  switch (type) {
    case MONOCTR_BOOTLOADER_VERSION:
      return FLASH_OTP_BLOCK_BOOTLOADER_VERSION;
    case MONOCTR_FIRMWARE_VERSION:
      return FLASH_OTP_BLOCK_FIRMWARE_VERSION;
    default:
      return -1;
  }
}
#endif

secbool monoctr_write(monoctr_type_t type, uint8_t value) {
#if PRODUCTION
  if (value > MONOCTR_MAX_VALUE) {
    return secfalse;
  }

  int block = get_otp_block(type);

  if (block < 0) {
    return secfalse;
  }

  uint8_t current_value = 0;

  if (sectrue != monoctr_read(type, &current_value)) {
    return secfalse;
  }

  if (value < current_value) {
    return secfalse;
  }

  if (value == current_value) {
    return sectrue;
  }

  uint8_t bits[FLASH_OTP_BLOCK_SIZE];
  for (int i = 0; i < FLASH_OTP_BLOCK_SIZE * 8; i++) {
    if (i < value) {
      bits[i / 8] &= ~(1 << (7 - (i % 8)));
    } else {
      bits[i / 8] |= (1 << (7 - (i % 8)));
    }
  }

  ensure(flash_otp_write(block, 0, bits, FLASH_OTP_BLOCK_SIZE), NULL);

#endif
  return sectrue;
}

secbool monoctr_read(monoctr_type_t type, uint8_t* value) {
#if PRODUCTION
  uint8_t bits[FLASH_OTP_BLOCK_SIZE];

  int block = get_otp_block(type);

  if (block < 0) {
    return secfalse;
  }

  ensure(flash_otp_read(block, 0, bits, FLASH_OTP_BLOCK_SIZE), NULL);

  int result = 0;

  int i;

  // Iterate through each bit position in the bit field
  for (i = 0; i < FLASH_OTP_BLOCK_SIZE * 8; i++) {
    // Calculate the byte and bit index within the byte
    int byteIndex = i / 8;
    int bitIndex = 7 - (i % 8);

    // Check if the current bit is 0
    if ((bits[byteIndex] & (1 << bitIndex)) == 0) {
      // If the bit is 0, increment the value
      result++;
    } else {
      // Stop when we find the first 1 bit
      break;
    }
  }

  for (; i < FLASH_OTP_BLOCK_SIZE * 8; i++) {
    // Calculate the byte and bit index within the byte
    int byteIndex = i / 8;
    int bitIndex = 7 - (i % 8);
    if ((bits[byteIndex] & (1 << bitIndex)) == 0) {
      // If the bit is 0, return false - the monotonic counter is not valid
      return secfalse;
    }
  }

  if (value != NULL) {
    *value = result;
  } else {
    return secfalse;
  }
#else

  *value = 0;

#endif

  return sectrue;
}
