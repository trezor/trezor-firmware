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

#ifndef LIB_TRANSLATIONS_H
#define LIB_TRANSLATIONS_H

#include <trezor_types.h>

bool translations_write(const uint8_t* data, uint32_t offset, uint32_t len);

const uint8_t* translations_read(uint32_t* len, uint32_t offset);

void translations_erase(void);

uint32_t translations_area_bytesize(void);

#endif  // LIB_TRANSLATIONS_H
