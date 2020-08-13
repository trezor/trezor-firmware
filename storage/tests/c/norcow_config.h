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

#ifndef __NORCOW_CONFIG_H__
#define __NORCOW_CONFIG_H__

#include "flash.h"

#define NORCOW_SECTOR_COUNT 2
#define NORCOW_SECTOR_SIZE (64 * 1024)
#define NORCOW_SECTORS \
  { 4, 16 }

/*
 * The length of the sector header in bytes. The header is preserved between
 * sector erasures.
 */
#if TREZOR_MODEL == T
#define NORCOW_HEADER_LEN 0
#elif TREZOR_MODEL == 1
#define NORCOW_HEADER_LEN (0x100)
#else
#error Unknown Trezor model
#endif

/*
 * Current storage version.
 */
#define NORCOW_VERSION ((uint32_t)0x00000003)

#endif
