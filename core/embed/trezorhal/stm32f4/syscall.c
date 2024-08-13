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

#include STM32_HAL_H

#include "syscall.h"
#include "image.h"
#include "irq.h"
#include "mpu.h"

#ifdef SYSCALL_DISPATCH

void syscall_init(void) {
  // SVCall priority should be the lowest since it is
  // generally a blocking operation
  NVIC_SetPriority(SVCall_IRQn, IRQ_PRI_LOWEST);
}

__attribute__((naked, no_stack_protector)) static uint32_t _invoke_app_callback(
    uint32_t args1, uint32_t arg2, uint32_t arg3, void *callback) {
  __asm__ volatile(
      "push {r1-r12, lr}      \n"

      "mrs r12, PSP           \n"  // reserved frame on unprivileged stack  (!@#
                                   // TODO check PSP value???)
      "push {r12}             \n"
      "sub r12, r12, #32      \n"
      "msr PSP, r12           \n"

      "str r0, [r12, #0]      \n"  // r0
      "str r1, [r12, #4]      \n"  // r1"
      "str r2, [r12, #8]      \n"  // r2"

      "mov r1, #0             \n"
      "str r1, [r12, #12]     \n"  // r3"
      "str r1, [r12, #16]     \n"  // r12"
      "str r1, [r12, #20]     \n"  // lr"

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
                             void *callback) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_APP);
  uint32_t retval = _invoke_app_callback(args1, arg2, arg3, callback);
  mpu_reconfig(mpu_mode);
  return retval;
}

// Jumps to reset vector of unprivileged application code
//
// Can be called only from an exception handler
__attribute__((naked, no_stack_protector)) static void start_app(
    uint32_t app_start) {
  __asm__ volatile(
      "ldr r12, [r0, #0]     \n"  // stack pointer
      "sub r12, r12, #32     \n"
      "msr PSP, r12          \n"

      "mov r1, #0             \n"
      "str r1, [r12, #0]      \n"  // r0
      "str r1, [r12, #4]      \n"  // r1"
      "str r1, [r12, #8]      \n"  // r2"
      "str r1, [r12, #12]     \n"  // r3"
      "str r1, [r12, #16]     \n"  // r12"
      "str r1, [r12, #20]     \n"  // lr"

      "ldr r1, [r0, #4]       \n"  // reset vector
      "bic r1, r1, #1         \n"
      "str r1, [r12, #24]     \n"  // return address

      "ldr r1, = 0x01000000   \n"
      "str r1, [r12, #28]     \n"  // xPSR

      "ldr r1, = 0xE000EF34   \n"  // FPU->FPPCCR
      "ldr r0, [r1]           \n"
      "bic r0, r0, #1         \n"  // Clear LSPACT to suppress lazy stacking to
      "str r0, [r1]           \n"  // avoid potential PSP stack overwrite.

      "mrs r1, CONTROL        \n"
      "bic r1, r1, #4         \n"  // Clear FPCA to suppress lazy stacking to
      "msr CONTROL, r1        \n"  // avoid potential PSP stack overwrite.

      "mrs r1, CONTROL        \n"  // Switch thread mode to unprivileged
      "orr r1, r1, #1         \n"  // by setting nPRIV bit in CONTROL register.
      "msr CONTROL, r1        \n"  // This applies after return from this
                                   // handler.

      // return to Secure Thread mode (use Secure PSP)
      "ldr lr, = 0xFFFFFFFD   \n"
      "bx lr                  \n");
}

void SVC_C_Handler(uint32_t *stack, uint32_t r4, uint32_t r5, uint32_t r6) {
  uint8_t svc_number = ((uint8_t *)stack[6])[-2];
  uint32_t args[6] = {stack[0], stack[1], stack[2], stack[3], r4, r5};

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  switch (svc_number) {
#ifdef SYSTEM_VIEW
    case SVC_GET_DWT_CYCCNT:
      cyccnt_cycles = *DWT_CYCCNT_ADDR;
      break;
#endif
    case SVC_START_APP:
      mpu_reconfig(MPU_MODE_APP);
      start_app(args[0]);
      break;
    case SVC_SYSCALL:
      syscall_handler(args, r6);
      stack[0] = args[0];
      stack[1] = args[1];
      break;
    default:
      stack[0] = 0xffffffff;
      stack[1] = 0xffffffff;
      break;
  }

  mpu_restore(mpu_mode);
}

__attribute__((naked, no_stack_protector)) void SVC_Handler(void) {
  __asm__ volatile(
      "       tst lr, #4      \n"  // Bit #3 tells which stack pointer should we
                                   // use
      "       ite eq          \n"  // Next 2 instructions are if-then-else
      "       mrseq r0, msp   \n"  // Make R0 point to main stack pointer
      "       mrsne r0, psp   \n"  // Make R0 point to process stack pointer

      "       ldr   r1, [r0, #24] \n"  // Load the PC of the SVC handler
      "       ldrb  r1, [r1, #-2] \n"  // Load the instruction at the PC
      "       cmp   r1, #2    \n"      // SVC_CALLBACK_RETURN
      "       beq   svc_callback_return \n"

      "       mov r1, r4      \n"  // pass R4 (arg5), R5 (arg6) and
      "       mov r2, r5      \n"  // R6 (sycall_number) as arguments
      "       mov r3, r6      \n"  // to SCV_C_Handler
      "       b SVC_C_Handler \n"  //

      "svc_callback_return: \n"

      "       ldr r0, [r0]           \n"
      "       pop {r1}               \n"
      "       msr PSP, r1            \n"
      "       pop {r1-r12, lr}       \n"
      "       bx lr                  \n");
}

void __attribute__((no_stack_protector, noreturn))
start_unprivileged_app(void) {
  //!@# TODO calculate better
  static const uint32_t app_start = COREAPP_START + IMAGE_HEADER_SIZE + 0x0400;

  mpu_reconfig(MPU_MODE_APP);

  register uint32_t ret __asm__("r0") = app_start;

  // SVC_START_APP is the only SVC that is allowed to be invoked from kernel
  // itself and it is used to start the unprivileged application code
  __asm__ volatile("svc %[svid]\n"
                   : "=r"(ret)
                   : [svid] "i"(SVC_START_APP), "r"(ret)
                   : "memory");

  // We never get here, just to supress compiler warning
  while (1) {
  }
}

#endif  // SYSCALL_DISPATCH
