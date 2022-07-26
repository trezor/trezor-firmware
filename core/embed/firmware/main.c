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

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "py/compile.h"
#include "py/gc.h"
#include "py/mperrno.h"
#include "py/nlr.h"
#include "py/repl.h"
#include "py/runtime.h"
#include "py/stackctrl.h"
#include "shared/runtime/pyexec.h"

#include "ports/stm32/gccollect.h"
#include "ports/stm32/pendsv.h"

#include "bl_check.h"
#include "board_capabilities.h"
#include "common.h"
#include "compiler_traits.h"
#include "display.h"
#include "flash.h"
#include "image.h"
#include "mpu.h"
#include "random_delays.h"
#ifdef TREZOR_MODEL_R
#include "rgb_led.h"
#endif
#if defined TREZOR_MODEL_R || defined TREZOR_MODEL_1
#include "button.h"
#endif

#ifdef SYSTEM_VIEW
#include "systemview.h"
#endif
#include "rng.h"
#include "sdcard.h"
#include "supervise.h"
#include "touch.h"
#ifdef USE_SECP256K1_ZKP
#include "zkp_context.h"
#endif

// from util.s
extern void shutdown_privileged(void);

int main(void) {
  random_delays_init();

#ifdef RDI
  rdi_start();
#endif

  // reinitialize HAL for Trezor One
#if defined TREZOR_MODEL_1
  HAL_Init();
#endif

  collect_hw_entropy();

#ifdef SYSTEM_VIEW
  enable_systemview();
#endif

#if !defined TREZOR_MODEL_1
  parse_boardloader_capabilities();

#if PRODUCTION
  check_and_replace_bootloader();
#endif
  // Enable MPU
  mpu_config_firmware();
#endif

  // Init peripherals
  pendsv_init();

#if defined TREZOR_MODEL_1
  display_init();
  button_init();
#endif

#if defined TREZOR_MODEL_R
  button_init();
  display_clear();
  rgb_led_init();
#endif

#if defined TREZOR_MODEL_T
  touch_init();
  // display_init_seq();
  sdcard_init();
  display_clear();
#endif

#if !defined TREZOR_MODEL_1
  // jump to unprivileged mode
  // http://infocenter.arm.com/help/topic/com.arm.doc.dui0552a/CHDBIBGJ.html
  __asm__ volatile("msr control, %0" ::"r"(0x1));
  __asm__ volatile("isb");
#endif

#ifdef USE_SECP256K1_ZKP
  ensure(sectrue * (zkp_context_init() == 0), NULL);
#endif

  printf("CORE: Preparing stack\n");
  // Stack limit should be less than real stack size, so we have a chance
  // to recover from limit hit.
  mp_stack_set_top(&_estack);
  mp_stack_set_limit((char *)&_estack - (char *)&_heap_end - 1024);

#if MICROPY_ENABLE_PYSTACK
  static mp_obj_t pystack[1024];
  mp_pystack_init(pystack, &pystack[MP_ARRAY_SIZE(pystack)]);
#endif

  // GC init
  printf("CORE: Starting GC\n");
  gc_init(&_heap_start, &_heap_end);

  // Interpreter init
  printf("CORE: Starting interpreter\n");
  mp_init();
  mp_obj_list_init(mp_sys_argv, 0);
  mp_obj_list_init(mp_sys_path, 0);
  mp_obj_list_append(
      mp_sys_path,
      MP_OBJ_NEW_QSTR(MP_QSTR_));  // current dir (or base dir of the script)

  // Execute the main script
  printf("CORE: Executing main script\n");
  pyexec_frozen_module("main.py");

  // Clean up
  printf("CORE: Main script finished, cleaning up\n");
  mp_deinit();

  return 0;
}

// MicroPython default exception handler

void __attribute__((noreturn)) nlr_jump_fail(void *val) {
  error_shutdown("Internal error", "(UE)", NULL, NULL);
}

// interrupt handlers

void NMI_Handler(void) {
  // Clock Security System triggered NMI
  if ((RCC->CIR & RCC_CIR_CSSF) != 0) {
    error_shutdown("Internal error", "(CS)", NULL, NULL);
  }
}

void HardFault_Handler(void) {
  error_shutdown("Internal error", "(HF)", NULL, NULL);
}

void MemManage_Handler(void) {
  error_shutdown("Internal error", "(MM)", NULL, NULL);
}

void BusFault_Handler(void) {
  error_shutdown("Internal error", "(BF)", NULL, NULL);
}

void UsageFault_Handler(void) {
  error_shutdown("Internal error", "(UF)", NULL, NULL);
}

__attribute__((noreturn)) void reboot_to_bootloader() {
  jump_to_with_flag(BOOTLOADER_START + IMAGE_HEADER_SIZE,
                    STAY_IN_BOOTLOADER_FLAG);
  for (;;)
    ;
}

void SVC_C_Handler(uint32_t *stack) {
  uint8_t svc_number = ((uint8_t *)stack[6])[-2];
  switch (svc_number) {
    case SVC_ENABLE_IRQ:
      HAL_NVIC_EnableIRQ(stack[0]);
      break;
    case SVC_DISABLE_IRQ:
      HAL_NVIC_DisableIRQ(stack[0]);
      break;
    case SVC_SET_PRIORITY:
      NVIC_SetPriority(stack[0], stack[1]);
      break;
#ifdef SYSTEM_VIEW
    case SVC_GET_DWT_CYCCNT:
      cyccnt_cycles = *DWT_CYCCNT_ADDR;
      break;
#endif
    case SVC_SHUTDOWN:
      shutdown_privileged();
      for (;;)
        ;
      break;
    case SVC_REBOOT_TO_BOOTLOADER:
      mpu_config_bootloader();
      __asm__ volatile("msr control, %0" ::"r"(0x0));
      __asm__ volatile("isb");
      // See stack layout in
      // https://developer.arm.com/documentation/ka004005/latest We are changing
      // return address in PC to land into reboot to avoid any bug with ROP and
      // raising privileges.
      stack[6] = (uintptr_t)reboot_to_bootloader;
      return;
    default:
      stack[0] = 0xffffffff;
      break;
  }
}

__attribute__((naked)) void SVC_Handler(void) {
  __asm volatile(
      " tst lr, #4    \n"    // Test Bit 3 to see which stack pointer we should
                             // use.
      " ite eq        \n"    // Tell the assembler that the nest 2 instructions
                             // are if-then-else
      " mrseq r0, msp \n"    // Make R0 point to main stack pointer
      " mrsne r0, psp \n"    // Make R0 point to process stack pointer
      " b SVC_C_Handler \n"  // Off to C land
  );
}

// MicroPython builtin stubs

mp_import_stat_t mp_import_stat(const char *path) {
  return MP_IMPORT_STAT_NO_EXIST;
}

mp_obj_t mp_builtin_open(uint n_args, const mp_obj_t *args, mp_map_t *kwargs) {
  return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_KW(mp_builtin_open_obj, 1, mp_builtin_open);
