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

#ifndef TREZORHAL_BOOTARGS_H
#define TREZORHAL_BOOTARGS_H

#include <sys/systask.h>
#include <trezor_types.h>

// Defines boot command processed in bootloader on next reboot
typedef enum {
  // Normal boot sequence
  BOOT_COMMAND_NONE = 0x00000000,
  // Stop and wait for further instructions
  BOOT_COMMAND_STOP_AND_WAIT = 0x0FC35A96,
  // Do not ask anything, install an upgrade
  BOOT_COMMAND_INSTALL_UPGRADE = 0xFA4A5C8D,
  // Show RSOD and wait for user input
  BOOT_COMMAND_SHOW_RSOD = 0x7CD945A0,
} boot_command_t;

// Maximum size boot_args array
#define BOOT_ARGS_MAX_SIZE (256 - 8)

typedef union {
  uint8_t raw[BOOT_ARGS_MAX_SIZE];
  // firmware header hash, BOOT_COMMAND_INSTALL_UPGRADE
  uint8_t hash[32];
  // error information, BOOT_COMMAND_SHOW_RSOD
  systask_postmortem_t pminfo;
} boot_args_t;

_Static_assert(sizeof(boot_args_t) == BOOT_ARGS_MAX_SIZE,
               "boot_args_t structure is too long");

// Initialize bootargs module after bootloader startup
//
// r11_register is the value of the r11 register at bootloader entry.
// This value is used only on STM32F4 platform. On STM32U5, it is ignored.
void bootargs_init(uint32_t r11_register);

// Configures the boot command and associated arguments for the next reboot.
// The arguments must adhere to the boot_args_t structure layout.
void bootargs_set(boot_command_t command, const void* args, size_t args_size);

// Returns the last boot command saved during bootloader startup
boot_command_t bootargs_get_command();

// Copies the boot arguments to the destination buffer
void bootargs_get_args(boot_args_t* dest);

// Returns a pointer to the boot arguments structure.
//
// This function is intended to be used only in rescue mode, when the MPU
// is disabled and the caller has full access to the boot arguments area.
boot_args_t* bootargs_ptr(void);

#endif  // TREZORHAL_BOOTARGS_H
