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

#ifndef TREZOR_EMULATOR
#error "emulator-only side-channel API"
#endif

// Emulator side-channel API of the startup module: how a run of the emulator
// ends and how a test harness sets it up. Not part of the module API that the
// firmware and the bootloader use.

#include <trezor_types.h>

// Process exit codes of the emulator. Every exit path maps to one of these
// so that a test harness can tell them apart. The boot command and its
// arguments are persisted to `trezor.bootargs` in the profile directory
// before the process ends.
typedef enum {
  // The command line was rejected; nothing ran and no file is written.
  BOOTUTILS_EMU_EXIT_USAGE = 1,
  // Closed by the user (window closed, ESC) or by a signal; the boot
  // arguments are not persisted.
  BOOTUTILS_EMU_EXIT_QUIT = 2,
  // Rebooted by one of the `reboot_*` calls; the persisted boot command
  // tells which one.
  BOOTUTILS_EMU_EXIT_REBOOT = 3,
  // Jumped to the next boot stage (bootloader to firmware).
  BOOTUTILS_EMU_EXIT_JUMP = 10,
  // Powered off.
  BOOTUTILS_EMU_EXIT_POWER_OFF = 11,
  // Halted after showing the RSOD.
  BOOTUTILS_EMU_EXIT_HALT = 12,
} bootutils_emu_exit_code_t;

// Writes the boot command and arguments to `trezor.bootargs` in the
// profile directory and terminates the emulator process with the given
// exit code.
void __attribute__((noreturn)) bootutils_emu_exit(
    bootutils_emu_exit_code_t code);

// Sets the boot command and arguments from a file in the format written
// by `bootutils_emu_exit()`. Returns false if the file cannot be read.
bool bootargs_emu_load_file(const char *path);
