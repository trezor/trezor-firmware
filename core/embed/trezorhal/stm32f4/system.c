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

#include <string.h>

#include "bootutils.h"
#include "mpu.h"
#include "systask.h"
#include "system.h"
#include "systick.h"
#include "systimer.h"

#if defined(TREZOR_MODEL_T) && (!defined(BOARDLOADER))
#include "startup_init.h"
#endif

#ifndef HardFault_IRQn
#define HardFault_IRQn (-13)  // not defined in stm32lib/cmsis/stm32429xx.h
#endif

#ifdef KERNEL_MODE

void system_init(systask_error_handler_t error_handler) {
#if defined(TREZOR_MODEL_T) && (!defined(BOARDLOADER))
  // Early boardloader versions on Model T initialized the CPU clock to 168MHz.
  // We need to set it to the STM32F429's maximum - 180MHz.
  set_core_clock(CLOCK_180_MHZ);
#endif
  mpu_init();
  mpu_reconfig(MPU_MODE_DEFAULT);
  systask_scheduler_init(error_handler);
  systick_init();
  systimer_init();
}

void system_exit(int exitcode) { systask_exit(NULL, exitcode); }

void system_exit_error_ex(const char* title, size_t title_len,
                          const char* message, size_t message_len,
                          const char* footer, size_t footer_len) {
  systask_exit_error(NULL, title, title_len, message, message_len, footer,
                     footer_len);
}

void system_exit_fatal_ex(const char* message, size_t message_len,
                          const char* file, size_t file_len, int line) {
  systask_exit_fatal(NULL, message, message_len, file, file_len, line);
}

__attribute__((used)) static void emergency_reset(void) {
  // TODO: reset peripherals (at least DMA, DMA2D)

  // Disable all NVIC interrupts and clear pending flags
  // so later the global interrupt can be re-enabled without
  // firing any pending interrupt
  for (int irqn = 0; irqn < 255; irqn++) {
    NVIC_DisableIRQ(irqn);
    NVIC_ClearPendingIRQ(irqn);
  }

  // Disable SysTick
  SysTick->CTRL = 0;

  // Clear PENDSV flag to prevent the PendSV_Handler call
  SCB->ICSR &= ~SCB_ICSR_PENDSVSET_Msk;

  // Clear SCB->SHCSR exception flags so we can return back
  // to thread mode without any exception active

  uint32_t preserved_flag = 0;

  switch ((__get_IPSR() & IPSR_ISR_Msk) - 16) {
    case MemoryManagement_IRQn:
      preserved_flag = SCB_SHCSR_MEMFAULTACT_Msk;
      break;
    case BusFault_IRQn:
      preserved_flag = SCB_SHCSR_BUSFAULTACT_Msk;
      break;
    case UsageFault_IRQn:
      preserved_flag = SCB_SHCSR_USGFAULTACT_Msk;
      break;
    case PendSV_IRQn:
      preserved_flag = SCB_SHCSR_PENDSVACT_Msk;
      break;
    case SysTick_IRQn:
      preserved_flag = SCB_SHCSR_SYSTICKACT_Msk;
      break;
    case SVCall_IRQn:
      preserved_flag = SCB_SHCSR_SVCALLACT_Msk;
      break;
    case HardFault_IRQn:
    default:
      break;
  }

  const uint32_t cleared_flags =
      SCB_SHCSR_MEMFAULTACT_Msk | SCB_SHCSR_BUSFAULTACT_Msk |
      SCB_SHCSR_USGFAULTACT_Msk | SCB_SHCSR_SVCALLACT_Msk |
      SCB_SHCSR_MONITORACT_Msk | SCB_SHCSR_PENDSVACT_Msk |
      SCB_SHCSR_SYSTICKACT_Msk;

  SCB->SHCSR &= ~(cleared_flags & ~preserved_flag);
}

