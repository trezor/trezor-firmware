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
#include "model.h"

#define FLASH_SECTOR_COUNT (256 * 2)

#define FLASH_STATUS_ALL_FLAGS \
  (FLASH_NSSR_PGSERR | FLASH_NSSR_PGAERR | FLASH_NSSR_WRPERR | FLASH_NSSR_EOP)

uint32_t flash_wait_and_clear_status_flags(void) {
  while (FLASH->NSSR & FLASH_NSSR_BSY)
    ;  // wait for all previous flash operations to complete
  const uint32_t result =
      FLASH->NSSR & FLASH_STATUS_ALL_FLAGS;  // get the current status flags
  FLASH->NSSR |= FLASH_STATUS_ALL_FLAGS;     // clear all status flags
  return result;
}

secbool flash_unlock_write(void) {
  HAL_FLASH_Unlock();
  FLASH->NSSR |= FLASH_STATUS_ALL_FLAGS;  // clear all status flags
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
  const uint32_t addr = 0x08000000 + (FLASH_PAGE_SIZE * sector) + offset;
  const uint32_t next = 0x08000000 + (FLASH_PAGE_SIZE * (sector + 1));
  if (addr + size > next) {
    return NULL;
  }
  return (const void *)addr;
}

uint32_t flash_sector_size(uint16_t sector) {
  if (sector >= FLASH_SECTOR_COUNT) {
    return 0;
  }
  return FLASH_PAGE_SIZE;
}

uint32_t flash_subarea_get_size(const flash_subarea_t *sub) {
  return FLASH_PAGE_SIZE * sub->num_sectors;
}

uint32_t flash_area_get_size(const flash_area_t *area) {
  uint32_t size = 0;
  for (int i = 0; i < area->num_subareas; i++) {
    size += flash_subarea_get_size(&area->subarea[i]);
  }
  return size;
}

uint16_t flash_total_sectors(const flash_area_t *area) {
  uint16_t total = 0;
  for (int i = 0; i < area->num_subareas; i++) {
    total += area->subarea[i].num_sectors;
  }
  return total;
}

const void *flash_area_get_address(const flash_area_t *area, uint32_t offset,
                                   uint32_t size) {
  uint32_t tmp_offset = offset;

  for (int i = 0; i < area->num_subareas; i++) {
    uint16_t sector = area->subarea[i].first_sector;

    if (tmp_offset >= flash_subarea_get_size(area->subarea)) {
      tmp_offset -= flash_subarea_get_size(area->subarea);
      continue;
    }

    const uint32_t addr = 0x08000000 + (FLASH_PAGE_SIZE * sector) + tmp_offset;
    const uint32_t area_end =
        0x08000000 + (FLASH_PAGE_SIZE * (area->subarea[i].first_sector +
                                         area->subarea[i].num_sectors));
    if (addr + size > area_end) {
      return NULL;
    }
    return (const void *)addr;
  }
  return NULL;
}

int32_t flash_get_sector_num(const flash_area_t *area,
                             uint32_t sector_inner_num) {
  uint16_t sector = 0;
  uint16_t remaining = sector_inner_num;
  for (int i = 0; i < area->num_subareas; i++) {
    if (remaining < area->subarea[i].num_sectors) {
      sector = area->subarea[i].first_sector + remaining;
      return sector;
    } else {
      remaining -= area->subarea[i].num_sectors;
    }
  }

  return -1;
}

secbool flash_area_erase(const flash_area_t *area,
                         void (*progress)(int pos, int len)) {
  ensure(flash_unlock_write(), NULL);
  FLASH_EraseInitTypeDef EraseInitStruct;
  EraseInitStruct.TypeErase = FLASH_TYPEERASE_PAGES;
  EraseInitStruct.NbPages = 1;

  int total_pages = 0;
  int done_pages = 0;
  for (int i = 0; i < area->num_subareas; i++) {
    total_pages += area->subarea[i].num_sectors;
  }

  if (progress) {
    progress(0, total_pages);
  }

  for (int s = 0; s < area->num_subareas; s++) {
    for (int i = 0; i < area->subarea[s].num_sectors; i++) {
      int page = area->subarea[s].first_sector + i;
      if (page >= 256) {
        EraseInitStruct.Banks = FLASH_BANK_2;
      } else {
        EraseInitStruct.Banks = FLASH_BANK_1;
      }
      EraseInitStruct.Page = page;
      uint32_t SectorError;
      if (HAL_FLASHEx_Erase(&EraseInitStruct, &SectorError) != HAL_OK) {
        ensure(flash_lock_write(), NULL);
        return secfalse;
      }
      // check whether the sector was really deleted (contains only 0xFF)
      const uint32_t addr_start = (uint32_t)flash_get_address(page, 0, 0);
      const uint32_t addr_end = (uint32_t)flash_get_address(page + 1, 0, 0);

      for (uint32_t addr = addr_start; addr < addr_end; addr += 4) {
        if (*((const uint32_t *)addr) != 0xFFFFFFFF) {
          ensure(flash_lock_write(), NULL);
          return secfalse;
        }
      }
      done_pages++;
      if (progress) {
        progress(done_pages, total_pages);
      }
    }
  }
  ensure(flash_lock_write(), NULL);
  return sectrue;
}

