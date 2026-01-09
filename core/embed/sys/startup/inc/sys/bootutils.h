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

#include <sys/systask.h>

#ifdef STM32F4
// Offset of the vector table in the bootloader image.
// This should match IMAGE_HEADER_SIZE in sec/image.h.
// Duplicated here to avoid circular dependency.
#define BOOTLOADER_VECTBL_OFFSET 0x400
#endif

// Wipe information structure
typedef struct {
  char title[64];
  char message[64];
  char footer[64];
} bootutils_wipe_info_t;

// Immediately resets the device and initiates the normal boot sequence as if
// the device was powered on
void __attribute__((noreturn)) reboot_device(void);

// Immediately resets the device
void __attribute__((noreturn)) reboot_to_off(void);

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

#ifdef USE_BOOTARGS_RSOD
// Resets the device with post-mortem information in bootargs
// so that the bootloader can display it.
void __attribute__((noreturn))
reboot_with_rsod(const systask_postmortem_t *pminfo);
#endif

// Resets the device and wipes all the user data.
// RSOD with wipe information is displayed.
void __attribute__((noreturn))
reboot_and_wipe(const bootutils_wipe_info_t *info);

// Allows the user to read the displayed error message and then
// reboots the device or waits for power-off.
//
// The function's behavior depends on the `RSOD_INFINITE_LOOP` macro:
// 1) If `RSOD_INFINITE_LOOP` is defined, the function enters an infinite loop.
// 2) If `RSOD_INFINITE_LOOP` is not defined, the function waits for a
//    specified duration and then resets the device.
void __attribute__((noreturn)) reboot_or_halt_after_rsod(void);

// Platform dependent alignment for vector table addresses
#define IMAGE_CODE_ALIGN(addr) \
  ((((uint32_t)(uintptr_t)addr) + (CODE_ALIGNMENT - 1)) & ~(CODE_ALIGNMENT - 1))

// Jumps to the next booting stage (e.g. bootloader to firmware).
// `vectbl_address` points to the flash at the vector table of the next stage.
//
// Before jumping, the function disables all interrupts and clears the
// memory and registers that could contain sensitive information.
void __attribute__((noreturn)) jump_to_next_stage(uint32_t vectbl_address);
