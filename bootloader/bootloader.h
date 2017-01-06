/*
 * This file is part of the TREZOR project.
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __BOOTLOADER_H__
#define __BOOTLOADER_H__

#define VERSION_MAJOR 1
#define VERSION_MINOR 3
#define VERSION_PATCH 1

#define STR(X) #X
#define VERSTR(X) STR(X)

#define VERSION_MAJOR_CHAR "\x01"
#define VERSION_MINOR_CHAR "\x03"
#define VERSION_PATCH_CHAR "\x01"

#include "memory.h"

void layoutFirmwareHash(uint8_t *hash);

#endif
