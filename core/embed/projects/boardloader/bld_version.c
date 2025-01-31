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

#include <sec/monoctr.h>

#include "bld_version.h"

uint8_t get_bootloader_min_version(void) {
  uint8_t version = 0;
  ensure(monoctr_read(MONOCTR_BOOTLOADER_VERSION, &version), "monoctr read");
  return version;
}

void write_bootloader_min_version(uint8_t version) {
  if (version > get_bootloader_min_version()) {
    ensure(monoctr_write(MONOCTR_BOOTLOADER_VERSION, version), "monoctr write");
  }
}
