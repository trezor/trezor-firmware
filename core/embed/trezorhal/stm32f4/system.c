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

#include "system.h"
#include "bootutils.h"
#include "mpu.h"
#include "systask.h"
#include "systick.h"
#include "systimer.h"

#ifdef KERNEL_MODE

void system_init(systask_error_handler_t error_handler) {
  mpu_init();
  mpu_reconfig(MPU_MODE_DEFAULT);
  systask_scheduler_init(error_handler);
  systick_init();
  systimer_init();
}

void system_exit(int exitcode) { systask_exit(NULL, exitcode); }

void system_exit_error(const char* title, const char* message,
                       const char* footer) {
  systask_exit_error(NULL, title, message, footer);
}

void system_exit_fatal(const char* message, const char* file, int line) {
  systask_exit_fatal(NULL, message, file, line);
}

#endif  // KERNEL_MODE

#ifndef HardFault_IRQn
#define HardFault_IRQn (-13)  // not defined in stm32lib/cmsis/stm32429xx.h
#endif

const char* system_fault_message(const system_fault_t* fault) {
  switch (fault->irqn) {
    case HardFault_IRQn:
      return "(HF)";

    case MemoryManagement_IRQn:
#if !(defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__))
      if (fault->sp < fault->sp_lim) {
        return "(SO)";
      } else {
        return "(MM)";
      }
#else
      return "(MM)";
#endif

    case BusFault_IRQn:
      return "(BF)";

    case UsageFault_IRQn:
#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__)
      if (fault->cfsr & SCB_CFSR_STKOF_Msk) {
        return "(SO)";
      } else {
        return "(UF)";
      }
#else
      return "(UF)";
#endif

#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__)
    case SecureFault_IRQn:
      return "(SF)";
#endif

#ifdef STM32U5
    case GTZC_IRQn:
      return "(IA)";
#endif

    case NonMaskableInt_IRQn:
      return "(CS)";
  }
  return "(FAULT)";
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
    case HardFault_IRQn:
      break;
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
      // Disable NVIC interrupts and clear pending flags
      // --------------------------------------------------------------

      "BL      emergency_reset     \n"  // Reset critical hardware components
                                        // so we can safely enter emergency mode

      "CPSIE   I                   \n"  // Re-enable interrupts

      // --------------------------------------------------------------
      // Check if we are in thread mode and if yes, jump to error_handler
      // --------------------------------------------------------------

      "LDR      R1, =0x1FF         \n"  // Get lower 9 bits of IPSR
      "MRS      R0, IPSR           \n"
      "ANDS     R0, R0, R1         \n"
      "CMP      R0, #0             \n"  // == 0 if in thread mode
      "ITTT     EQ                 \n"
      "MOVEQ    R0, R5             \n"  // R0 = pminfo
      "LDREQ    LR, =reboot        \n"
      "BXEQ     R6                 \n"  // jump to error_handler directly

      // --------------------------------------------------------------
      // Return from exception to thread mode
      // --------------------------------------------------------------

      "SUB     SP, SP, #32         \n"  // Allocate space for exception frame

      "MOV     R0, #0              \n"
      "STR     R5, [SP, #0]        \n"  // future R0 = pminfo
      "STR     R0, [SP, #4]        \n"  // future R1 = 0
      "STR     R0, [SP, #8]        \n"  // future R2 = 0
      "STR     R0, [SP, #12]       \n"  // future R3 = 0
      "STR     R0, [SP, #16]       \n"  // future R12 = 0
      "LDR     R1, =reboot         \n"
      "STR     R0, [SP, #20]       \n"  // future LR = reboot()
      "BIC     R6, R6, #1          \n"
      "STR     R6, [SP, #24]       \n"  // return address = error_handler()
      "LDR     R1, = 0x01000000    \n"  // THUMB bit set
      "STR     R1, [SP, #28]       \n"  // future xPSR

      "MOV     R4, R0              \n"  // Clear registers R4-R11
      "MOV     R5, R0              \n"
      "MOV     R6, R0              \n"
      "MOV     R7, R0              \n"
      "MOV     R8, R0              \n"
      "MOV     R9, R0              \n"
      "MOV     R10, R0             \n"
      "MOV     R11, R0             \n"

      "MRS     R0, CONTROL         \n"
      "BIC     R0, R0, #4          \n"  // Clear FPCA to suppress lazy stacking
                                        // to avoid potential stack overwrite.
      "BIC     R0, R0, #2          \n"  // Clear SPSEL to use MSP for thread
                                        // mode
      "BIC     R0, R0, #1          \n"  // Clear nPRIV to run in privileged mode
      "MSR     CONTROL, R1         \n"

      "LDR     R1, = 0xE000EF34    \n"  // FPU->FPPCCR
      "LDR     R0, [R1]            \n"
      "BIC     R0, R0, #1          \n"  // Clear LSPACT to suppress lazy
                                        // stacking to
      "STR     R0, [R1]            \n"  // avoid potential stack overwrite.

      "LDR     LR, = 0xFFFFFFF9    \n"  // Return to Secure Thread mode, use MSP
      "BX      LR                  \n"
      :  // no output
      : [PMINFO_SIZE] "i"(sizeof(systask_postmortem_t)),
        [STK_GUARD] "i"(&__stack_chk_guard)
      :  // no clobber
  );
}
