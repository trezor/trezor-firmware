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
 * @brief Check bootloader hash against the installed bootloader.
 *
 * Computes the hash of the provided bootloader image and compares it
 * with the hash of the currently installed bootloader.
 *
 * @return `true` if the hashes do not match (bootloader needs replacement),
 *         `false` otherwise.
 */
bool bl_check_check(void);

/**
 * @brief Replace the currently installed bootloader.
 *
 * Writes a new bootloader image into flash.
 *
 * @param data Pointer to the bootloader image data.
 * @param len  Size of the bootloader data in bytes.
 */
void bl_check_replace(const uint8_t* data, size_t len);
