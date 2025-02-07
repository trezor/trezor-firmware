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

#ifdef KERNEL_MODE

#include <trezor_types.h>

typedef void (*new_stack_callback_t)(uint32_t arg1, uint32_t arg2);

// Disables interrupts, disables the MPU, clears
// all registers, sets up a new stack and calls the given callback.
//
// If `clear_bkregs` is set, the function also clears the BKP registers
// and SRAM2 on STM32U5. It has no effect on STM32F4.
//
// The function is intended to be used in special cases, like
// emergency situations, where the current stack may be corrupted.
__attribute((noreturn)) void call_with_new_stack(uint32_t arg1, uint32_t arg2,
                                                 bool clear_bkpregs,
                                                 new_stack_callback_t callback);

// Ensure that we are running in privileged thread mode.
//
// This function is used only on STM32F4, where a direct jump to the
// bootloader is performed. It checks if we are in handler mode, and
// if so, it switches to privileged thread mode.
void ensure_thread_mode(void);

// Ensure compatible hardware settings before jumping to
// the different booting stage. This function is used to
// ensure backward compatibility with older versions of
// released bootloaders and firmware.
//
// Does nothing on almost all platforms.
void ensure_compatible_settings(void);

// Clears USB peripheral fifo memory
//
// Used to wipe sensitive data from USB peripheral memory.
void clear_otg_hs_memory(void);

// Resets critical peripherals, disables all interrupts, and clears
// pending interrupts in the NVIC controller.
//
// This function is used to stop pending DMA transfers and interrupts,
// ensuring it is safe to jump to the next stage or initiate rescue mode.
void reset_peripherals_and_interrupts(void);

// Jumps to the binary using its vector table.
//
// The target binary is called with interrupts disabled, and all registers
// are cleared except R11, which is set to the specified value.
__attribute((noreturn)) void jump_to_vectbl(uint32_t vectbl_addr, uint32_t r11);

#endif  // KERNEL_MODE
