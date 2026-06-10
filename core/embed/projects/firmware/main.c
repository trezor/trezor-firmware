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

#include <trezor_model.h>
#include <trezor_rtl.h>

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

#include <io/display.h>
#include <io/notify.h>
#include <io/rsod.h>
#include <sec/boot_image.h>
#include <sys/linker_utils.h>
#include <sys/logging.h>
#include <sys/systask.h>
#include <sys/system.h>
#include "rust_ui_common.h"

#include <blake2s.h>

#include "sys/bootutils.h"

#ifdef USE_SECP256K1_ZKP
#include "zkp_context.h"
#endif

#ifdef USE_BLE
#include <io/ble.h>
#endif

#ifdef USE_NRF
#include <io/nrf.h>

extern const void nrf_app_start;
extern const void nrf_app_end;
extern const void nrf_app_size;

#endif

LOG_DECLARE(coreapp_main)

int main_func(uint32_t cmd, void *arg) {
  if (cmd == 1) {
    systask_postmortem_t *info = (systask_postmortem_t *)arg;
    rsod_gui(info);
    system_exit(0);
  }

  bool fading = DISPLAY_JUMP_BEHAVIOR == DISPLAY_RESET_CONTENT;

  bool update_required = false;

#if PRODUCTION || BOOTLOADER_QA
  // Check if the bootloader is valid and replace it if not
  bool bl_update_required = boot_image_check(boot_image_get_embdata());
  update_required = update_required || bl_update_required;
#endif

#ifdef USE_NRF
  bool nrf_update_required_ =
      nrf_update_required(&nrf_app_start, (size_t)&nrf_app_size);
  update_required = update_required || nrf_update_required_;
#endif

  if (update_required) {
    screen_update();
    fading = true;

#if PRODUCTION || BOOTLOADER_QA
    if (bl_update_required) {
      boot_image_replace(boot_image_get_embdata());
    }
#endif

#ifdef USE_NRF
    if (nrf_update_required_) {
      nrf_update(&nrf_app_start, (size_t)&nrf_app_size);
    }
#endif
  }

#if PRODUCTION || BOOTLOADER_QA
  if (bl_update_required) {
    reboot_device();
  }
#endif

#ifdef USE_NRF
#if PRODUCTION
  if (!nrf_authenticate()) {
    error_shutdown("Bluetooth authentication failed");
  }
#endif
#endif

  screen_boot_stage_2(fading);

  notify_send(NOTIFY_BOOT);

#ifdef USE_SECP256K1_ZKP
  ensure(sectrue * (zkp_context_init() == 0), NULL);
#endif

  LOG_INF("Preparing stack");
  // Stack limit should be less than real stack size, so we have a chance
  // to recover from limit hit.
  mp_stack_set_top(&_stack_section_end);
  mp_stack_set_limit((char *)&_stack_section_end -
                     (char *)&_stack_section_start - 1024);

#if MICROPY_ENABLE_PYSTACK
  static mp_obj_t pystack[1024];
  mp_pystack_init(pystack, &pystack[MP_ARRAY_SIZE(pystack)]);
#endif

  // GC init
  LOG_INF("Starting GC");
  gc_init(&_heap_start, &_heap_end);

  // Interpreter init
  LOG_INF("Starting interpreter");
  mp_init();
  mp_obj_list_init(mp_sys_argv, 0);
  mp_obj_list_init(mp_sys_path, 0);
  mp_obj_list_append(mp_sys_path, MP_OBJ_NEW_QSTR(MP_QSTR__dot_frozen));

  // Execute the main script
  LOG_INF("Executing main script");
  pyexec_frozen_module("main.py");

  // Clean up
  LOG_INF("Main script finished, cleaning up");
  mp_deinit();

  // Python code shouldn't ever exit, avoid black screen if it does
  error_shutdown("(PE)");

  return 0;
}

// MicroPython default exception handler

void __attribute__((noreturn)) nlr_jump_fail(void *val) {
  error_shutdown("(UE)");
}

// MicroPython builtin stubs

mp_import_stat_t mp_import_stat(const char *path) {
  return MP_IMPORT_STAT_NO_EXIST;
}

mp_obj_t mp_builtin_open(uint n_args, const mp_obj_t *args, mp_map_t *kwargs) {
  return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_KW(mp_builtin_open_obj, 1, mp_builtin_open);

// `reset_handler` is the application entry point (first routine called
// from kernel)
__attribute((no_stack_protector)) void reset_handler(uint32_t cmd, void *arg,
                                                     uint32_t random_value) {
  // Initialize linker script defined sections (.bss, .data, ...)
  init_linker_sections();

  // Initialize stack protector
  extern uint32_t __stack_chk_guard;
  __stack_chk_guard = random_value;

  // Now everything is perfectly initialized and we can do anything
  // in C code

  int main_result = main_func(cmd, arg);

  system_exit(main_result);
}
