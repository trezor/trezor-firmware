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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sec/entropy.h>

static entropy_data_t g_entropy = {0};

void entropy_init(void) {
  entropy_data_t* ent = &g_entropy;
#ifdef SECRET_PRIVILEGED_MASTER_KEY_SLOT
  ent->size = 32;
#else
  ent->size = 32 + 12;  // Legacy
#endif
}

void entropy_get(entropy_data_t* entropy) { *entropy = g_entropy; }
