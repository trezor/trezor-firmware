/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#ifndef __NORCOW_H__
#define __NORCOW_H__

#include <stdint.h>
#include "secbool.h"

/*
 * Storage parameters:
 */

#define NORCOW_SECTOR_COUNT  2
#if TREZOR_MODEL == T
#define NORCOW_SECTOR_SIZE   (64*1024)
#elif TREZOR_MODEL == 1
#define NORCOW_SECTOR_SIZE   (16*1024)
#else
#error Unknown TREZOR Model
#endif

/*
 * Initialize storage
 */
void norcow_init(void);

/*
 * Wipe the storage
 */
void norcow_wipe(void);

/*
 * Looks for the given key, returns status of the operation
 */
secbool norcow_get(uint16_t key, const void **val, uint16_t *len);

/*
 * Sets the given key, returns status of the operation
 */
secbool norcow_set(uint16_t key, const void *val, uint16_t len);

/*
 * Update a word in flash in the given key at the given offset.
 * Note that you can only change bits from 1 to 0.
 */
secbool norcow_update(uint16_t key, uint16_t offset, uint32_t value);

#endif
