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

#include STM32_HAL_H

#include <string.h>

#include "common.h"
#include "flash.h"

#if defined STM32F427xx || defined STM32F429xx
#define FLASH_SECTOR_COUNT 24
#elif defined STM32F405x
#define FLASH_SECTOR_COUNT 12
#else
#error Unknown MCU
#endif

// note: FLASH_SR_RDERR is STM32F42xxx and STM32F43xxx specific (STM32F427)
// (reference RM0090 section 3.7.5)
#if !defined STM32F427xx && !defined STM32F429xx
#define FLASH_SR_RDERR 0
#endif

#define FLASH_STATUS_ALL_FLAGS                                            \
  (FLASH_SR_RDERR | FLASH_SR_PGSERR | FLASH_SR_PGPERR | FLASH_SR_PGAERR | \
   FLASH_SR_WRPERR | FLASH_SR_SOP | FLASH_SR_EOP)

// see docs/memory.md for more information

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
#if defined STM32F427xx || defined STM32F429xx
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
    [24] = 0x08200000,  // last element - not a valid sector
#elif defined STM32F405xx
    [12] = 0x08100000,  // last element - not a valid sector
#else
#error Unknown MCU
#endif
};

uint32_t flash_wait_and_clear_status_flags(void) {
  while (FLASH->SR & FLASH_SR_BSY)
    ;  // wait for all previous flash operations to complete
  const uint32_t result =
      FLASH->SR & FLASH_STATUS_ALL_FLAGS;  // get the current status flags
  FLASH->SR |= FLASH_STATUS_ALL_FLAGS;     // clear all status flags
  return result;
}

secbool flash_unlock_write(void) {
  HAL_FLASH_Unlock();
  FLASH->SR |= FLASH_STATUS_ALL_FLAGS;  // clear all status flags
  return sectrue;
}

secbool flash_lock_write(void) {
  HAL_FLASH_Lock();
  return sectrue;
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
  return (const void *)addr;
}

uint32_t flash_sector_size(uint16_t sector) {
  if (sector >= FLASH_SECTOR_COUNT) {
    return 0;
  }
  return FLASH_SECTOR_TABLE[sector + 1] - FLASH_SECTOR_TABLE[sector];
}

secbool flash_area_erase_bulk(const flash_area_t *area, int count,
                              void (*progress)(int pos, int len)) {
  ensure(flash_unlock_write(), NULL);
  FLASH_EraseInitTypeDef EraseInitStruct = {0};
  EraseInitStruct.TypeErase = FLASH_TYPEERASE_SECTORS;
  EraseInitStruct.VoltageRange = FLASH_VOLTAGE_RANGE_3;
  EraseInitStruct.NbSectors = 1;

  int total_sectors = 0;
  int done_sectors = 0;
  for (int a = 0; a < count; a++) {
    for (int i = 0; i < area[a].num_subareas; i++) {
      total_sectors += area[a].subarea[i].num_sectors;
    }
  }
  if (progress) {
    progress(0, total_sectors);
  }

  for (int a = 0; a < count; a++) {
    for (int s = 0; s < area[a].num_subareas; s++) {
      for (int i = 0; i < area[a].subarea[s].num_sectors; i++) {
        int sector = area[a].subarea[s].first_sector + i;

        EraseInitStruct.Sector = sector;
        uint32_t SectorError;
        if (HAL_FLASHEx_Erase(&EraseInitStruct, &SectorError) != HAL_OK) {
          ensure(flash_lock_write(), NULL);
          return secfalse;
        }
        // check whether the sector was really deleted (contains only 0xFF)
        const uint32_t addr_start = FLASH_SECTOR_TABLE[sector],
                       addr_end = FLASH_SECTOR_TABLE[sector + 1];
        for (uint32_t addr = addr_start; addr < addr_end; addr += 4) {
          if (*((const uint32_t *)addr) != 0xFFFFFFFF) {
            ensure(flash_lock_write(), NULL);
            return secfalse;
          }
        }
        done_sectors++;
        if (progress) {
          progress(done_sectors, total_sectors);
        }
      }
    }
  }
  ensure(flash_lock_write(), NULL);
  return sectrue;
}

