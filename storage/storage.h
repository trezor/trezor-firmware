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

#ifndef __STORAGE_H__
#define __STORAGE_H__

#include <stddef.h>
#include <stdint.h>
#include "secbool.h"

// The length of the external salt in bytes.
#define EXTERNAL_SALT_SIZE 32

// If the top bit of APP is set, then the value is not encrypted.
#define FLAG_PUBLIC 0x80

// If the top two bits of APP are set, then the value is not encrypted and it
// can be written even when the storage is locked.
#define FLAGS_WRITE 0xC0

// Mask for extracting the "real" app_id.
#define FLAGS_APPID 0x3F

typedef secbool (*PIN_UI_WAIT_CALLBACK)(uint32_t wait, uint32_t progress,
                                        const char *message);

void storage_init(PIN_UI_WAIT_CALLBACK callback, const uint8_t *salt,
                  const uint16_t salt_len);
void storage_wipe(void);
secbool storage_is_unlocked(void);
void storage_lock(void);
secbool storage_unlock(uint32_t pin, const uint8_t *ext_salt);
secbool storage_has_pin(void);
secbool storage_pin_fails_increase(void);
uint32_t storage_get_pin_rem(void);
secbool storage_change_pin(uint32_t oldpin, uint32_t newpin,
                           const uint8_t *old_ext_salt,
                           const uint8_t *new_ext_salt);
secbool storage_has_wipe_code(void);
secbool storage_change_wipe_code(uint32_t pin, const uint8_t *ext_salt,
                                 uint32_t wipe_code);
secbool storage_get(const uint16_t key, void *val, const uint16_t max_len,
                    uint16_t *len);
secbool storage_set(const uint16_t key, const void *val, const uint16_t len);
secbool storage_delete(const uint16_t key);
secbool storage_set_counter(const uint16_t key, const uint32_t count);
secbool storage_next_counter(const uint16_t key, uint32_t *count);

#endif
