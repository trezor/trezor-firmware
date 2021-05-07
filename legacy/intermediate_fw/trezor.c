/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "trezor.h"
#include <libopencm3/stm32/desig.h>
#include <libopencm3/stm32/flash.h>
#include <vendor/libopencm3/include/libopencmsis/core_cm3.h>
#include "bitmaps.h"
#include "bl_check.h"
#include "layout.h"
#include "memory.h"
#include "memzero.h"
#include "oled.h"
#include "rng.h"
#include "setup.h"
#include "timer.h"
#include "util.h"

void __attribute__((noinline, noreturn, section(".data"))) reboot_device(void) {
  __disable_irq();
  SCB_AIRCR = SCB_AIRCR_VECTKEY | SCB_AIRCR_SYSRESETREQ;
  while (1)
    ;
}

int main(void) {
  setupApp();
  __stack_chk_guard = random32();  // this supports compiler provided
                                   // unpredictable stack protection checks
  oledInit();
  if (is_mode_unprivileged()) {
    layoutDialog(&bmp_icon_warning, NULL, NULL, NULL, "Cannot update", NULL,
                 NULL, "Unprivileged mode", "Unsigned firmware", NULL);
    shutdown();
  }

  mpu_config_off();  // needed for flash writable, RAM RWX
  timer_init();
  check_and_replace_bootloader(false);

  // from this point the execution is from RAM instead of flash
  reboot_device();

  return 0;
}
