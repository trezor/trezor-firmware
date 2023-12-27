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

#include "flash_common.h"
#include "test_layout.h"

uint32_t flash_sector_size(uint16_t sector);

secbool flash_write_byte(uint16_t sector, uint32_t offset, uint8_t data);

secbool flash_write_word(uint16_t sector, uint32_t offset, uint32_t data);

#endif
