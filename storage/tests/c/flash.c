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

#include <assert.h>
#include <stdlib.h>
#include <string.h>

#include "common.h"
#include "flash.h"
#include "norcow_config.h"

#define FLASH_SECTOR_COUNT 24

static const uint32_t FLASH_START = 0x08000000;
static const uint32_t FLASH_END = 0x08200000;
static const uint32_t FLASH_SECTOR_TABLE[FLASH_SECTOR_COUNT + 1] = {
    [0] = FLASH_START,  // - 0x08003FFF |  16 KiB
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
    [12] = 0x08100000,  // - 0x08103FFF |  16 KiB
    [13] = 0x08104000,  // - 0x08107FFF |  16 KiB
    [14] = 0x08108000,  // - 0x0810BFFF |  16 KiB
    [15] = 0x0810C000,  // - 0x0810FFFF |  16 KiB
    [16] = 0x08110000,  // - 0x0811FFFF |  64 KiB
    [17] = 0x08120000,  // - 0x0813FFFF | 128 KiB
    [18] = 0x08140000,  // - 0x0815FFFF | 128 KiB
    [19] = 0x08160000,  // - 0x0817FFFF | 128 KiB
    [20] = 0x08180000,  // - 0x0819FFFF | 128 KiB
    [21] = 0x081A0000,  // - 0x081BFFFF | 128 KiB
    [22] = 0x081C0000,  // - 0x081DFFFF | 128 KiB
    [23] = 0x081E0000,  // - 0x081FFFFF | 128 KiB
    [24] = FLASH_END,   // last element - not a valid sector
};
const uint32_t FLASH_SIZE = FLASH_END - FLASH_START;
uint8_t *FLASH_BUFFER = NULL;

secbool flash_unlock_write(void) { return sectrue; }

secbool flash_lock_write(void) { return sectrue; }

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

const void *flash_get_address(uint16_t sector, uint32_t offset, uint32_t size) {
  if (sector >= FLASH_SECTOR_COUNT) {
    return NULL;
  }
  const uint32_t addr = FLASH_SECTOR_TABLE[sector] + offset;
  const uint32_t next = FLASH_SECTOR_TABLE[sector + 1];
  if (addr + size > next) {
    return NULL;
  }
  return FLASH_BUFFER + addr - FLASH_SECTOR_TABLE[0];
}

secbool flash_sector_erase(uint16_t sector) {
  if (sector >= FLASH_SECTOR_COUNT) {
    return secfalse;
  }
  const uint32_t offset = FLASH_SECTOR_TABLE[sector] - FLASH_SECTOR_TABLE[0];
  const uint32_t size =
      FLASH_SECTOR_TABLE[sector + 1] - FLASH_SECTOR_TABLE[sector];
  memset(FLASH_BUFFER + offset, 0xFF, size);
  return sectrue;
}

static secbool flash_write(uint16_t sector, uint32_t offset,
                           const uint8_t *data, size_t data_size) {
  // check proper alignment
  if ((offset % data_size) != 0) {
    return secfalse;
  }

  uint8_t *flash = (uint8_t *)flash_get_address(sector, offset, data_size);

  if (flash == NULL) {
    return secfalse;
  }

  // check if not writing ones to zeroes
  for (size_t i = 0; i < data_size; i++) {
    if (data[i] != (data[i] & flash[i])) {
      return secfalse;
    }
  }

  memcpy(flash, data, data_size);

  return sectrue;
}

secbool flash_write_byte(uint16_t sector, uint32_t offset, uint8_t data) {
  return flash_write(sector, offset, (uint8_t *)&data, sizeof(uint8_t));
}

secbool flash_write_word(uint16_t sector, uint32_t offset, uint32_t data) {
  return flash_write(sector, offset, (uint8_t *)&data, sizeof(uint32_t));
}

secbool flash_write_quadword(uint16_t sector, uint32_t offset,
                             const uint32_t *data) {
  return flash_write(sector, offset, (uint8_t *)data, 4 * sizeof(uint32_t));
}

secbool flash_write_burst(uint16_t sector, uint32_t offset,
                          const uint32_t *data) {
  return flash_write(sector, offset, (uint8_t *)data, 32 * sizeof(uint32_t));
}

secbool flash_write_block(uint16_t sector, uint32_t offset,
                          const flash_block_t block) {
#if defined FLASH_BIT_ACCESS
  return flash_write_word(sector, offset, block[0]);
#else

  uint32_t *addr =
      (uint32_t *)flash_get_address(sector, offset, sizeof(flash_block_t));

  secbool old_all_ff = sectrue;
  secbool new_all_00 = sectrue;
  secbool all_equal = sectrue;

  for (int i = 0; i < FLASH_BLOCK_WORDS; i++) {
    if (addr[i] != 0xFFFFFFFF) {
      old_all_ff = secfalse;
    }
    if (block[i] != 0x00000000) {
      new_all_00 = secfalse;
    }
    if (addr[i] != ((uint32_t *)block)[i]) {
      all_equal = secfalse;
    }
  }

  if (!(old_all_ff == sectrue || new_all_00 == sectrue ||
        all_equal == sectrue)) {
    return secfalse;
  }

  for (int i = 0; i < FLASH_BLOCK_WORDS; i++) {
    if (sectrue !=
        flash_write_word(sector, offset + i * sizeof(uint32_t), block[i])) {
      return secfalse;
    }
  }
  return sectrue;
#endif
}
