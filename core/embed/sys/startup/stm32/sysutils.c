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

#include <trezor_bsp.h>

#include <sys/linker_utils.h>
#include <sys/sysutils.h>

#ifdef KERNEL_MODE

__attribute((naked, noreturn, no_stack_protector)) void call_with_new_stack(
    uint32_t arg1, uint32_t arg2, new_stack_callback_t callback) {
  __asm__ volatile(

      // R0, R1, R2 are used for arguments

      "CPSID   F                   \n"  // Disable interrupts/faults

      // --------------------------------------------------------------
      // Disable MPU
      // --------------------------------------------------------------

      "DMB     0xF                 \n"  // Data memory barrier
      "LDR     R4, =0xE000ED94     \n"  // MPU->CTRL
      "MOV     R5, #0              \n"
      "STR     R5, [R4]            \n"  // Disable MPU
  );

#ifdef STM32U5
  __asm__ volatile(
      // --------------------------------------------------------------
      // Delete all secrets and SRAM2 where stack is located.
      // SAES peripheral need to be disabled, so that we don't get
      // tamper events.
      // --------------------------------------------------------------

      // RCC->AHBENR1 &= ~RCC_AHBENR1_SAESEN;
      "LDR     R4, =%[_RCC_AHB2ENR1] \n"
      "LDR     R5, =%[_RCC_AHB2ENR1_SAESEN] \n"
      "LDR     R6, [R4]            \n"
      "BIC     R6, R6, R5          \n"
      "STR     R6, [R4]            \n"

      // TAMP->CR2 |= TAMP_CR2_BKERASE;
      "LDR     R4, =%[_TAMP_CR2]    \n"
      "LDR     R5, =%[_TAMP_CR2_BKERASE] \n"
      "LDR     R6, [R4]            \n"
      "ORR     R6, R6, R5          \n"
      "STR     R6, [R4]            \n"

      :  // no output
      : [_RCC_AHB2ENR1] "i"(&RCC->AHB2ENR1),
        [_RCC_AHB2ENR1_SAESEN] "i"(RCC_AHB2ENR1_SAESEN),
        [_TAMP_CR2] "i"(&TAMP->CR2),
        [_TAMP_CR2_BKERASE] "i"(TAMP_CR2_BKERASE)

      :  // no clobber
  );
#endif  // STM32U5

  __asm__ volatile(
      // --------------------------------------------------------------
      // Setup new stack
      // --------------------------------------------------------------

      "LDR     R4, =%[estack]      \n"  // Setup new stack
      "MSR     MSP, R4             \n"  // Set MSP
#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__)
      "LDR     R4, =%[sstack]      \n"
      "ADD     R4, R4, #256        \n"  // Add safety margin
      "MSR     MSPLIM, R4          \n"  // Set MSPLIM
#endif

      // --------------------------------------------------------------
      // Clear all VFP registers
      // --------------------------------------------------------------

      "LDR     R4, = 0xE000EF34    \n"  // FPU->FPCCR
      "LDR     R5, [R4]            \n"
      "BIC     R5, R5, #1          \n"  // Clear LSPACT to suppress lazy
                                        // stacking
      "STR     R5, [R4]            \n"

      // TODO: clear VFP registers (maybe for ARMV7-M only)

      // --------------------------------------------------------------
      // Clear all unused registers
      // --------------------------------------------------------------

      "MOV     R3, #0              \n"
      "MOV     R4, R3              \n"
      "MOV     R5, R3              \n"
      "MOV     R6, R3              \n"
      "MOV     R7, R3              \n"
      "MOV     R8, R3              \n"
      "MOV     R9, R3              \n"
      "MOV     R10, R3             \n"
      "MOV     R11, R3             \n"
      "MOV     R12, R3             \n"

      // --------------------------------------------------------------
      // Invoke phase 2 function
      // --------------------------------------------------------------

      // R0 = arg1
      // R1 = arg2

      "BX      R2                  \n"

      :  // no output
      : [estack] "i"(&_stack_section_end),
        [sstack] "i"(&_stack_section_start)
      :  // no clobber
  );
}

