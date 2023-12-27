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

#ifndef __NORCOW_H__
#define __NORCOW_H__

#include <stdint.h>
#include "secbool.h"

/*
 * Storage parameters
 */

#include "norcow_config.h"

/*
 * Initialize storage
 */
void norcow_init(uint32_t *norcow_version);

/*
 * Wipe the storage
 */
void norcow_wipe(void);

/*
 * Looks for the given key, returns status of the operation
 */
secbool norcow_get(uint16_t key, const void **val, uint16_t *len);

/*
 * Reads the next entry in the storage starting at offset. Returns secfalse if
 * there is none.
 */
secbool norcow_get_next(uint32_t *offset, uint16_t *key, const void **val,
                        uint16_t *len);

/*
 * Sets the given key, returns status of the operation. If NULL is passed
 * as val, then norcow_set allocates a new key of size len. The value should
 * then be written using norcow_update_bytes().
 */
secbool norcow_set(uint16_t key, const void *val, uint16_t len);
secbool norcow_set_ex(uint16_t key, const void *val, uint16_t len,
                      secbool *found);

/*
 * Deletes the given key, returns status of the operation.
 */
secbool norcow_delete(uint16_t key);

secbool norcow_set_counter(uint16_t key, uint32_t count);

secbool norcow_next_counter(uint16_t key, uint32_t *count);

/*
 * Update the value of the given key, data are written sequentially from start
 * Data are guaranteed to be stored on flash once the total item len is reached.
 *
 * It is only allowed to update bytes of pristine items, i.e. items that were
 * not yet set after allocating them with norcow_set(key, NULL, len).
 */
secbool norcow_update_bytes(const uint16_t key, const uint8_t *data,
                            const uint16_t len);

/*
 * Complete storage version upgrade
 */
secbool norcow_upgrade_finish(void);

#endif
