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

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sec/board_capabilities.h>

void parse_boardloader_capabilities() {}

uint32_t get_board_name() { return HW_MODEL; }

// Gets the boardloader version
void get_boardloader_version(boardloader_version_t* version) {
  boardloader_version_t v = {.version_major = 0,
                             .version_minor = 0,
                             .version_patch = 0,
                             .version_build = 0};
  *version = v;
}
