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

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sys/flash.h>

#ifdef KERNEL_MODE

#ifdef STM32U585xx
#define FLASH_BANK_PAGES 128
#define FLASH_SECTOR_COUNT (FLASH_BANK_PAGES * 2)
#else
#define FLASH_BANK_PAGES 256
#define FLASH_SECTOR_COUNT (FLASH_BANK_PAGES * 2)
#endif

#define FLASH_STATUS_ALL_FLAGS \
  (FLASH_NSSR_PGSERR | FLASH_NSSR_PGAERR | FLASH_NSSR_WRPERR | FLASH_NSSR_EOP)

#ifdef SECMON
extern uint32_t _codelen;
#define SECMON_SIZE ((uint32_t) & _codelen)
#define KERNEL_SECTOR_START \
  ((FIRMWARE_START_S + SECMON_SIZE - FLASH_BASE) / FLASH_PAGE_SIZE)

flash_area_t FIRMWARE_AREA = {0};
#endif  // SECMON

void flash_init(void) {
#ifdef SECMON
  // FIRMWARE_AREA is defined here because it depends on the
  // SECMON size which is not known at compile time.

  FIRMWARE_AREA = (flash_area_t){
      .num_subareas = 2,
      .subarea[0] =
          {
              .first_sector = FIRMWARE_SECTOR_START,
              .num_sectors = KERNEL_SECTOR_START - FIRMWARE_SECTOR_START,
          },
      .subarea[1] =
          {
              .first_sector = KERNEL_SECTOR_START,
              .num_sectors = FIRMWARE_SECTOR_END - KERNEL_SECTOR_START + 1,
          },
  };
#endif
}

static bool flash_sector_is_secure(uint32_t sector) {
#if defined(__ARM_FEATURE_CMSE) && (__ARM_FEATURE_CMSE == 3U)
#ifdef SECMON
  if (sector < KERNEL_SECTOR_START) {
    return true;
  } else if (sector >= STORAGE_1_SECTOR_START &&
             sector <= STORAGE_1_SECTOR_END) {
    return true;
  } else if (sector >= STORAGE_2_SECTOR_START &&
             sector <= STORAGE_2_SECTOR_END) {
    return true;
  }
#else
  return true;
#endif
#endif
  return false;
}

const void *flash_get_address(uint16_t sector, uint32_t offset, uint32_t size) {
  if (sector >= FLASH_SECTOR_COUNT) {
    return NULL;
  }

  if (offset + size > FLASH_PAGE_SIZE) {
    return NULL;
  }

  uint32_t base_addr =
      flash_sector_is_secure(sector) ? FLASH_BASE_S : FLASH_BASE_NS;

  return (const void *)(base_addr + FLASH_PAGE_SIZE * sector + offset);
}

uint32_t flash_sector_size(uint16_t first_sector, uint16_t sector_count) {
  if (first_sector + sector_count > FLASH_SECTOR_COUNT) {
    return 0;
  }
  return FLASH_PAGE_SIZE * sector_count;
}

uint16_t flash_sector_find(uint16_t first_sector, uint32_t offset) {
  return first_sector + offset / FLASH_PAGE_SIZE;
}

secbool flash_unlock_write(void) {
  HAL_FLASH_Unlock();
  FLASH->NSSR |= FLASH_STATUS_ALL_FLAGS;  // clear all status flags
#if defined(__ARM_FEATURE_CMSE) && (__ARM_FEATURE_CMSE == 3U)
  FLASH->SECSR |= FLASH_STATUS_ALL_FLAGS;  // clear all status flags
#endif
  return sectrue;
}

secbool flash_lock_write(void) {
  HAL_FLASH_Lock();
  return sectrue;
}

secbool flash_sector_erase(uint16_t sector) {
  if (sector >= FLASH_SECTOR_COUNT) {
    return secfalse;
  }

  FLASH_EraseInitTypeDef EraseInitStruct = {
      .TypeErase = FLASH_TYPEERASE_PAGES,
      .Banks = FLASH_BANK_1,
      .Page = sector,
      .NbPages = 1,
  };

  if (sector >= FLASH_BANK_PAGES) {
    EraseInitStruct.Banks = FLASH_BANK_2;
    EraseInitStruct.Page = sector - FLASH_BANK_PAGES;
  }

  if (flash_sector_is_secure(sector)) {
    EraseInitStruct.TypeErase = FLASH_TYPEERASE_PAGES;
  }

  uint32_t sector_error = 0;

  if (HAL_FLASHEx_Erase(&EraseInitStruct, &sector_error) != HAL_OK) {
    return secfalse;
  }

  // check whether the sector was really deleted (contains only 0xFF)
  const uint32_t *sector_start =
      (const uint32_t *)flash_get_address(sector, 0, 0);

  const uint32_t *sector_end =
      sector_start + flash_sector_size(sector, 1) / sizeof(uint32_t);

  for (const uint32_t *addr = sector_start; addr < sector_end; addr++) {
    if (*addr != 0xFFFFFFFF) {
      return secfalse;
    }
  }

  return sectrue;
}

secbool flash_write_quadword(uint16_t sector, uint32_t offset,
                             const uint32_t *data) {
  uint32_t address =
      (uint32_t)flash_get_address(sector, offset, FLASH_QUADWORD_SIZE);
  if (address == 0) {
    return secfalse;
  }
  if (offset % FLASH_QUADWORD_SIZE) {  // we write only at 16-byte boundary
    return secfalse;
  }

  for (int i = 0; i < FLASH_QUADWORD_WORDS; i++) {
    if (data[i] != (data[i] & *((const uint32_t *)address + i))) {
      return secfalse;
    }
  }

  secbool all_match = sectrue;
  for (int i = 0; i < FLASH_QUADWORD_WORDS; i++) {
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

  for (int i = 0; i < FLASH_QUADWORD_WORDS; i++) {
    if (data[i] != *((const uint32_t *)address + i)) {
      return secfalse;
    }
  }
  return sectrue;
}

secbool flash_write_burst(uint16_t sector, uint32_t offset,
                          const uint32_t *data) {
  uint32_t address =
      (uint32_t)flash_get_address(sector, offset, FLASH_BURST_SIZE);
  if (address == 0) {
    return secfalse;
  }
  if (offset % FLASH_BURST_SIZE) {  // we write only at 128-byte boundary
    return secfalse;
  }

  for (int i = 0; i < FLASH_BURST_WORDS; i++) {
    if (data[i] != (data[i] & *((const uint32_t *)address + i))) {
      return secfalse;
    }
  }

  secbool all_match = sectrue;
  for (int i = 0; i < FLASH_BURST_WORDS; i++) {
    if (data[i] != *((const uint32_t *)address + i)) {
      all_match = secfalse;
      break;
    }
  }
  if (all_match == sectrue) {
    return sectrue;
  }

  if (HAL_OK !=
      HAL_FLASH_Program(FLASH_TYPEPROGRAM_BURST, address, (uint32_t)data)) {
    return secfalse;
  }

  for (int i = 0; i < FLASH_BURST_WORDS; i++) {
    if (data[i] != *((const uint32_t *)address + i)) {
      return secfalse;
    }
  }
  return sectrue;
}

secbool flash_write_block(uint16_t sector, uint32_t offset,
                          const flash_block_t block) {
  return flash_write_quadword(sector, offset, block);
}

#endif  // KERNEL_MODE
