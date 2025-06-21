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

/**
 * @brief Verify the installed bootloader against expected hashes.
 *
 * Calculates the hash of the currently installed bootloader and compares
 * it against two known-good expected hashes.
 *
 * @param hash_00 Pointer to the expected hash for 0x00 padded image.
 * @param hash_FF Pointer to the expected hash for 0xFF padded image.
 * @param hash_len         Length of each hash, in bytes.
 *
 * @return `true` if the installed bootloader's hash does not match either
 *         of the expected hashes (indicating it should be replaced),
 *         `false` if it matches one of them.
 */
bool bl_check_check(const uint8_t *hash_00, const uint8_t *hash_FF,
                    size_t hash_len);

/**
 * @brief Replace the currently installed bootloader.
 *
 * Writes a new bootloader image into flash.
 *
 * @param data Pointer to the bootloader image data.
 * @param len  Size of the bootloader data in bytes.
 */
void bl_check_replace(const uint8_t *data, size_t len);
