/*
 * This file is part of the TREZOR project, https://trezor.io/
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
#define VERSION_MINOR 8
#define VERSION_PATCH 0

#define STR(X) #X
#define VERSTR(X) STR(X)

#define VERSION_MAJOR_CHAR "\x01"
#define VERSION_MINOR_CHAR "\x08"
#define VERSION_PATCH_CHAR "\x00"

#include <stdbool.h>
#include <stdint.h>

void show_halt(const char *line1, const char *line2);
void layoutFirmwareFingerprint(const uint8_t *hash);
bool get_button_response(void);

#endif
