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

#pragma once

#ifdef KERNEL_MODE

#include <trezor_types.h>

#include <trezor-storage/flash_area.h>
#include <trezor-storage/flash_ll.h>

#include "../norcow_config.h"

void flash_init(void);

void flash_deinit(void);

extern const flash_area_t BOARDLOADER_AREA;
extern const flash_area_t SECRET_AREA;
extern const flash_area_t BHK_AREA;
extern const flash_area_t ASSETS_AREA;
extern const flash_area_t BOOTLOADER_AREA;
extern const flash_area_t UNUSED_AREA;

#ifdef SECMON
extern flash_area_t FIRMWARE_AREA;
#else
extern const flash_area_t FIRMWARE_AREA;
#endif

#ifdef USE_BOOT_UCB
extern const flash_area_t BOOTUCB_AREA;
extern const flash_area_t BOOTUPDATE_AREA;
#ifdef BOARDLOADER
extern const flash_area_t NONBOARDLOADER_AREA;
#endif
#endif  // USE_BOOT_UCB

#endif  // KERNEL_MODE
