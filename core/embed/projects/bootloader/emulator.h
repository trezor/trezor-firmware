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

// The model's memory.h gives flash regions as absolute DEVICE addresses, which
// the boot chain then dereferences directly -- correct on the MCU, where flash
// is memory-mapped there. The emulator's flash is an mmap of `trezor.flash` at
// whatever address the kernel picked, so those constants point at nothing. Each
// one is replaced by a variable holding the mapped address of the same region,
// assigned in main() once flash_init() has run.
//
// Include this AFTER trezor_model.h so the #undef takes effect, and note the
// constants are gone in emulator builds: anything needing a compile-time value
// (a linker script, a static initializer) cannot use these.

#undef FIRMWARE_START
#undef BOOTLOADER_START

extern uintptr_t FIRMWARE_START;
extern uintptr_t BOOTLOADER_START;
