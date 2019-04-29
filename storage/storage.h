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

#ifndef __STORAGE_H__
#define __STORAGE_H__

#include <stddef.h>
#include <stdint.h>
#include "secbool.h"

typedef secbool (*PIN_UI_WAIT_CALLBACK)(uint32_t wait, uint32_t progress,
                                        const char *message);

void storage_init(PIN_UI_WAIT_CALLBACK callback, const uint8_t *salt,
                  const uint16_t salt_len);
void storage_wipe(void);
secbool storage_is_unlocked(void);
void storage_lock(void);
secbool storage_unlock(const uint32_t pin);
secbool storage_has_pin(void);
secbool storage_pin_fails_increase(void);
uint32_t storage_get_pin_rem(void);
secbool storage_change_pin(const uint32_t oldpin, const uint32_t newpin);
secbool storage_get(const uint16_t key, void *val, const uint16_t max_len,
                    uint16_t *len);
secbool storage_set(const uint16_t key, const void *val, uint16_t len);
secbool storage_delete(const uint16_t key);
secbool storage_set_counter(const uint16_t key, const uint32_t count);
secbool storage_next_counter(const uint16_t key, uint32_t *count);

#endif