secbool flash_area_erase_bulk(const flash_area_t *areas, int count,
                              void (*progress)(int pos, int len)) {
  ensure(flash_unlock_write(), NULL);
  FLASH_EraseInitTypeDef EraseInitStruct;
  EraseInitStruct.TypeErase = FLASH_TYPEERASE_PAGES;
  EraseInitStruct.NbPages = 1;

  int total_pages = 0;
  int done_pages = 0;
  for (int c = 0; c < count; c++) {
    for (int i = 0; i < areas[c].num_subareas; i++) {
      total_pages += areas[c].subarea[i].num_sectors;
    }
  }

  if (progress) {
    progress(0, total_pages);
  }

  for (int c = 0; c < count; c++) {
    for (int s = 0; s < areas[c].num_subareas; s++) {
      for (int i = 0; i < areas[c].subarea[s].num_sectors; i++) {
        int page = areas[c].subarea[s].first_sector + i;
        if (page >= 256) {
          EraseInitStruct.Banks = FLASH_BANK_2;
        } else {
          EraseInitStruct.Banks = FLASH_BANK_1;
        }
        EraseInitStruct.Page = page;
        uint32_t SectorError;
        if (HAL_FLASHEx_Erase(&EraseInitStruct, &SectorError) != HAL_OK) {
          ensure(flash_lock_write(), NULL);
          return secfalse;
        }
        // check whether the sector was really deleted (contains only 0xFF)
        const uint32_t addr_start = (uint32_t)flash_get_address(page, 0, 0);
        const uint32_t addr_end = (uint32_t)flash_get_address(page + 1, 0, 0);

        for (uint32_t addr = addr_start; addr < addr_end; addr += 4) {
          if (*((const uint32_t *)addr) != 0xFFFFFFFF) {
            ensure(flash_lock_write(), NULL);
            return secfalse;
          }
        }
        done_pages++;
        if (progress) {
          progress(done_pages, total_pages);
        }
      }
    }
  }
  ensure(flash_lock_write(), NULL);
  return sectrue;
}

secbool flash_write_quadword(uint16_t sector, uint32_t offset,
                             const uint32_t *data) {
  uint32_t address =
      (uint32_t)flash_get_address(sector, offset, 4 * sizeof(uint32_t));
  if (address == 0) {
    return secfalse;
  }
  if (offset % (4 * sizeof(uint32_t))) {  // we write only at 16-byte boundary
    return secfalse;
  }

  for (int i = 0; i < 4; i++) {
    if (data[i] != (data[i] & *((const uint32_t *)address + i))) {
      return secfalse;
    }
  }

  secbool all_match = sectrue;
  for (int i = 0; i < 4; i++) {
    if (data[i] != *((const uint32_t *)address + i)) {
      all_match = secfalse;
      break;
    }
  }
  if (all_match == sectrue) {
    return sectrue;
  }

  if (HAL_OK !=
      HAL_FLASH_Program(FLASH_TYPEPROGRAM_QUADWORD, address, (uint32_t)data)) {
    return secfalse;
  }

  for (int i = 0; i < 4; i++) {
    if (data[i] != *((const uint32_t *)address + i)) {
      return secfalse;
    }
  }
  return sectrue;
}

secbool flash_area_write_quadword(const flash_area_t *area, uint32_t offset,
                                  const uint32_t *data) {
  uint32_t tmp_offset = offset;
  for (int i = 0; i < area->num_subareas; i++) {
    uint16_t sector = area->subarea[i].first_sector;

    uint32_t sub_size = flash_subarea_get_size(&area->subarea[i]);
    if (tmp_offset >= sub_size) {
      tmp_offset -= sub_size;
      continue;
    }

    // in correct subarea
    for (int s = 0; s < area->subarea[i].num_sectors; s++) {
      const uint32_t sector_size = flash_sector_size(sector);
      if (tmp_offset >= sector_size) {
        tmp_offset -= sector_size;
        sector++;

        if (s == area->subarea[i].num_sectors - 1) {
          return secfalse;
        }
        continue;
      }
      // in correct sector
      return flash_write_quadword(sector, tmp_offset, data);
    }
  }
  return secfalse;
}

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
  if (datalen % 16 != 0) {
    return secfalse;
  }
  if (block >= FLASH_OTP_NUM_BLOCKS ||
      offset + datalen > FLASH_OTP_BLOCK_SIZE) {
    return secfalse;
  }
  ensure(flash_unlock_write(), NULL);
  for (uint8_t i = 0; i < datalen; i++) {
    uint32_t address =
        FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE + offset + i;
    ensure(sectrue * (HAL_OK == HAL_FLASH_Program(FLASH_TYPEPROGRAM_QUADWORD,
                                                  address, (uint32_t)data)),
           NULL);
  }
  ensure(flash_lock_write(), NULL);
  return sectrue;
}

secbool flash_otp_lock(uint8_t block) {
  // check that all quadwords in the block have been written to
  volatile uint8_t *addr =
      (__IO uint8_t *)(FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE);

  secbool qw_locked = secfalse;
  for (uint8_t i = 0; i < FLASH_OTP_BLOCK_SIZE; i++) {
    if (addr[i] != 0xFF) {
      qw_locked = sectrue;
    }
    if (i % 16 == 15 && qw_locked == secfalse) {
      return secfalse;
    }
  }
  return sectrue;
}

secbool flash_otp_is_locked(uint8_t block) {
  // considering block locked if any quadword in the block is non-0xFF
  volatile uint8_t *addr =
      (__IO uint8_t *)(FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE);

  for (uint8_t i = 0; i < FLASH_OTP_BLOCK_SIZE; i++) {
    if (addr[i] != 0xFF) {
      return sectrue;
    }
  }
  return secfalse;
}
