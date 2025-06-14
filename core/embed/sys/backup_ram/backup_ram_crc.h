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

#pragma once

#include <trezor_types.h>

#define BACKUP_RAM_CRC16_INITIAL 0xFFFF /** Initial value for CRC-16-CCITT*/

/**
 * @brief Calculate CRC-16-CCITT for the backup RAM storage.
 *
 * @param data Pointer to the data to calculate CRC for.
 * @param size Length of the data in bytes.
 * @param initial_crc Initial CRC value to start the calculation from. Use
 *  BACKUP_RAM_CRC16_INITIAL for a fresh calculation. Use the last calculated
 * CRC value to continue the calculation from a previous state.
 *
 * @return uint16_t Calculated CRC value.
 */
uint16_t backup_ram_crc16(const void *data, size_t size, uint16_t initial_crc);
