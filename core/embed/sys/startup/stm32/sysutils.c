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

#ifdef TREZOR_MODEL_T2T1
#include "../stm32f4/startup_init.h"
#endif

__attribute((naked, noreturn, no_stack_protector)) void call_with_new_stack(
    uint32_t arg1, uint32_t arg2, bool clear_bkpregs,
    new_stack_callback_t callback) {
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
      "CMP     R2, #0              \n"  // clear_bkpregs?
      "BEQ     1f                  \n"
      // --------------------------------------------------------------
      // Delete all BKP registers and SRAM2 where stack is located.
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
      "1:                          \n"
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

      "MOV     R4, #0              \n"
      "MOV     R5, R4              \n"
      "MOV     R6, R4              \n"
      "MOV     R7, R4              \n"
      "MOV     R8, R4              \n"
      "MOV     R9, R4              \n"
      "MOV     R10, R4             \n"
      "MOV     R11, R4             \n"
      "MOV     R12, R4             \n"

      // --------------------------------------------------------------
      // Invoke phase 2 function
      // --------------------------------------------------------------

      // R0 = arg1
      // R1 = arg2

      "BX      R3                  \n"

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

void ensure_compatible_settings(void) {
#ifdef TREZOR_MODEL_T2T1
  // Early version of bootloader on T2T1 expects 168 MHz core clock.
  // So we need to set it here before handover to the bootloader.
  set_core_clock(CLOCK_168_MHZ);
#endif
}

__attribute((naked, noreturn, no_stack_protector)) void jump_to_vectbl(
    uint32_t vectbl_addr, uint32_t r11) {
  __asm__ volatile(
      "CPSID    F                  \n"

      "MOV      R11, R1            \n"
      "MOV      LR, R0             \n"

      "LDR      R0, =0             \n"
      "MOV      R1, R0             \n"
      "MOV      R2, R0             \n"
      "MOV      R3, R0             \n"
      "MOV      R4, R0             \n"
      "MOV      R5, R0             \n"
      "MOV      R6, R0             \n"
      "MOV      R7, R0             \n"
      "MOV      R8, R0             \n"
      "MOV      R9, R0             \n"
      "MOV      R10, R0            \n"  // R11 is set to r11 argument
      "MOV      R12, R0            \n"

      "LDR      R0, [LR]           \n"  // Initial MSP value
      "MSR      MSP, R0            \n"  // Set MSP

      "LDR      R0, =%[_SCB_VTOR]  \n"  // Reset handler
      "STR      LR, [R0]           \n"  // Set SCB->VTOR = vectb_addr

      "MOV      R0, R1             \n"  // Zero out R0

      "LDR      LR, [LR, #4]       \n"  // Reset handler
      "BX       LR                 \n"  // Go to reset handler

      :  // no output
      : [_SCB_VTOR] "i"(&SCB->VTOR)
      :  // no clobber
  );
}

void reset_peripherals_and_interrupts(void) {
#ifdef __HAL_RCC_DMA2D_FORCE_RESET
  __HAL_RCC_DMA2D_CLK_DISABLE();
  __HAL_RCC_DMA2D_FORCE_RESET();
  __HAL_RCC_DMA2D_RELEASE_RESET();
#endif

#ifdef __HAL_RCC_DSI_FORCE_RESET
  __HAL_RCC_DSI_CLK_DISABLE();
  __HAL_RCC_DSI_FORCE_RESET();
  __HAL_RCC_DSI_RELEASE_RESET();
#endif

#ifdef __HAL_RCC_GFXMMU_FORCE_RESET
  __HAL_RCC_GFXMMU_CLK_DISABLE();
  __HAL_RCC_GFXMMU_FORCE_RESET();
  __HAL_RCC_GFXMMU_RELEASE_RESET();
#endif

#ifdef __HAL_RCC_LTDC_FORCE_RESET
  __HAL_RCC_LTDC_CLK_DISABLE();
  __HAL_RCC_LTDC_FORCE_RESET();
  __HAL_RCC_LTDC_RELEASE_RESET();
#endif

#ifdef __HAL_RCC_GPDMA1_FORCE_RESET
  __HAL_RCC_GPDMA1_CLK_DISABLE();
  __HAL_RCC_GPDMA1_FORCE_RESET();
  __HAL_RCC_GPDMA1_RELEASE_RESET();
#endif

#ifdef __HAL_RCC_DMA1_FORCE_RESET
  __HAL_RCC_DMA1_CLK_DISABLE();
  __HAL_RCC_DMA1_FORCE_RESET();
  __HAL_RCC_DMA1_RELEASE_RESET();
#endif

#ifdef __HAL_RCC_DMA2_FORCE_RESET
  __HAL_RCC_DMA2_CLK_DISABLE();
  __HAL_RCC_DMA2_FORCE_RESET();
  __HAL_RCC_DMA2_RELEASE_RESET();
#endif

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

#endif  // KERNEL_MODE