// Ensure that we are running in privileged thread mode.
//
// This function is used only on STM32F4, where a direct jump to the
// bootloader is performed. It checks if we are in handler mode, and
// if so, it switches to privileged thread mode.
__attribute((naked, no_stack_protector)) void ensure_thread_mode(void) {
  __asm__ volatile(
      // --------------------------------------------------------------
      // Check if we are in handler mode
      // --------------------------------------------------------------

      "LDR      R1, =0x1FF         \n"  // Get lower 9 bits of IPSR
      "MRS      R0, IPSR           \n"
      "ANDS     R0, R0, R1         \n"
      "CMP      R0, #0             \n"  // == 0 if in thread mode
      "IT       EQ                 \n"
      "BXEQ     LR                 \n"  // return if in thread mode

      // --------------------------------------------------------------
      // Disable FP registers lazy stacking
      // --------------------------------------------------------------

      "LDR     R1, = 0xE000EF34    \n"  // FPU->FPCCR
      "LDR     R0, [R1]            \n"
      "BIC     R0, R0, #1          \n"  // Clear LSPACT to suppress lazy
                                        // stacking
      "STR     R0, [R1]            \n"

      // --------------------------------------------------------------
      // Exit handler mode, enter thread mode
      // --------------------------------------------------------------

      "MOV     R0, SP              \n"  // Align stack pointer to 8 bytes
      "AND     R0, R0, #~7         \n"
      "MOV     SP, R0              \n"
      "SUB     SP, SP, #32         \n"  // Allocate space for the stack frame

      "MOV     R0, #0              \n"
      "STR     R0, [SP, #0]        \n"  // future R0 = 0
      "STR     R0, [SP, #4]        \n"  // future R1 = 0
      "STR     R0, [SP, #8]        \n"  // future R2 = 0
      "STR     R0, [SP, #12]       \n"  // future R3 = 0
      "STR     R12, [SP, #16]      \n"  // future R12 = R12
      "STR     LR, [SP, #20]       \n"  // future LR = LR
      "BIC     LR, LR, #1          \n"
      "STR     LR, [SP, #24]       \n"  // return address = LR
      "LDR     R0, = 0x01000000    \n"  // THUMB bit set
      "STR     R0, [SP, #28]       \n"  // future xPSR

      "MRS     R0, CONTROL         \n"  // Clear SPSEL to use MSP for thread
      "BIC     R0, R0, #3          \n"  // Clear nPRIV to run in privileged mode
      "MSR     CONTROL, R0         \n"

      "LDR     LR, = 0xFFFFFFF9    \n"  // Return to Secure Thread mode, use MSP
      "BX      LR                  \n");
}


// Clears USB FIFO memory to prevent data leakage of sensitive information
__attribute((used)) void clear_otg_hs_memory(void) {
#ifdef STM32F4

  // reference RM0090 section 35.12.1 Figure 413
  #define USB_OTG_HS_DATA_FIFO_RAM (USB_OTG_HS_PERIPH_BASE + 0x20000U)
  #define USB_OTG_HS_DATA_FIFO_SIZE (4096U)

  // use the HAL version due to section 2.1.6 of STM32F42xx Errata sheet
  __HAL_RCC_USB_OTG_HS_CLK_ENABLE();  // enable USB_OTG_HS peripheral clock so
                                      // that the peripheral memory is
                                      // accessible
  __IO uint32_t* usb_fifo_ram = (__IO uint32_t*)USB_OTG_HS_DATA_FIFO_RAM;

  for (uint32_t i = 0; i < USB_OTG_HS_DATA_FIFO_SIZE / 4; i++) {
    usb_fifo_ram[i] = 0;
  }

  __HAL_RCC_USB_OTG_HS_CLK_DISABLE();  // disable USB OTG_HS peripheral clock as
                                       // the peripheral is not needed right now
#endif
}


#endif  // KERNEL_MODE
