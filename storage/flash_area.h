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

#ifndef FLASH_AREA_H
#define FLASH_AREA_H

#include <stdint.h>
#include "secbool.h"

#include "flash.h"

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

typedef struct {
  uint16_t first_sector;
  uint16_t num_sectors;
} flash_subarea_t;

typedef struct {
  flash_subarea_t subarea[4];
  uint8_t num_subareas;
} flash_area_t;

uint32_t flash_area_get_size(const flash_area_t *area);

uint16_t flash_area_total_sectors(const flash_area_t *area);

const void *flash_area_get_address(const flash_area_t *area, uint32_t offset,
                                   uint32_t size);

#if defined FLASH_BIT_ACCESS
secbool __wur flash_area_write_byte(const flash_area_t *area, uint32_t offset,
                                    uint8_t data);
secbool __wur flash_area_write_word(const flash_area_t *area, uint32_t offset,
                                    uint32_t data);
#endif
secbool __wur flash_area_write_quadword(const flash_area_t *area,
                                        uint32_t offset, const uint32_t *data);

secbool __wur flash_area_write_burst(const flash_area_t *area, uint32_t offset,
                                     const uint32_t *data);

secbool __wur flash_area_write_block(const flash_area_t *area, uint32_t offset,
                                     const flash_block_t block);

secbool __wur flash_area_erase(const flash_area_t *area,
                               void (*progress)(int pos, int len));
secbool __wur flash_area_erase_bulk(const flash_area_t *area, int count,
                                    void (*progress)(int pos, int len));

// Erases the single sector in the designated flash area
// The 'offset' parameter must indicate the relative sector offset within the
// flash area If 'offset' is outside the bounds of the flash area,
// 'bytes_erased' is set to 0 otherwise, 'bytes_erased' is set to the size of
// the erased sector
secbool __wur flash_area_erase_partial(const flash_area_t *area,
                                       uint32_t offset, uint32_t *bytes_erased);

#endif  // FLASH_AREA_H
