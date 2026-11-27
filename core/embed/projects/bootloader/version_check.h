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

// Version the bootloader reports (Features, intro screen), packed as
// VERSION_UINT32. Under pq_secure_boot it is the installed RELEASE version,
// from the bootloader's own boot header -- the number install decisions use,
// and which a header-only update changes without touching the code. Falls
// back to the compiled VERSION_* when that header does not parse, and is the
// compiled version on the legacy scheme.
uint32_t bootloader_reported_version(void);

// Protection against bootloader downgrade

// Ensures bootloader version is stored in monotonic counter
// If the version cannot be written, the function will shutdown the device
void ensure_bootloader_min_version(void);

// Protection against firmware downgrade

// This functions checks if the firmware version is at least the minimum
// required version, returns sectrue if check_version is higher or equal to the
// stored version
secbool check_firmware_min_version(uint8_t check_version);

// Checks a version against the bootloader monotonic counter, returns sectrue
// if check_version is higher or equal to the stored version
secbool check_bootloader_min_version(uint8_t check_version);

// Ensures firmware version is stored in monotonic counter
// If the version cannot be written, the function will shutdown the device
void ensure_firmware_min_version(uint8_t version);

// This functions checks if the secmon version is at least the minimum
// required version, returns sectrue if check_version is higher or equal to the
// stored version
secbool check_secmon_min_version(uint8_t check_version);

// Ensures secmon version is stored in monotonic counter
// If the version cannot be written, the function will shutdown the device
void ensure_secmon_min_version(uint8_t version);
