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

// This header provides the norcow configuration required by the storage
// module, which includes it by this exact name. It intentionally stays flat
// rather than under `inc/sec/` for that reason.
//
// Do not include this header or add dependencies to it unless required by
// storage.

#ifndef __NORCOW_CONFIG_H__
#define __NORCOW_CONFIG_H__

#include <trezor_model.h>
#include <trezor_types.h>

#include <sys/flash.h>

#define NORCOW_HEADER_LEN 0

// Norcow uses all the storage areas provided by the flash layout
#define NORCOW_SECTOR_COUNT STORAGE_AREAS_COUNT

/*
 * Current storage version.
 */
#define NORCOW_VERSION ((uint32_t)0x00000006)

#endif
