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

#ifndef TREZORHAL_FWUTILS_H
#define TREZORHAL_FWUTILS_H

#include <trezor_types.h>

// Callback function for firmware hash calculation.
typedef void (*firmware_hash_callback_t)(void* context, uint32_t progress,
                                         uint32_t total);

// Calculates hash of the firmware area.
//
// `challenge` is a optional pointer to the challenge data.
// `challenge_len` is the length of the challenge data (1..32).
// `hash` is a pointer to a buffer where the hash will be stored.
// `hash_len` is size of the buffer (must be at least 32).
// `callback` is an optional callback function that will be called during the
// hash calculation.
// `callback_context` is a pointer that will be passed to the callback function.
//
// Returns `sectrue` if the hash was calculated successfully, `secfalse`
// otherwise.
secbool firmware_calc_hash(const uint8_t* challenge, size_t challenge_len,
                           uint8_t* hash, size_t hash_len,
                           firmware_hash_callback_t callback,
                           void* callback_context);

// Reads the firmware vendor string from the header in the firmware area.
//
// `buff` is a pointer to a buffer where the vendor string will be stored.
// `buff_size` is the length of the buffer (reserve at least 64 bytes).
//
// Returns `sectrue` if the vendor string was read successfully, `secfalse`
// otherwise.
secbool firmware_get_vendor(char* buff, size_t buff_size);

#ifdef KERNEL_MODE

// Invalidates the firmware by erasing the first 1KB of the firmware area.
//
// Note: only works when write access to firmware area is enabled by MPU
void firmware_invalidate_header(void);

#endif  // KERNEL_MODE

#endif  // TREZORHAL_FWUTILS_H
