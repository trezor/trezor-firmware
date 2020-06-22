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
#include "bitmaps.h"
#include "memzero.h"
#include "oled.h"
#include "rng.h"
#include "setup.h"
#include "timer.h"
#include "util.h"
#if !EMULATOR
#include <libopencm3/stm32/desig.h>
#include <vendor/libopencm3/include/libopencmsis/core_cm3.h>
#endif

/* Screen timeout */
uint32_t system_millis_lock_start = 0;

void __attribute__((noinline, noreturn, section(".data"))) scb_reset_system_ram(void)
{
            SCB_AIRCR = SCB_AIRCR_VECTKEY | SCB_AIRCR_SYSRESETREQ;
                    while (1);
}

void __attribute__((noinline, noreturn, section(".data"))) ram_shim(void) {
    volatile int a = 127;
    asm("");
    a++;
    scb_reset_system_ram();
    for (;;);
}

int main(void) {
  setup();
  __stack_chk_guard = random32();  // this supports compiler provided
                                   // unpredictable stack protection checks
  oledInit();
  mpu_config_off();

  timer_init();

  oledDrawBitmap(40, 0, &bmp_logo64);
  oledRefresh();
  ram_shim();


  return 0;
}
