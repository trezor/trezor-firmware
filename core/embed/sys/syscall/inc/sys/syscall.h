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

#include <sys/syscall_numbers.h>

// Reserved SVC numbers
#define SVC_SYSCALL 0
#define SVC_SYSTASK_YIELD 1

#ifdef KERNEL_MODE

// Handles all syscall requests.
//
// `args` points to an array of six 32-bit arguments.
// `syscall` is the syscall number, which is one of the `SYSCALL_XXX` constants.
//
// Input parameters are passed in `args[0]` to `args[5]`,
// and unused arguments may have undefined values.
//
// Return values must be copied to `args[0]` and
// `args[1]` (if returning a 64-bit value).
void syscall_handler(uint32_t* args, uint32_t syscall, void* applet);

#endif  // KERNEL_MODE

// Returns from the unprivileged callback invoked by the kernel
//
// Used for the storage callback and the unprivileged SAES hack callback.
// Do not use for other purposes unless there is a very good reason.
static inline void __attribute__((no_stack_protector))
return_from_unprivileged_callback(uint32_t retval) {
  register uint32_t r0 __asm__("r0") = retval;
  register uint32_t r6 __asm__("r6") = SYSCALL_RETURN_FROM_CALLBACK;

  __asm__ volatile("svc %[svid]\n"
                   : "=r"(r0)
                   : [svid] "i"(SVC_SYSCALL), "r"(r0), "r"(r6)
                   : "memory");
}
