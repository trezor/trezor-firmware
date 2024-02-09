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
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#include "common.h"
#include "sdcard.h"
#include "sdcard_emu_mock.h"

#define SDCARD_BLOCKS (sd_mock.capacity_bytes / SDCARD_BLOCK_SIZE)

static void sdcard_exit(void) {
  if (sd_mock.buffer == NULL) {
    return;
  }
  int r = munmap(sd_mock.buffer, sd_mock.capacity_bytes);
  ensure(sectrue * (r == 0), "munmap failed");
  sd_mock.buffer = NULL;
}

void sdcard_init(void) {
  if (sd_mock.buffer != NULL) {
    return;
  }

  // check whether the file exists and it has the correct size
  struct stat sb;
  int r = stat(sd_mock.filename, &sb);
  int should_clear = 0;

  // (re)create if non existent or wrong size
  if (r != 0 || sb.st_size != sd_mock.capacity_bytes) {
    int fd = open(sd_mock.filename, O_RDWR | O_CREAT | O_TRUNC, (mode_t)0600);
    ensure(sectrue * (fd >= 0), "open failed");
    r = ftruncate(fd, sd_mock.capacity_bytes);
    ensure(sectrue * (r == 0), "truncate failed");
    r = close(fd);
    ensure(sectrue * (r == 0), "close failed");

    should_clear = 1;
  }

  // mmap file
  int fd = open(sd_mock.filename, O_RDWR);
  ensure(sectrue * (fd >= 0), "open failed");

  void *map = mmap(0, sd_mock.capacity_bytes, PROT_READ | PROT_WRITE,
                   MAP_SHARED, fd, 0);
  ensure(sectrue * (map != MAP_FAILED), "mmap failed");

  sd_mock.buffer = (uint8_t *)map;

  if (should_clear) {
    for (int i = 0; i < sd_mock.capacity_bytes; ++i) sd_mock.buffer[i] = 0xFF;
  }

  sd_mock.powered = secfalse;

  atexit(sdcard_exit);
}

secbool sdcard_is_present(void) { return sd_mock.inserted; }

secbool sdcard_power_on(void) {
  if (sd_mock.inserted == secfalse) {
    return secfalse;
  }
  sdcard_init();
  sd_mock.powered = sectrue;
  return sectrue;
}

void sdcard_power_off(void) { sd_mock.powered = secfalse; }

uint64_t sdcard_get_capacity_in_bytes(void) {
  return sd_mock.powered == sectrue ? sd_mock.capacity_bytes : 0;
}

secbool sdcard_read_blocks(uint32_t *dest, uint32_t block_num,
                           uint32_t num_blocks) {
  if (sectrue != sd_mock.powered) {
    return secfalse;
  }
  if (block_num >= SDCARD_BLOCKS) {
    return secfalse;
  }
  if (num_blocks > SDCARD_BLOCKS - block_num) {
    return secfalse;
  }
  memcpy(dest, sd_mock.buffer + block_num * SDCARD_BLOCK_SIZE,
         num_blocks * SDCARD_BLOCK_SIZE);
  return sectrue;
}

secbool sdcard_write_blocks(const uint32_t *src, uint32_t block_num,
                            uint32_t num_blocks) {
  if (sectrue != sd_mock.powered) {
    return secfalse;
  }
  if (block_num >= SDCARD_BLOCKS) {
    return secfalse;
  }
  if (num_blocks > SDCARD_BLOCKS - block_num) {
    return secfalse;
  }
  memcpy(sd_mock.buffer + block_num * SDCARD_BLOCK_SIZE, src,
         num_blocks * SDCARD_BLOCK_SIZE);
  return sectrue;
}

uint64_t __wur sdcard_get_manuf_id(void) { return (uint64_t)sd_mock.manuf_ID; }
uint64_t __wur sdcard_get_serial_num(void) {
  return (uint64_t)sd_mock.serial_number;
}
