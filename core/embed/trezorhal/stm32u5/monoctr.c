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
#include "flash_area.h"
#include "model.h"
#include "secret.h"

static int32_t get_offset(monoctr_type_t type) {
  switch (type) {
    case MONOCTR_BOOTLOADER_VERSION:
      return SECRET_MONOTONIC_COUNTER_OFFSET;
    case MONOCTR_FIRMWARE_VERSION:
      return SECRET_MONOTONIC_COUNTER2_OFFSET;
    default:
      return -1;
  }
}

secbool monoctr_write(monoctr_type_t type, uint8_t value) {
  if (value > MONOCTR_MAX_VALUE) {
    return secfalse;
  }

  int32_t offset = get_offset(type);

  if (offset < 0) {
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

  for (int i = 0; i < value; i++) {
    uint32_t data[4] = {0};
    secret_write((uint8_t *)data, offset + i * 16, 16);
  }

  return sectrue;
}

secbool monoctr_read(monoctr_type_t type, uint8_t *value) {
  int32_t offset = get_offset(type);

  if (offset < 0) {
    return secfalse;
  }

  const uint8_t *counter_addr = flash_area_get_address(
      &SECRET_AREA, offset, SECRET_MONOTONIC_COUNTER_LEN);

  if (counter_addr == NULL) {
    return secfalse;
  }

  int counter = 0;

  int i = 0;

  for (i = 0; i < SECRET_MONOTONIC_COUNTER_LEN / 16; i++) {
    secbool not_cleared = sectrue;
    for (int j = 0; j < 16; j++) {
      if (counter_addr[i * 16 + j] != 0xFF) {
        not_cleared = secfalse;
        break;
      }
    }

    if (not_cleared != sectrue) {
      counter++;
    } else {
      break;
    }
  }

  for (; i < SECRET_MONOTONIC_COUNTER_LEN / 16; i++) {
    secbool not_cleared = sectrue;
    for (int j = 0; j < 16; j++) {
      if (counter_addr[i * 16 + j] != 0xFF) {
        not_cleared = secfalse;
        break;
      }
    }

    if (not_cleared != sectrue) {
      // monotonic counter is not valid
      return secfalse;
    }
  }

  if (value != NULL) {
    *value = counter;
  } else {
    return secfalse;
  }

  return sectrue;
}
