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

#ifndef FLASH_H
#define FLASH_H

#include <stdint.h>
#include <stdlib.h>
#include "secbool.h"

#define FLASH_SECTOR_COUNT 24

void flash_init(void);

secbool __wur flash_unlock(void);
secbool __wur flash_lock(void);

const void *flash_get_address(uint8_t sector, uint32_t offset, uint32_t size);

secbool __wur flash_erase_sectors(const uint8_t *sectors, int len,
                                  void (*progress)(int pos, int len));
static inline secbool flash_erase_sector(uint8_t sector) {
  return flash_erase_sectors(&sector, 1, NULL);
}
secbool __wur flash_write_byte(uint8_t sector, uint32_t offset, uint8_t data);
secbool __wur flash_write_word(uint8_t sector, uint32_t offset, uint32_t data);

#endif
