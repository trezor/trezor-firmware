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

#include "backup_ram_crc.h"

uint16_t backup_ram_crc16(const void* data, size_t size, uint16_t initial_crc) {
  uint16_t crc = initial_crc;
  const uint8_t* ptr = (const uint8_t*)data;

  // CRC-16-CCITT polynomial x^16 + x^12 + x^5 + 1
  const uint16_t polynomial = 0x1021;

  for (size_t i = 0; i < size; i++) {
    crc ^= (uint16_t)ptr[i] << 8;
    for (uint8_t bit = 0; bit < 8; bit++) {
      if (crc & 0x8000) {
        crc = (crc << 1) ^ polynomial;
      } else {
        crc = crc << 1;
      }
    }
  }

  return crc;
}
