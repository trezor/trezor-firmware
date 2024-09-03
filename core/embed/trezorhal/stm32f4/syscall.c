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

#include "syscall.h"
#include "mpu.h"

#ifdef SYSCALL_DISPATCH

__attribute__((naked, no_stack_protector)) static uint32_t _invoke_app_callback(
    uint32_t args1, uint32_t arg2, uint32_t arg3, void* callback) {
  __asm__ volatile(
      "push {r1-r12, lr}      \n"

      "mrs r12, PSP           \n"  // reserved frame on unprivileged stack  (!@#
                                   // TODO check PSP value???)
      "push {r12}             \n"
      "sub r12, r12, #32      \n"
      "msr PSP, r12           \n"

      "str r0, [r12, #0]      \n"  // pass r0
      "str r1, [r12, #4]      \n"  // pass r1
      "str r2, [r12, #8]      \n"  // pass r2

      "mov r1, #0             \n"

      "mov r4, r1             \n"  // Clear registers r4-r11
      "mov r5, r1             \n"
      "mov r6, r1             \n"
      "mov r7, r1             \n"
      "mov r8, r1             \n"
      "mov r9, r1             \n"
      "mov r10, r1            \n"
      "mov r11, r1            \n"

      "str r1, [r12, #12]     \n"  // clear r3
      "str r1, [r12, #16]     \n"  // clear r12
      "str r1, [r12, #20]     \n"  // clear lr

      "bic r3, r3, #1         \n"
      "str r3, [r12, #24]     \n"  // return address

      "ldr r1, = 0x01000000   \n"
      "str r1, [r12, #28]     \n"  // xPSR

      "ldr r1, = 0xE000EF34   \n"  // FPU->FPPCCR
      "ldr r0, [r1]           \n"
      "bic r0, r0, #1         \n"  // Clear LSPACT to suppress lazy stacking to
      "str r0, [r1]           \n"  // avoid potential PSP stack overwrite.

      "mrs r1, CONTROL        \n"
      "bic r1, r1, #4         \n"  // Clear FPCA to suppress lazy stacking to
      "msr CONTROL, r1        \n"  // avoid potential PSP stack overwrite.

      // return to Secure Thread mode (use Secure PSP)
      "ldr lr, = 0xFFFFFFFD   \n"
      "bx lr                  \n");
}

uint32_t invoke_app_callback(uint32_t args1, uint32_t arg2, uint32_t arg3,
                             void* callback) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_APP);
  uint32_t retval = _invoke_app_callback(args1, arg2, arg3, callback);
  mpu_reconfig(mpu_mode);
  return retval;
}

__attribute__((naked, no_stack_protector)) void return_from_app_callback(
    uint32_t retval, uint32_t* msp) {
  __asm__ volatile(
      "MSR    MSP, R1         \n"
      "POP    {R1}            \n"
      "MSR    PSP, R1         \n"
      "POP    {R1-R12, LR}    \n"
      "BX     LR              \n");
}

#endif  // SYSCALL_DISPATCH
