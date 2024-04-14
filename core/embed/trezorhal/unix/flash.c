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

#include <fcntl.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include <string.h>

#include "common.h"
#include "flash.h"
#include "model.h"
#include "profile.h"

#ifndef FLASH_FILE
#define FLASH_FILE profile_flash_path()
#endif

#if defined TREZOR_MODEL_T || defined TREZOR_MODEL_R
#define FLASH_SECTOR_COUNT 24
#elif defined TREZOR_MODEL_1
#define FLASH_SECTOR_COUNT 12
#elif defined TREZOR_MODEL_T3T1 || defined TREZOR_MODEL_T3B1
#define FLASH_SECTOR_COUNT 256
#else
#error Unknown MCU
#endif

static uint32_t FLASH_SECTOR_TABLE[FLASH_SECTOR_COUNT + 1] = {
#if defined TREZOR_MODEL_T || defined TREZOR_MODEL_R
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
#elif defined TREZOR_MODEL_1
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
#elif defined TREZOR_MODEL_T3T1 || defined TREZOR_MODEL_T3B1
    [0] = 0x08000000,  // - 0x08001FFF |   8 KiB
                       // rest is initialized in flash_init
#else
#error Unknown Trezor model
#endif
};

static uint8_t *FLASH_BUFFER = NULL;
static uint32_t FLASH_SIZE;

static void flash_exit(void) {
  int r = munmap(FLASH_BUFFER, FLASH_SIZE);
  ensure(sectrue * (r == 0), "munmap failed");
}

void flash_init(void) {
  if (FLASH_BUFFER) return;

#if defined TREZOR_MODEL_T3T1 || defined TREZOR_MODEL_T3B1
  for (size_t i = 0; i < FLASH_SECTOR_COUNT; i++) {
    FLASH_SECTOR_TABLE[i + 1] =
        FLASH_SECTOR_TABLE[i] + 0x2000;  // 8KiB size sectors
  }
#endif

  FLASH_SIZE = FLASH_SECTOR_TABLE[FLASH_SECTOR_COUNT] - FLASH_SECTOR_TABLE[0];

  // check whether the file exists and it has the correct size
  struct stat sb;
  int r = stat(FLASH_FILE, &sb);

  // (re)create if non existent or wrong size
  if (r != 0 || sb.st_size != FLASH_SIZE) {
    int fd = open(FLASH_FILE, O_RDWR | O_CREAT | O_TRUNC, (mode_t)0600);
    ensure(sectrue * (fd >= 0), "open failed");
    for (int i = 0; i < FLASH_SIZE / 16; i++) {
      ssize_t s = write(
          fd,
          "\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF",
          16);
      ensure(sectrue * (s >= 0), "write failed");
    }
    r = close(fd);
    ensure(sectrue * (r == 0), "close failed");
  }

  // mmap file
  int fd = open(FLASH_FILE, O_RDWR);
  ensure(sectrue * (fd >= 0), "open failed");

  void *map = mmap(0, FLASH_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
  ensure(sectrue * (map != MAP_FAILED), "mmap failed");

  FLASH_BUFFER = (uint8_t *)map;

  atexit(flash_exit);
}

secbool flash_unlock_write(void) { return sectrue; }

secbool flash_lock_write(void) { return sectrue; }

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

uint32_t flash_sector_size(uint16_t first_sector, uint16_t sector_count) {
  if (first_sector + sector_count > FLASH_SECTOR_COUNT) {
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

secbool flash_write_byte(uint16_t sector, uint32_t offset, uint8_t data) {
  uint8_t *flash = (uint8_t *)flash_get_address(sector, offset, 1);
  if (!flash) {
    return secfalse;
  }
  if ((flash[0] & data) != data) {
    return secfalse;  // we cannot change zeroes to ones
  }
  flash[0] = data;
  return sectrue;
}

secbool flash_write_word(uint16_t sector, uint32_t offset, uint32_t data) {
  if (offset % sizeof(uint32_t)) {  // we write only at 4-byte boundary
    return secfalse;
  }
  uint32_t *flash = (uint32_t *)flash_get_address(sector, offset, sizeof(data));
  if (!flash) {
    return secfalse;
  }
  if ((flash[0] & data) != data) {
    return secfalse;  // we cannot change zeroes to ones
  }
  flash[0] = data;
  return sectrue;
}

secbool flash_write_block(uint16_t sector, uint32_t offset,
                          const flash_block_t block) {
  if (offset % (sizeof(uint32_t) *
                FLASH_BLOCK_WORDS)) {  // we write only at block boundary
    return secfalse;
  }

  for (int i = 0; i < FLASH_BLOCK_WORDS; i++) {
    if (!flash_write_word(sector, offset + i * sizeof(uint32_t), block[i])) {
      return secfalse;
    }
  }
  return sectrue;
}
