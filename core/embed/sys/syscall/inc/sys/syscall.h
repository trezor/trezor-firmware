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

#ifndef TREZORHAL_SYSCALL_H

// Reserved SVC numbers
#define SVC_SYSCALL 0
#define SVC_SYSTASK_YIELD 1
#define SVC_CALLBACK_RETURN 2

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
void syscall_handler(uint32_t* args, uint32_t syscall);

// Invokes the application callback from the syscall handler.
//
// This is a *temporary* helper function used to invoke application callbacks
// from the syscall handler. It will be removed once all callback arguments
// are eliminated from syscalls.
uint32_t invoke_app_callback(uint32_t args1, uint32_t arg2, uint32_t arg3,
                             void* callback);

// Internal function for returning from an application callback.
// This function is called from an unprivileged app via an SVC call. It restores
// the stack pointer and returns control to the privileged caller.
void return_from_app_callback(uint32_t retval, uint32_t* msp);

// Invokes an unprivileged function from privileged mode.
//
// This is a *temporary* helper function used to control the STM32 SAES
// peripheral from unprivileged mode for backward compatibility (due to
// different hardware keys being used in privileged and unprivileged modes).
uint32_t invoke_unpriv(void* func);

#endif  // KERNEL_MODE

// Returns from an unprivileged callback.
//
// Same as `invoke_unpriv`, this function should be removed once
// we resolve the issue with `secure_aes`, which needs to jump to
// unprivileged mode.

static void inline __attribute__((no_stack_protector))
syscall_return_from_callback(uint32_t retval) {
  register uint32_t r0 __asm__("r0") = retval;
  __asm__ volatile("svc %[svid]\n"
                   :
                   : [svid] "i"(SVC_CALLBACK_RETURN), "r"(r0)
                   : "memory");
}

#endif  // TREZORHAL_SYSCALL_H
