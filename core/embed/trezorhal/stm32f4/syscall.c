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
    uint32_t arg1, uint32_t arg2, uint32_t arg3, void* callback) {
  __asm__ volatile(
      "push {r1-r12, lr}      \n"

#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__)
      "mrs r12, PSPLIM        \n"  // Backup unprivileged stack limit
      "push {r12}             \n"
#endif
      "mrs r12, PSP           \n"  // Backup unprivileged stack pointer
      "push {r12}             \n"

      "sub r12, r12, #32      \n"  // Reserve space for stack frame
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

      "vmov r0, s0            \n"  // Use FPU instruction to ensure lazy
                                   // stacking

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
      "MSR    MSP, R1            \n"
      "POP    {R1}               \n"
      "MSR    PSP, R1            \n"
#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__)
      "POP    {R1}               \n"
      "MSR    PSPLIM, R1         \n"
#endif

      "LDR    R1, = 0xE000EF34   \n"  // FPU->FPCCR
      "LDR    R2, [R1]           \n"
      "BIC    R2, R2, #1         \n"  // Clear LSPACT to suppress repeated lazy
      "STR    R2, [R1]           \n"  // stacking that was already done

      "POP    {R1-R12, LR}    \n"
      "BX     LR              \n");
}

#endif  // SYSCALL_DISPATCH
