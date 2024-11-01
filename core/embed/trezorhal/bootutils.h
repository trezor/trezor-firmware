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

#ifndef TREZORHAL_BOOTUTILS_H
#define TREZORHAL_BOOTUTILS_H

#include <trezor_types.h>

// Immediately resets the device and initiates the normal boot sequence.
void __attribute__((noreturn)) reboot_device(void);

// Resets the device and enters the bootloader,
// halting there and waiting for further user instructions.
void __attribute__((noreturn)) reboot_to_bootloader(void);

// Resets the device into the bootloader and automatically continues
// with the installation of new firmware (also known as an
// interaction-less upgrade).
//
// If the provided hash is NULL or invalid, the device will stop
// at the bootloader and will require user acknowledgment to proceed
// with the firmware installation.
void __attribute__((noreturn)) reboot_and_upgrade(const uint8_t hash[32]);

// Allows the user to see the displayed error message and then
// safely shuts down the device (clears secrets, memory, etc.).
//
// This function is called when the device enters an
// unrecoverable error state.
void __attribute__((noreturn)) secure_shutdown(void);

// Alternative memset with slightly different arguments
//
// This function writes a 32-bit value to a range of memory addresses.
// The range is defined by the start and stop pointers and must
// be aligned to 4 bytes.
void memset_reg(volatile void *start, volatile void *stop, uint32_t val);

// Jumps to the next booting stage (e.g. bootloader to firmware).
// `address` points to the flash at the vector table of the next stage.
//
// Before jumping, the function disables all interrupts and clears the
// memory and registers that could contain sensitive information.
void jump_to(uint32_t address);

// Ensure compatible hardware settings before jumping to
// the different booting stage. This function is used to
// ensure backward compatibility with older versions of
// released bootloaders and firmware.
//
// Does nothing on almost all platforms.
void ensure_compatible_settings(void);

#endif  // TREZORHAL_BOOTUTILS_H
