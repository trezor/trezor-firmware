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
// The function is intended to be used in special cases, like
// emergency situations, where the current stack may be corrupted.
__attribute((noreturn)) void call_with_new_stack(uint32_t arg1, uint32_t arg2,
                                                 new_stack_callback_t callback);

// Ensure that we are running in privileged thread mode.
//
// This function is used only on STM32F4, where a direct jump to the
// bootloader is performed. It checks if we are in handler mode, and
// if so, it switches to privileged thread mode.
void ensure_thread_mode(void);

// Clears USB peripheral fifo memory
void clear_otg_hs_memory(void);

#endif  // KERNEL_MODE
