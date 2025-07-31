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

#include <sec/entropy.h>
#include <sec/storage.h>

#include "memzero.h"

void storage_setup(PIN_UI_WAIT_CALLBACK callback) {
  entropy_data_t entropy;
  entropy_get(&entropy);
  storage_init(callback, entropy.bytes, entropy.size);
  memzero(&entropy, sizeof(entropy));
}

#endif  // SECURE_MODE
