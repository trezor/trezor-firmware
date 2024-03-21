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

#include <libopencm3/stm32/flash.h>
#include <string.h>

#include "common.h"
#include "flash.h"
#include "flash_area.h"
#include "memory.h"
#include "supervise.h"

#define STORAGE_AREAS_COUNT 2

static const uint32_t FLASH_SECTOR_TABLE[FLASH_SECTOR_COUNT + 1] = {
    [0] = 0x08000000,   // - 0x08003FFF |  16 KiB
    [1] = 0x08004000,   // - 0x08007FFF |  16 KiB
    [2] = 0x08008000,   // - 0x0800BFFF |  16 KiB
    [3] = 0x0800C000,   // - 0x0800FFFF |  16 KiB
    [4] = 0x08010000,   // - 0x0801FFFF |  64 KiB
    [5] = 0x08020000,   // - 0x0803FFFF | 128 KiB
    [6] = 0x08040000,   // - 0x0805FFFF | 128 KiB
    [7] = 0x08060000,   // - 0x0807FFFF | 128 KiB
    [8] = 0x08080000,   // - 0x0809FFFF | 128 KiB
    [9] = 0x080A0000,   // - 0x080BFFFF | 128 KiB
    [10] = 0x080C0000,  // - 0x080DFFFF | 128 KiB
    [11] = 0x080E0000,  // - 0x080FFFFF | 128 KiB
    [12] = 0x08100000,  // last element - not a valid sector
};

const flash_area_t STORAGE_AREAS[STORAGE_AREAS_COUNT] = {
    {
        .num_subareas = 1,
        .subarea[0] =
            {
                .first_sector = 2,
                .num_sectors = 1,
            },
    },
    {
        .num_subareas = 1,
        .subarea[0] =
            {
                .first_sector = 3,
                .num_sectors = 1,
            },
    },
};

static secbool flash_check_success(uint32_t status) {
  return (status & (FLASH_SR_PGAERR | FLASH_SR_PGPERR | FLASH_SR_PGSERR |
                    FLASH_SR_WRPERR))
             ? secfalse
             : sectrue;
}

secbool flash_unlock_write(void) {
  svc_flash_unlock();
  return sectrue;
}

secbool flash_lock_write(void) { return flash_check_success(svc_flash_lock()); }

const void *flash_get_address(uint16_t sector, uint32_t offset, uint32_t size) {
  if (sector >= FLASH_SECTOR_COUNT) {
    return NULL;
  }
  const uint32_t addr = FLASH_SECTOR_TABLE[sector] + offset;
  const uint32_t next = FLASH_SECTOR_TABLE[sector + 1];
  if (addr + size > next) {
    return NULL;
  }
  return (const void *)FLASH_PTR(addr);
}

uint32_t flash_sector_size(uint16_t first_sector, uint16_t sector_count) {
  if (first_sector + sector_count >= FLASH_SECTOR_COUNT) {
    return 0;
  }
  return FLASH_SECTOR_TABLE[first_sector + sector_count] -
         FLASH_SECTOR_TABLE[first_sector];
}

uint16_t flash_sector_find(uint16_t first_sector, uint32_t offset) {
  uint16_t sector = first_sector;

  while (sector < FLASH_SECTOR_COUNT) {
    uint32_t sector_size =
        FLASH_SECTOR_TABLE[sector + 1] - FLASH_SECTOR_TABLE[sector];

    if (offset < sector_size) {
      break;
    }
    offset -= sector_size;
    sector++;
  }

  return sector;
}

secbool flash_write_byte(uint16_t sector, uint32_t offset, uint8_t data) {
  uint8_t *address = (uint8_t *)flash_get_address(sector, offset, 1);
  if (address == NULL) {
    return secfalse;
  }

  if ((*address & data) != data) {
    return secfalse;
  }

  svc_flash_program(FLASH_CR_PROGRAM_X8);
  *(volatile uint8_t *)address = data;

  if (*address != data) {
    return secfalse;
  }

  return sectrue;
}

secbool flash_write_word(uint16_t sector, uint32_t offset, uint32_t data) {
  uint32_t *address = (uint32_t *)flash_get_address(sector, offset, 4);
  if (address == NULL) {
    return secfalse;
  }

  if (offset % 4 != 0) {
    return secfalse;
  }

  if ((*address & data) != data) {
    return secfalse;
  }

  svc_flash_program(FLASH_CR_PROGRAM_X32);
  *(volatile uint32_t *)address = data;

  if (*address != data) {
    return secfalse;
  }

  return sectrue;
}

secbool flash_write_block(uint16_t sector, uint32_t offset,
                          const flash_block_t block) {
  return flash_write_word(sector, offset, block[0]);
}

secbool flash_sector_erase(uint16_t sector) {
  svc_flash_erase_sector(sector);
  return sectrue;
}
