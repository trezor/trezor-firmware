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

typedef void (*PIN_UI_WAIT_CALLBACK)(uint32_t wait, uint32_t progress);

void storage_init(PIN_UI_WAIT_CALLBACK callback);
void storage_wipe(void);
secbool storage_check_pin(const uint32_t pin);
secbool storage_unlock(const uint32_t pin);
secbool storage_has_pin(void);
secbool storage_change_pin(const uint32_t oldpin, const uint32_t newpin);
secbool storage_get(const uint16_t key, const void **val, uint16_t *len);
secbool storage_set(const uint16_t key, const void *val, uint16_t len);

#endif
