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

#ifndef TREZORHAL_OPTIGA_COMMON_H
#define TREZORHAL_OPTIGA_COMMON_H

typedef enum _optiga_result {
  OPTIGA_SUCCESS = 0,     // Operation completed successfully.
  OPTIGA_ERR_I2C_WRITE,   // HAL failed on I2C write.
  OPTIGA_ERR_I2C_READ,    // HAL failed on I2C read.
  OPTIGA_ERR_BUSY,        // Optiga is busy processing another command.
  OPTIGA_ERR_TIMEOUT,     // Optiga did not return data within the time limit.
  OPTIGA_ERR_SIZE,        // Input or output exceeds buffer size.
  OPTIGA_ERR_CRC,         // Invalid CRC.
  OPTIGA_ERR_UNEXPECTED,  // Optiga returned unexpected data.
  OPTIGA_ERR_PROCESS,     // Processing error.
  OPTIGA_ERR_PARAM,       // Invalid command parameters.
  OPTIGA_ERR_CMD,         // Command error. See error code data object 0xF1C2.
} optiga_result;

#endif
