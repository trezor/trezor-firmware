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

#include <rtl/strutils.h>
#include <sys/bootargs.h>
#include <sys/bootutils.h>
#include <sys/linker_utils.h>
#include <sys/mpu.h>
#include <sys/stack_utils.h>
#include <sys/syscall_ipc.h>
#include <sys/systask.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <sys/systimer.h>
#include <sys/sysutils.h>

#ifdef USE_DBG_CONSOLE
#include <sys/dbg_console.h>
#endif

#ifdef USE_IPC
#include <sys/ipc.h>
#endif

#ifdef USE_SDRAM
#include <sys/sdram.h>
#endif

#ifdef USE_TRUSTZONE
#include <sys/trustzone.h>
#endif

#if defined(TREZOR_MODEL_T2T1) && (!defined(BOARDLOADER))
#include "../stm32f4/startup_init.h"
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
#ifdef USE_TRUSTZONE
  tz_init();
#endif
  mpu_init();
  mpu_reconfig(MPU_MODE_DEFAULT);
  systask_scheduler_init(error_handler);
  systick_init();
  systimer_init();
#ifdef KERNEL
#ifdef USE_IPC
  ipc_init();
#endif
  syscall_ipc_init();
#endif
#ifdef USE_DBG_CONSOLE
  dbg_console_init();
#endif
}

void system_deinit(void) {
#ifdef FIXED_HW_DEINIT
  systick_deinit();
#endif
  mpu_reconfig(MPU_MODE_DISABLED);
}

__attribute((noreturn, no_stack_protector)) static void
system_emergency_rescue_phase_2(uint32_t arg1, uint32_t arg2) {
  systask_error_handler_t error_handler = (systask_error_handler_t)arg1;

  // Reset peripherals (so we are sure that no DMA is pending)
  reset_peripherals_and_interrupts();

  // Althought MPU is disabled, we need to change MPU driver state
  mpu_reconfig(MPU_MODE_DISABLED);

  // Copy bootargs to our stack
  boot_args_t bootargs;
  bootargs_get_args(&bootargs);

  // Clear unused part of our stack
  clear_unused_stack();

  // Save stack protector guard for later
  extern uint32_t __stack_chk_guard;
  uint32_t stack_chk_guard = __stack_chk_guard;

  // Clear all memory except our stack.
  // NOTE: This also clear bootargs, if the model doesn't support
  // showing RSOD in the bootloader startup.
  memregion_t region = MEMREGION_ALL_RUNTIME_RAM;
  MEMREGION_DEL_SECTION(&region, _stack_section);
#ifdef USE_BOOTARGS_RSOD
  MEMREGION_DEL_SECTION(&region, _bootargs_ram);
#endif
  memregion_fill(&region, 0);

  // Reinitialize .bss, .data, ...
  init_linker_sections();

  // Reinitialize stack protector guard
  __stack_chk_guard = stack_chk_guard;

  // Now we can safely enable interrupts again
  __enable_fault_irq();
  // In case we crashed while irq_lock was active
  __enable_irq();

#ifndef SECMON
  // Ensure we are in thread mode.
  //
  // In the secure monitor, we are not able to ensure a transition to
  // thread mode under all circumstances. And because the error_handler is
  // always NULL in the secure monitor, it's not even necessary.
  ensure_thread_mode();
#endif

  // Now everything is perfectly initialized and we can do anything
  // in C code

  if (error_handler != NULL) {
    error_handler(&bootargs.pminfo);
    // We reach this point only if error_handler returns that's
    // not expected to happen. We clear the memory again and reboot.
    reboot_device();
  }

  // We reach this point only if error_handler is NULL
  // (if USE_BOOTARGS_RSOD is defined we leave postmortem info
  // in bootargs, so it can be used by the bootloader)
  NVIC_SystemReset();
}

__attribute((naked, noreturn, no_stack_protector)) void system_emergency_rescue(
    systask_error_handler_t error_handler, const systask_postmortem_t* pminfo) {
  // Save `pminfo` to bootargs so it isn't overwritten by succesive call
  bootargs_set(BOOT_COMMAND_SHOW_RSOD, pminfo, sizeof(*pminfo));

  call_with_new_stack((uint32_t)error_handler, 0, true,
                      system_emergency_rescue_phase_2);
}

#endif  // KERNEL_MODE

#ifdef STM32U5
const char* system_fault_message(const system_fault_t* fault) {
  const char* fault_type = "FAULT";
  switch (fault->irqn) {
    case HardFault_IRQn:
      fault_type = "HF";
      break;
    case MemoryManagement_IRQn:
      fault_type = "MM";
      break;
    case BusFault_IRQn:
      fault_type = "BF";
      break;
    case UsageFault_IRQn:
      fault_type = (fault->cfsr & SCB_CFSR_STKOF_Msk) ? "SO" : "UF";
      break;
    case SecureFault_IRQn:
      fault_type = "SF";
      break;
    case GTZC_IRQn:
      fault_type = "IA";
      break;
    case NonMaskableInt_IRQn:
      fault_type = "CS";
      break;
  }

  static char message[48] = "";
  cstr_append(message, sizeof(message), fault_type);
  cstr_append(message, sizeof(message), " @ 0x");
  cstr_append_uint32_hex(message, sizeof(message), fault->pc);

  return message;
}
#else   // STM32U5
const char* system_fault_message(const system_fault_t* fault) {
  const char* fault_type = "FAULT";
  switch (fault->irqn) {
    case HardFault_IRQn:
      fault_type = "HF";
      break;
    case MemoryManagement_IRQn:
      fault_type = (fault->sp < fault->sp_lim) ? "SO" : "MM";
      break;
    case BusFault_IRQn:
      fault_type = "BF";
      break;
    case UsageFault_IRQn:
      fault_type = "UF";
      break;
    case NonMaskableInt_IRQn:
      fault_type = "CS";
      break;
  }

  static char message[48] = "";
  cstr_append(message, sizeof(message), fault_type);
  cstr_append(message, sizeof(message), " @ 0x");
  cstr_append_uint32_hex(message, sizeof(message), fault->pc);

  return message;
}
#endif  // STM32U5
