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

#ifndef TREZORHAL_SYSTEM_H
#define TREZORHAL_SYSTEM_H

#include <systask.h>

#ifdef KERNEL_MODE

// Initializes the fundamental system services
// (MPU, SysTick, systimer and task scheduler).
//
// `error_handler` is a callback that is called when a kernel task terminates
//                 with an error
void system_init(systask_error_handler_t error_handler);

// Calls the error handler in the emergency mode.
//
// This function is called when the system encounters a critical error
// and needs to perform a useful action (such as displaying an error message)
// before it is reset or shut down.
//
// The function may be called from any context, including interrupt context.
// It completely resets stack pointers, clears the .bss segment, reinitializes
// the .data segment, and calls the `error_handler` callback.
//
// The system will be in a state similar to a reset when `main()` is called
// (but with some hardware peripherals still initialized and running).
__attribute__((noreturn)) void system_emergency_rescue(
    systask_error_handler_t error_handler, const systask_postmortem_t* pminfo);

#endif  // KERNEL_MODE

// Terminates the current task normally with the given exit code.
//
// If the current task is the kernel task, the error handler is called with the
// postmortem information. If the task is not the kernel task, the task is
// terminated immediately and the kernel task is scheduled.
void system_exit(int exitcode);

// Terminates the current task with an error message.
//
// See the notes for `system_exit` regarding the behavior of the error handler
void system_exit_error(const char* title, const char* message,
                       const char* footer);

// Like `system_exit_error`, but with explicit lengths for the strings.
void system_exit_error_ex(const char* title, size_t title_len,
                          const char* message, size_t message_len,
                          const char* footer, size_t footer_len);

// Terminates the current task with a fatal error message.
//
// See the notes for `system_exit` regarding the behavior of the error handler
void system_exit_fatal(const char* message, const char* file, int line);

// Like `system_exit_fatal`, but with explicit lengths for the strings.
void system_exit_fatal_ex(const char* message, size_t message_len,
                          const char* file, size_t file_len, int line);

// Returns string representation of the system fault.
const char* system_fault_message(const system_fault_t* fault);

#endif  // TREZORHAL_SYSTEM_H
