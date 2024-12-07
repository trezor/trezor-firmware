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

#ifndef LIB_FLASH_UTILS_H
#define LIB_FLASH_UTILS_H

#include <trezor_types.h>

#ifdef KERNEL_MODE

// Progress callback function called during the flash erase operation.
//
// Progress is reported as: (100 * pos) / total [%].
typedef void (*flash_progress_callback_t)(int pos, int total);

// Erases both storage areas
//
// Callback is invoked after each sector or page is erased.
secbool erase_storage(flash_progress_callback_t progress_cb);

// Erases all flash areas including storage, assets and firmware.
//
// If called from boardloader, also erases bootloader area.
//
// Callback is invoked after each sector or page is erased.
secbool erase_device(flash_progress_callback_t progress_cb);

#endif  // KERNEL_MODE

#endif  // LIB_FLASH_UTILS_H