secbool flash_area_erase_partial(const flash_area_t *area, uint32_t offset,
                                 uint32_t *bytes_erased) {
  uint32_t sector_offset = 0;
  *bytes_erased = 0;

  for (int s = 0; s < area->num_subareas; s++) {
    for (int i = 0; i < area->subarea[s].num_sectors; i++) {
      uint32_t sector_index = area->subarea[s].first_sector + i;
      uint32_t sector_size = FLASH_SECTOR_TABLE[sector_index + 1] -
                             FLASH_SECTOR_TABLE[sector_index];

      if (offset == sector_offset) {
        ensure(flash_unlock_write(), NULL);

        FLASH_EraseInitTypeDef erase_init = {
            .TypeErase = FLASH_TYPEERASE_SECTORS,
            .VoltageRange = FLASH_VOLTAGE_RANGE_3,
            .Sector = sector_index,
            .NbSectors = 1};

        uint32_t sector_error;

        if (HAL_FLASHEx_Erase(&erase_init, &sector_error) != HAL_OK) {
          ensure(flash_lock_write(), NULL);
          return secfalse;
        }

        ensure(flash_lock_write(), NULL);

        *bytes_erased = sector_size;
        return sectrue;
      }

      sector_offset += sector_size;
    }
  }

  if (offset == sector_offset) {
    return sectrue;
  }

  return secfalse;
}

secbool flash_write_byte(uint16_t sector, uint32_t offset, uint8_t data) {
  uint32_t address = (uint32_t)flash_get_address(sector, offset, 1);
  if (address == 0) {
    return secfalse;
  }
  if (data != (data & *((const uint8_t *)address))) {
    return secfalse;
  }
  if (HAL_OK != HAL_FLASH_Program(FLASH_TYPEPROGRAM_BYTE, address, data)) {
    return secfalse;
  }
  if (data != *((const uint8_t *)address)) {
    return secfalse;
  }
  return sectrue;
}

secbool flash_write_word(uint16_t sector, uint32_t offset, uint32_t data) {
  uint32_t address = (uint32_t)flash_get_address(sector, offset, 4);
  if (address == 0) {
    return secfalse;
  }
  if (offset % sizeof(uint32_t)) {  // we write only at 4-byte boundary
    return secfalse;
  }
  if (data != (data & *((const uint32_t *)address))) {
    return secfalse;
  }
  if (HAL_OK != HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, address, data)) {
    return secfalse;
  }
  if (data != *((const uint32_t *)address)) {
    return secfalse;
  }
  return sectrue;
}

#define FLASH_OTP_LOCK_BASE 0x1FFF7A00U

secbool flash_otp_read(uint8_t block, uint8_t offset, uint8_t *data,
                       uint8_t datalen) {
  if (block >= FLASH_OTP_NUM_BLOCKS ||
      offset + datalen > FLASH_OTP_BLOCK_SIZE) {
    return secfalse;
  }
  for (uint8_t i = 0; i < datalen; i++) {
    data[i] = *(__IO uint8_t *)(FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE +
                                offset + i);
  }
  return sectrue;
}

secbool flash_otp_write(uint8_t block, uint8_t offset, const uint8_t *data,
                        uint8_t datalen) {
  if (block >= FLASH_OTP_NUM_BLOCKS ||
      offset + datalen > FLASH_OTP_BLOCK_SIZE) {
    return secfalse;
  }
  ensure(flash_unlock_write(), NULL);
  for (uint8_t i = 0; i < datalen; i++) {
    uint32_t address =
        FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE + offset + i;
    ensure(sectrue * (HAL_OK == HAL_FLASH_Program(FLASH_TYPEPROGRAM_BYTE,
                                                  address, data[i])),
           NULL);
  }
  ensure(flash_lock_write(), NULL);
  return sectrue;
}

secbool flash_otp_lock(uint8_t block) {
  if (block >= FLASH_OTP_NUM_BLOCKS) {
    return secfalse;
  }
  ensure(flash_unlock_write(), NULL);
  HAL_StatusTypeDef ret = HAL_FLASH_Program(FLASH_TYPEPROGRAM_BYTE,
                                            FLASH_OTP_LOCK_BASE + block, 0x00);
  ensure(flash_lock_write(), NULL);
  return sectrue * (ret == HAL_OK);
}

secbool flash_otp_is_locked(uint8_t block) {
  return sectrue * (0x00 == *(__IO uint8_t *)(FLASH_OTP_LOCK_BASE + block));
}
