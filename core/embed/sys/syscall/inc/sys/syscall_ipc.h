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

#ifdef KERNEL

#include <trezor_types.h>

#include <sys/syscall_numbers.h>

// Initializes IPC for syscalls
bool syscall_ipc_init(void);

// Enqueues a syscall for processing in the kernel event loop
//
// Queued syscalls are signalled to the kernel task by
// asserting SYSEVENT_SYSCALL.
//
// The function may be called only from kernel handler mode
// (respectively from SVCall handler).
void syscall_ipc_enqueue(uint32_t* args, syscall_number_t syscall);

// Dequeues and processed a syscall
//
// Removes the syscall from the queue and executes it. This
// function is intended to be called from the kernel event loop.
void syscall_ipc_dequeue(void);

#endif  // KERNEL
