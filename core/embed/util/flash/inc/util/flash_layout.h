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

#ifndef TREZORHAL_LAYOUT_H_
#define TREZORHAL_LAYOUT_H_

#include "flash_area.h"

#define STORAGE_AREAS_COUNT (2)

extern const flash_area_t STORAGE_AREAS[STORAGE_AREAS_COUNT];
extern const flash_area_t BOARDLOADER_AREA;
extern const flash_area_t SECRET_AREA;
extern const flash_area_t BHK_AREA;
extern const flash_area_t ASSETS_AREA;
extern const flash_area_t BOOTLOADER_AREA;
extern const flash_area_t FIRMWARE_AREA;
extern const flash_area_t UNUSED_AREA;

#endif  // TREZORHAL_LAYOUT_H_
