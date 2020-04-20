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
#include "bl_check.h"
#include "buttons.h"
#include "common.h"
#include "config.h"
#include "gettext.h"
#include "layout.h"
#include "layout2.h"
#include "memzero.h"
#include "oled.h"
#include "rng.h"
#include "setup.h"
#include "timer.h"
#include "usb.h"
#include "util.h"
#if !EMULATOR
#include <libopencm3/stm32/desig.h>
#include "otp.h"
#include "sys.h"
#endif

#define autoPowerOffDelayMsDefault (5 * 60 * 1000U)  // 5 minutes

static void collect_hw_entropy(bool privileged) {
#if EMULATOR
  (void)privileged;
  memzero(HW_ENTROPY_DATA, HW_ENTROPY_LEN);
#else
  if (privileged) {
    desig_get_unique_id((uint32_t *)HW_ENTROPY_DATA);
    // set entropy in the OTP randomness block
    if (!flash_otp_is_locked(FLASH_OTP_BLOCK_RANDOMNESS)) {
      uint8_t entropy[FLASH_OTP_BLOCK_SIZE] = {0};
      random_buffer(entropy, FLASH_OTP_BLOCK_SIZE);
      flash_otp_write(FLASH_OTP_BLOCK_RANDOMNESS, 0, entropy,
                      FLASH_OTP_BLOCK_SIZE);
      flash_otp_lock(FLASH_OTP_BLOCK_RANDOMNESS);
    }
    // collect entropy from OTP randomness block
    flash_otp_read(FLASH_OTP_BLOCK_RANDOMNESS, 0, HW_ENTROPY_DATA + 12,
                   FLASH_OTP_BLOCK_SIZE);
  } else {
    // unprivileged mode => use fixed HW_ENTROPY
    memset(HW_ENTROPY_DATA, 0x3C, HW_ENTROPY_LEN);
  }
#endif
}

int main(void) {
#ifndef APPVER
  setup();
  __stack_chk_guard = random32();  // this supports compiler provided
                                   // unpredictable stack protection checks
  oledInit();
#else
  // check_bootloader();
  setupApp();
#if !EMULATOR
  register_timer("layout", timer1s / 2, layoutStatusLogo);
  register_timer("button", timer1s / 2, buttonsTimer);
#endif
  __stack_chk_guard = random32();  // this supports compiler provided
                                   // unpredictable stack protection checks
#endif

  drbg_init();

  if (!is_mode_unprivileged()) {
    collect_hw_entropy(true);
    timer_init();
#ifdef APPVER
    // enable MPU (Memory Protection Unit)
    mpu_config_firmware();
#endif
  } else {
    collect_hw_entropy(false);
  }

#if DEBUG_LINK
  oledSetDebugLink(1);
#if !EMULATOR
  config_wipe();
#endif
#endif

#if EMULATOR
  g_ucWorkMode = WORK_MODE_USB;
#endif
  config_init();
  layoutHome();
  usbInit();

  for (;;) {
    usbPoll();
    layoutHomeInfo();
  }
  return 0;
}
