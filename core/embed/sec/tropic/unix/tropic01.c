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
#ifdef KERNEL_MODE

#include <trezor_rtl.h>

#include <memzero.h>
#include <sec/tropic.h>

bool tropic_hal_init(void) { return true; }

void tropic_hal_deinit(void) {}

void tropic_set_ui_progress(tropic_ui_progress_t ui_progress) {
  if (ui_progress != NULL) {
    ui_progress();
  }
}

void lt_secure_memzero(void *const ptr, const size_t count) {
  memzero(ptr, count);
}

#endif
