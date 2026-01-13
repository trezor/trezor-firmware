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

#ifdef KERNEL

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <rtl/sizedefs.h>
#include <sec/rng.h>
#include <sys/applet.h>
#include <sys/coreapp.h>
#include <sys/mpu.h>
#include <sys/systask.h>

static mpu_area_t coreapp_code_area;
static mpu_area_t coreapp_tls_area;

// defined in linker script
extern uint32_t _kernel_flash_end;
#define KERNEL_END ALIGN_UP((uint32_t) & _kernel_flash_end, COREAPP_ALIGNMENT)

// Initializes coreapp applet
void coreapp_init(applet_t* applet) {
  const uint32_t CODE1_START = KERNEL_END;

#ifdef FIRMWARE_P1_START
  const uint32_t CODE1_END = FIRMWARE_P1_START + FIRMWARE_P1_MAXSIZE;
#else
  const uint32_t CODE1_END = FIRMWARE_START + FIRMWARE_MAXSIZE;
#endif

  const applet_layout_t coreapp_layout = {
      .data1.start = (uint32_t)AUX1_RAM_START,
      .data1.size = (uint32_t)AUX1_RAM_SIZE,
#ifdef AUX2_RAM_START
      .data2.start = (uint32_t)AUX2_RAM_START,
      .data2.size = (uint32_t)AUX2_RAM_SIZE,
#endif
      .code1.start = CODE1_START,
      .code1.size = CODE1_END - CODE1_START,
#ifdef FIRMWARE_P2_START
      .code2.start = FIRMWARE_P2_START,
      .code2.size = FIRMWARE_P2_MAXSIZE,
#endif
  };

  applet_privileges_t coreapp_privileges = {
      .assets_area_access = true,
  };

  applet_init(applet, &coreapp_layout, &coreapp_privileges);
}

static void coreapp_clear_memory(applet_t* applet) {
  if (applet->layout.data1.size > 0) {
    memset((void*)applet->layout.data1.start, 0, applet->layout.data1.size);
  }
  if (applet->layout.data2.size > 0) {
    memset((void*)applet->layout.data2.start, 0, applet->layout.data2.size);
  }
}

bool coreapp_reset(applet_t* applet, uint32_t cmd, const void* arg,
                   size_t arg_size) {
  // Enable access to coreapp memory regions
  mpu_set_active_applet(&applet->layout);

  // Clear all memory the applet is allowed to use
  coreapp_clear_memory(applet);

  const coreapp_header_t* header =
      (coreapp_header_t*)applet->layout.code1.start;

  // Remember code and TLS areas
  // (we will need then later for extension applets)
  coreapp_tls_area = header->tls;
  coreapp_code_area = applet->layout.code1;

  // Reset the applet task (stack pointer, etc.)
  if (!systask_init(&applet->task, header->stack.start, header->stack.size, 0,
                    applet)) {
    return false;
  }

  systask_enable_tls(&applet->task, header->tls);

  // Copy the arguments onto the applet stack
  void* arg_copy = NULL;
  if (arg != NULL && arg_size > 0) {
    arg_copy = systask_push_data(&applet->task, arg, arg_size);
    if (arg_copy == NULL) {
      return false;
    }
  }

  // Schedule the applet task run
  uint32_t arg1 = cmd;
  uint32_t arg2 = (uint32_t)arg_copy;
  uint32_t arg3 = rng_get();

  return systask_push_call(&applet->task, header->startup, arg1, arg2, arg3);
}

mpu_area_t coreapp_get_code_area(void) { return coreapp_code_area; }

mpu_area_t coreapp_get_tls_area(void) { return coreapp_tls_area; }

#endif  // KERNEL
