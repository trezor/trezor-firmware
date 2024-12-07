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

#ifndef TREZORHAL_SYSCALL_INTERNAL_H
#define TREZORHAL_SYSCALL_INTERNAL_H

#include <trezor_types.h>

#include <sys/applet.h>
#include <sys/syscall.h>

#include "syscall_numbers.h"

#ifndef KERNEL_MODE

static inline uint32_t __attribute__((no_stack_protector))
syscall_invoke0(uint32_t syscall) {
  register uint32_t ret __asm__("r0");
  register uint32_t r6 __asm__("r6") = syscall;

  __asm__ volatile("svc %[svid]\n"
                   : "=r"(ret)
                   : [svid] "i"(SVC_SYSCALL), "r"(r6)
                   : "memory");

  return ret;
}

static inline uint64_t __attribute__((no_stack_protector))
syscall_invoke0_ret64(uint32_t syscall) {
  register uint32_t ret_lo __asm__("r0");
  register uint32_t ret_hi __asm__("r1");
  register uint32_t r6 __asm__("r6") = syscall;

  __asm__ volatile("svc %[svid]\n"
                   : "=r"(ret_lo), "=r"(ret_hi)
                   : [svid] "i"(SVC_SYSCALL), "r"(r6)
                   : "memory");

  return ((uint64_t)ret_hi << 32) | ret_lo;
}

static inline uint32_t __attribute__((no_stack_protector))
syscall_invoke1(uint32_t arg1, uint32_t syscall) {
  register uint32_t ret __asm__("r0") = arg1;
  register uint32_t r6 __asm__("r6") = syscall;

  __asm__ volatile("svc %[svid]\n"
                   : "=r"(ret)
                   : [svid] "i"(SVC_SYSCALL), "r"(ret), "r"(r6)
                   : "memory");
  return ret;
}

static inline uint32_t __attribute__((no_stack_protector))
syscall_invoke2(uint32_t arg1, uint32_t arg2, uint32_t syscall) {
  register uint32_t ret __asm__("r0") = arg1;
  register uint32_t r1 __asm__("r1") = arg2;
  register uint32_t r6 __asm__("r6") = syscall;

  __asm__ volatile("svc %[svid]\n"
                   : "=r"(ret)
                   : [svid] "i"(SVC_SYSCALL), "r"(ret), "r"(r1), "r"(r6)
                   : "memory");

  return ret;
}

static inline uint64_t __attribute__((no_stack_protector))
syscall_invoke2_ret64(uint32_t arg1, uint32_t arg2, uint32_t syscall) {
  register uint32_t ret_lo __asm__("r0") = arg1;
  register uint32_t ret_hi __asm__("r1") = arg2;
  register uint32_t r6 __asm__("r6") = syscall;

  __asm__ volatile("svc %[svid]\n"
                   : "=r"(ret_lo), "=r"(ret_hi)
                   : [svid] "i"(SVC_SYSCALL), "r"(ret_lo), "r"(ret_hi), "r"(r6)
                   : "memory");

  return ((uint64_t)ret_hi << 32) | ret_lo;
}

static inline uint32_t __attribute__((no_stack_protector))
syscall_invoke3(uint32_t arg1, uint32_t arg2, uint32_t arg3, uint32_t syscall) {
  register uint32_t ret __asm__("r0") = arg1;
  register uint32_t r1 __asm__("r1") = arg2;
  register uint32_t r2 __asm__("r2") = arg3;
  register uint32_t r6 __asm__("r6") = syscall;

  __asm__ volatile("svc %[svid]\n"
                   : "=r"(ret)
                   : [svid] "i"(SVC_SYSCALL), "r"(ret), "r"(r1), "r"(r2),
                     "r"(r6)
                   : "memory");

  return ret;
}

static inline uint32_t __attribute__((no_stack_protector))
syscall_invoke4(uint32_t arg1, uint32_t arg2, uint32_t arg3, uint32_t arg4,
                uint32_t syscall) {
  register uint32_t ret __asm__("r0") = arg1;
  register uint32_t r1 __asm__("r1") = arg2;
  register uint32_t r2 __asm__("r2") = arg3;
  register uint32_t r3 __asm__("r3") = arg4;
  register uint32_t r6 __asm__("r6") = syscall;

  __asm__ volatile("svc %[svid]\n"
                   : "=r"(ret)
                   : [svid] "i"(SVC_SYSCALL), "r"(ret), "r"(r1), "r"(r2),
                     "r"(r3), "r"(r6)
                   : "memory");

  return ret;
}

static inline uint32_t __attribute__((no_stack_protector))
syscall_invoke5(uint32_t arg1, uint32_t arg2, uint32_t arg3, uint32_t arg4,
                uint32_t arg5, uint32_t syscall) {
  register uint32_t ret __asm__("r0") = arg1;
  register uint32_t r1 __asm__("r1") = arg2;
  register uint32_t r2 __asm__("r2") = arg3;
  register uint32_t r3 __asm__("r3") = arg4;
  register uint32_t r4 __asm__("r4") = arg5;
  register uint32_t r6 __asm__("r6") = syscall;

  __asm__ volatile("svc %[svid]\n"
                   : "=r"(ret)
                   : [svid] "i"(SVC_SYSCALL), "r"(ret), "r"(r1), "r"(r2),
                     "r"(r3), "r"(r4), "r"(r6)
                   : "memory");

  return ret;
}

static inline uint32_t __attribute__((no_stack_protector))
syscall_invoke6(uint32_t arg1, uint32_t arg2, uint32_t arg3, uint32_t arg4,
                uint32_t arg5, uint32_t arg6, uint32_t syscall) {
  register uint32_t ret __asm__("r0") = arg1;
  register uint32_t r1 __asm__("r1") = arg2;
  register uint32_t r2 __asm__("r2") = arg3;
  register uint32_t r3 __asm__("r3") = arg4;
  register uint32_t r4 __asm__("r4") = arg5;
  register uint32_t r5 __asm__("r5") = arg6;
  register uint32_t r6 __asm__("r6") = syscall;

  __asm__ volatile("svc %[svid]\n"
                   : "=r"(ret)
                   : [svid] "i"(SVC_SYSCALL), "r"(ret), "r"(r1), "r"(r2),
                     "r"(r3), "r"(r4), "r"(r5), "r"(r6)
                   : "memory");

  return ret;
}

#endif  // KERNEL_MODE

#endif  // TREZORHAL_SYSCALL_INTERNAL_H
