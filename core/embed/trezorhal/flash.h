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

#ifndef TREZORHAL_FLASH_H
#define TREZORHAL_FLASH_H

#include <stdint.h>
#include <stdlib.h>
#include "platform.h"
#include "secbool.h"

#define FLASH_OTP_NUM_BLOCKS 16
#define FLASH_OTP_BLOCK_SIZE 32

/**
 * Flash driver interface is designed to abstract away differences between
 * various MCUs used in Trezor devices.
 *
 * Generally, flash memory is divided into sectors. On different MCUs, sectors
 * may have different sizes, and therefore, different number of sectors are used
 * for a given purpose. For example, on STM32F4, the sectors are relatively
 * large so we use single sector for Storage. On STM32U5, the sectors are
 * smaller, so we use multiple sectors for the Storage. Storage implementation
 * should not care about this, and should use flash_area_t interface to access
 * the flash memory.
 *
 * flash_area_t represents a location in flash memory. It may be contiguous, or
 * it may be composed of multiple non-contiguous subareas.
 *
 * flash_subarea_t represents a contiguous area in flash memory, specified by
 * first_sector and num_sectors.
 */

#include "flash_common.h"

void flash_init(void);

secbool flash_write_byte(uint16_t sector, uint32_t offset, uint8_t data);

secbool flash_write_word(uint16_t sector, uint32_t offset, uint32_t data);

uint32_t flash_wait_and_clear_status_flags(void);

secbool __wur flash_otp_read(uint8_t block, uint8_t offset, uint8_t *data,
                             uint8_t datalen);
secbool __wur flash_otp_write(uint8_t block, uint8_t offset,
                              const uint8_t *data, uint8_t datalen);
secbool __wur flash_otp_lock(uint8_t block);
secbool __wur flash_otp_is_locked(uint8_t block);

#endif  // TREZORHAL_FLASH_H
