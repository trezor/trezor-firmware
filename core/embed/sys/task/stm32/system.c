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
#include <trezor_rtl.h>

#include <sys/bootargs.h>
#include <sys/bootutils.h>
#include <sys/linker_utils.h>
#include <sys/mpu.h>
#include <sys/systask.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <sys/systimer.h>
#include <sys/sysutils.h>

#ifdef USE_SDRAM
#include <sys/sdram.h>
#endif

#if defined(TREZOR_MODEL_T2T1) && (!defined(BOARDLOADER))
#include "../stm32f4/startup_init.h"
#endif

#ifndef HardFault_IRQn
#define HardFault_IRQn (-13)  // not defined in stm32lib/cmsis/stm32429xx.h
#endif

#ifdef KERNEL_MODE

void system_init(systask_error_handler_t error_handler) {
#if defined(TREZOR_MODEL_T2T1) && (!defined(BOARDLOADER))
  // Early boardloader versions on Model T initialized the CPU clock to 168MHz.
  // We need to set it to the STM32F429's maximum - 180MHz.
  set_core_clock(CLOCK_180_MHZ);
#endif
#ifdef USE_SDRAM
  sdram_init();
#endif
  mpu_init();
  mpu_reconfig(MPU_MODE_DEFAULT);
  systask_scheduler_init(error_handler);
  systick_init();
  systimer_init();
}

void system_deinit(void) {
#ifdef FIXED_HW_DEINIT
  systick_deinit();
#endif
  mpu_reconfig(MPU_MODE_DISABLED);
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
  // Reset peripherals

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

__attribute((noreturn, no_stack_protector)) static void
system_emergency_rescue_phase_2(uint32_t arg1, uint32_t arg2) {
  systask_error_handler_t error_handler = (systask_error_handler_t)arg1;

  // Reset peripherals (so we are sure that no DMA is pending)
  emergency_reset();

  // Copy pminfo from to our stack
  // MPU is now disable, we have full access to bootargs.
  systask_postmortem_t pminfo = bootargs_ptr()->pminfo;

  // Clear unused part of our stack
  clear_unused_stack();

  // Save stack protector guard for later
  extern uint32_t __stack_chk_guard;
  uint32_t stack_chk_guard = __stack_chk_guard;

  // Clear all memory except our stack.
  // NOTE: This also clear bootargs, so we don't pass pminfo structure
  // to the bootloader for now.
  memregion_t region = MEMREGION_ALL_ACCESSIBLE_RAM;
  MEMREGION_DEL_SECTION(&region, _stack_section);
  memregion_fill(&region, 0);

  // Reinitialize .bss, .data, ...
  init_linker_sections();

  // Reinitialize stack protector guard
  __stack_chk_guard = stack_chk_guard;

  // Now we can safely enable interrupts again
  __enable_fault_irq();

  // Ensure we are in thread mode
  ensure_thread_mode();

  // Now everything is perfectly initialized and we can do anything
  // in C code

  if (error_handler != NULL) {
    error_handler(&pminfo);
  }

  // We reach this point only if error_handler is NULL or
  // if it returns. Neither is expected to happen.
  reboot_device();
}

__attribute((naked, noreturn, no_stack_protector)) void system_emergency_rescue(
    systask_error_handler_t error_handler, const systask_postmortem_t* pminfo) {
  // Save `pminfo` to bootargs so it isn't overwritten by succesive call
  bootargs_set(BOOT_COMMAND_SHOW_RSOD, pminfo, sizeof(*pminfo));

  call_with_new_stack((uint32_t)error_handler, 0,
                      system_emergency_rescue_phase_2);
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