__attribute((naked, no_stack_protector)) void system_emergency_rescue(
    systask_error_handler_t error_handler, const systask_postmortem_t* pminfo) {
  extern uint32_t __stack_chk_guard;

  __asm__ volatile(
      "MOV     R5, R1              \n"  // R5 = pminfo
      "MOV     R6, R0              \n"  // R6 = error_handler

      "CPSID   I                   \n"  // Disable interrupts

      // --------------------------------------------------------------
      // Disable MPU
      // --------------------------------------------------------------

      "DMB     0xF                 \n"  // Data memory barrier
      "LDR     R0, =0xE000ED94     \n"  // MPU->CTRL
      "MOV     R1, #0              \n"
      "STR     R1, [R0]            \n"  // Disable MPU

      // --------------------------------------------------------------
      // Setup new stack
      // --------------------------------------------------------------

      "LDR     R0, =_estack        \n"  // Setup new stack
      "MSR     MSP, R0             \n"  // Set MSP
#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__)
      "LDR     R0, =_sstack        \n"
      "ADD     R0, R0, #256        \n"  // Add safety margin
      "MSR     MSPLIM, R0          \n"  // Set MSPLIM
#endif

      // --------------------------------------------------------------
      // Copy pminfo to new stack
      // --------------------------------------------------------------

      "LDR     R2, =%[PMINFO_SIZE] \n"  // Copy pminfo to new stack
      "SUB     SP, R2              \n"  // Allocate space for pminfo
      "MOV     R0, SP              \n"  // Destination
      "MOV     R1, R5              \n"  // Source
      "MOV     R5, R0              \n"  // R5 = pminfo on the new stack
      "BL      memcpy              \n"

      // --------------------------------------------------------------
      // Save stack protector guard
      // --------------------------------------------------------------

      "LDR     R0, =%[STK_GUARD]   \n"  // Save stack protector guard
      "LDR     R7, [R0]            \n"  // R7 = __stack_chk_guard

      // --------------------------------------------------------------
      // Clear .bss, initialize .data, ...
      // --------------------------------------------------------------

      "LDR     R0, =bss_start      \n"  // Clear .bss
      "MOV     R1, #0              \n"
      "LDR     R2, =bss_end        \n"
      "SUB     R2, R2, R0          \n"
      "BL      memset              \n"

      "LDR     R0, =data_vma       \n"  // Initialize .data
      "LDR     R1, =data_lma       \n"
      "LDR     R2, =data_size      \n"
      "BL      memcpy              \n"

#ifdef STM32U5
      "LDR     R0, =confidential_vma   \n"  // Initialize .confidental
      "LDR     R1, =confidential_lma   \n"
      "LDR     R2, =confidential_size  \n"
      "BL      memcpy                  \n"
#endif

      // --------------------------------------------------------------
      // Restore stack protector guard
      // --------------------------------------------------------------

      "LDR     R0, =%[STK_GUARD]   \n"  // Restore stack protector guard
      "STR     R7, [R0]            \n"

      // --------------------------------------------------------------
      // Reset critical hardware so we can safely enable interrupts
      // --------------------------------------------------------------

      "BL      emergency_reset     \n"

      "CPSIE   I                   \n"  // Re-enable interrupts

      // --------------------------------------------------------------
      // Clear all VFP registers
      // --------------------------------------------------------------

      "LDR     R1, = 0xE000EF34    \n"  // FPU->FPCCR
      "LDR     R0, [R1]            \n"
      "BIC     R0, R0, #1          \n"  // Clear LSPACT to suppress lazy
                                        // stacking
      "STR     R0, [R1]            \n"

      // TODO: clear VFP registers (maybe for ARMV7-M only)

      // --------------------------------------------------------------
      // Clear R7-R11 registers
      // --------------------------------------------------------------

      "MOV     R0, #0              \n"
      "MOV     R7, R0              \n"
      "MOV     R8, R0              \n"
      "MOV     R9, R0              \n"
      "MOV     R10, R0             \n"
      "MOV     R11, R0             \n"

      // --------------------------------------------------------------
      // Check if we are in thread mode and if yes, jump to error_handler
      // --------------------------------------------------------------

      "LDR      R1, =0x1FF         \n"  // Get lower 9 bits of IPSR
      "MRS      R0, IPSR           \n"
      "ANDS     R0, R0, R1         \n"
      "CMP      R0, #0             \n"  // == 0 if in thread mode
      "ITTT     EQ                 \n"
      "MOVEQ    R0, R5             \n"  // R0 = pminfo
      "LDREQ    LR, =secure_shutdown\n"
      "BXEQ     R6                 \n"  // jump to error_handler directly

      // --------------------------------------------------------------
      // Return from exception to thread mode
      // --------------------------------------------------------------

      "MOV     R0, SP              \n"  // Align stack pointer to 8 bytes
      "AND     R0, R0, #~7         \n"
      "MOV     SP, R0              \n"
      "SUB     SP, SP, #32         \n"  // Allocate space for the stack frame

      "MOV     R0, #0              \n"
      "STR     R5, [SP, #0]        \n"  // future R0 = pminfo
      "STR     R0, [SP, #4]        \n"  // future R1 = 0
      "STR     R0, [SP, #8]        \n"  // future R2 = 0
      "STR     R0, [SP, #12]       \n"  // future R3 = 0
      "STR     R0, [SP, #16]       \n"  // future R12 = 0
      "LDR     R1, =secure_shutdown\n"
      "STR     R0, [SP, #20]       \n"  // future LR = secure_shutdown()
      "BIC     R6, R6, #1          \n"
      "STR     R6, [SP, #24]       \n"  // return address = error_handler()
      "LDR     R1, = 0x01000000    \n"  // THUMB bit set
      "STR     R1, [SP, #28]       \n"  // future xPSR

      "MOV     R4, R0              \n"  // Clear registers R4-R6
      "MOV     R5, R0              \n"  // (R7-R11 are already cleared)
      "MOV     R6, R0              \n"

      "MRS     R0, CONTROL         \n"  // Clear SPSEL to use MSP for thread
      "BIC     R0, R0, #3          \n"  // Clear nPRIV to run in privileged mode
      "MSR     CONTROL, R1         \n"

      "LDR     LR, = 0xFFFFFFF9    \n"  // Return to Secure Thread mode, use MSP
      "BX      LR                  \n"
      :  // no output
      : [PMINFO_SIZE] "i"(sizeof(systask_postmortem_t)),
        [STK_GUARD] "i"(&__stack_chk_guard)
      :  // no clobber
  );
}

