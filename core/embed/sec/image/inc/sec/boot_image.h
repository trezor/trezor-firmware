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
 * Structure representing a bootloader image and all its associated data.
 */
typedef struct {
  const void* image_ptr;
  size_t image_size;
#ifndef USE_BOOT_UCB
  uint8_t hash_00[32];
  uint8_t hash_FF[32];
#endif
} boot_image_t;

/**
 * @brief Get the new bootloader available as a part of the build.
 *
 * This function retrieves the bootloader image that is
 * included in the build. The image is expected to be padded
 * with 0x00 and 0xFF bytes to match the expected size.
 *
 * @return Pointer to a `boot_image_t` structure containing the
 *         image data, size, and expected hashes.
 */
const boot_image_t* boot_image_get_embdata(void);

/**
 * @brief Verify the installed bootloader against expected hashes.
 *
 * Calculates the hash of the currently installed bootloader and compares
 * it against two known-good expected hashes.
 *
 * @param image Pointer to the `boot_image_t` structure containing
 *              the expected hashes and other image data.
 *
 * @return `true` if the installed bootloader's hash does not match either
 *         of the expected hashes (indicating it should be replaced),
 *         `false` if it matches one of them.
 */
bool boot_image_check(const boot_image_t* image);

/**
 * @brief Replace the currently installed bootloader.
 *
 * Writes a new bootloader image into flash.
 *
 * @param image Pointer to the `boot_image_t` structure containing
 *              the new bootloader image data.
 */
void boot_image_replace(const boot_image_t* image);
