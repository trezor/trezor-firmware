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

#include <trezor_types.h>

// (Re)starts calculation of the firmware hash
//
// `challenge` is a pointer to the challenge data (optional, can be NULL).
// `challenge_len` is the length of the challenge data (1..32).
//
// Return 0 on success, -1 on error.
int firmware_hash_start(const uint8_t* challenge, size_t challenge_len);

// Continues with the firmware hash calculation.
//
// `hash` is a pointer to a buffer where the hash will be stored.
// `hash_len` is size of the buffer (must be at least 32).
//
// Return value between 0 and 100 indicates the progress of the hash
// calculation. 100 means the hash was calculated successfully and
// `hash` contains the hash. -1 means an error occurred during the
int firmware_hash_continue(uint8_t* hash, size_t hash_len);

// Reads the firmware vendor string from the header in the firmware area.
//
// `buff` is a pointer to a buffer where the vendor string will be stored.
// `buff_size` is the length of the buffer (reserve at least 64 bytes).
//
// Returns `sectrue` if the vendor string was read successfully, `secfalse`
// otherwise.
secbool firmware_get_vendor(char* buff, size_t buff_size);

#ifdef SECURE_MODE

// Invalidates the firmware by erasing the first 1KB of the firmware area.
//
// Note: only works when write access to firmware area is enabled by MPU
void firmware_invalidate_header(void);

#endif  // SECURE_MODE
