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

#ifdef SECURE_MODE

#include <sec/storage.h>

#include "memzero.h"
#include "storage_salt.h"

void storage_setup(PIN_UI_WAIT_CALLBACK callback) {
  storage_salt_t salt;
  storage_salt_get(&salt);
  storage_init(callback, salt.bytes, salt.size);
  memzero(&salt, sizeof(salt));
}

#endif  // SECURE_MODE