#endif  // KERNEL_MODE

#ifdef STM32U5
const char* system_fault_message(const system_fault_t* fault) {
  switch (fault->irqn) {
    case HardFault_IRQn:
      return "(HF)";
    case MemoryManagement_IRQn:
      return "(MM)";
    case BusFault_IRQn:
      return "(BF)";
    case UsageFault_IRQn:
      return (fault->cfsr & SCB_CFSR_STKOF_Msk) ? "(SO)" : "(UF)";
    case SecureFault_IRQn:
      return "(SF)";
    case GTZC_IRQn:
      return "(IA)";
    case NonMaskableInt_IRQn:
      return "(CS)";
    default:
      return "(FAULT)";
  }
}
#else   // STM32U5
const char* system_fault_message(const system_fault_t* fault) {
  switch (fault->irqn) {
    case HardFault_IRQn:
      return "(HF)";
    case MemoryManagement_IRQn:
      return (fault->sp < fault->sp_lim) ? "(SO)" : "(MM)";
    case BusFault_IRQn:
      return "(BF)";
    case UsageFault_IRQn:
      return "(UF)";
    case NonMaskableInt_IRQn:
      return "(CS)";
    default:
      return "(FAULT)";
  }
}
#endif  // STM32U5

void system_exit_error(const char* title, const char* message,
                       const char* footer) {
  size_t title_len = title != NULL ? strlen(title) : 0;
  size_t message_len = message != NULL ? strlen(message) : 0;
  size_t footer_len = footer != NULL ? strlen(footer) : 0;
  system_exit_error_ex(title, title_len, message, message_len, footer,
                       footer_len);
}

void system_exit_fatal(const char* message, const char* file, int line) {
  size_t message_len = message != NULL ? strlen(message) : 0;
  size_t file_len = file != NULL ? strlen(file) : 0;
  system_exit_fatal_ex(message, message_len, file, file_len, line);
}
