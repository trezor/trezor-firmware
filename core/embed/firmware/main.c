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

#include "py/builtin.h"
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
#include "memzero.h"
#include "model.h"
#include "mpu.h"
#include "random_delays.h"

#include TREZOR_BOARD

#ifdef USE_RGB_LED
#include "rgb_led.h"
#endif
#ifdef USE_CONSUMPTION_MASK
#include "consumption_mask.h"
#endif
#ifdef USE_DMA2D
#include "dma2d.h"
#endif
#ifdef USE_BUTTON
#include "button.h"
#endif
#ifdef USE_I2C
#include "i2c.h"
#endif
#ifdef USE_TOUCH
#include "touch.h"
#endif
#ifdef USE_SD_CARD
#include "sdcard.h"
#endif
#ifdef USE_OPTIGA
#include "optiga_commands.h"
#include "optiga_transport.h"
#include "secret.h"
#endif
#include "unit_variant.h"

#ifdef SYSTEM_VIEW
#include "systemview.h"
#endif
#include "platform.h"
#include "rng.h"
#include "supervise.h"
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

  display_reinit();

#if !defined TREZOR_MODEL_1
  parse_boardloader_capabilities();

  unit_variant_init();

#ifdef USE_OPTIGA
  uint8_t secret[SECRET_OPTIGA_KEY_LEN] = {0};
  secbool secret_ok =
      secret_read(secret, SECRET_OPTIGA_KEY_OFFSET, SECRET_OPTIGA_KEY_LEN);
#endif

#if PRODUCTION || BOOTLOADER_QA
  check_and_replace_bootloader();
#endif
  // Enable MPU
  mpu_config_firmware();
#endif

  // Init peripherals
  pendsv_init();

#ifdef USE_DMA2D
  dma2d_init();
#endif

#if !PRODUCTION
  // enable BUS fault and USAGE fault handlers
  SCB->SHCSR |= (SCB_SHCSR_USGFAULTENA_Msk | SCB_SHCSR_BUSFAULTENA_Msk);
#endif

#if defined TREZOR_MODEL_T
  set_core_clock(CLOCK_180_MHZ);
#endif

#ifdef USE_BUTTON
  button_init();
#endif

#ifdef USE_RGB_LED
  rgb_led_init();
#endif

#ifdef USE_CONSUMPTION_MASK
  consumption_mask_init();
#endif

#ifdef USE_I2C
  i2c_init();
#endif

#ifdef USE_TOUCH
  touch_init();
#endif

#ifdef USE_SD_CARD
  sdcard_init();
#endif

#ifdef USE_OPTIGA
  optiga_init();
  optiga_open_application();
  if (sectrue == secret_ok) {
    optiga_sec_chan_handshake(secret, sizeof(secret));
  }
  memzero(secret, sizeof(secret));
#endif

#if !defined TREZOR_MODEL_1
  drop_privileges();
#endif

#ifdef USE_SECP256K1_ZKP
  ensure(sectrue * (zkp_context_init() == 0), NULL);
#endif

  printf("CORE: Preparing stack\n");
  // Stack limit should be less than real stack size, so we have a chance
  // to recover from limit hit.
  mp_stack_set_top(&_estack);
  mp_stack_set_limit((char *)&_estack - (char *)&_sstack - 1024);

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
  mp_obj_list_append(mp_sys_path, MP_OBJ_NEW_QSTR(MP_QSTR__dot_frozen));

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
  error_shutdown("INTERNAL ERROR", "(UE)");
}

// interrupt handlers

void NMI_Handler(void) {
  // Clock Security System triggered NMI
  if ((RCC->CIR & RCC_CIR_CSSF) != 0) {
    error_shutdown("INTERNAL ERROR", "(CS)");
  }
}

void HardFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(HF)"); }

void MemManage_Handler_MM(void) { error_shutdown("INTERNAL ERROR", "(MM)"); }

void MemManage_Handler_SO(void) { error_shutdown("INTERNAL ERROR", "(SO)"); }

void BusFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(BF)"); }

void UsageFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(UF)"); }

// MicroPython builtin stubs

mp_import_stat_t mp_import_stat(const char *path) {
  return MP_IMPORT_STAT_NO_EXIST;
}

mp_obj_t mp_builtin_open(uint n_args, const mp_obj_t *args, mp_map_t *kwargs) {
  return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_KW(mp_builtin_open_obj, 1, mp_builtin_open);
