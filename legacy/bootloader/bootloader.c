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

#include <string.h>

#include <libopencm3/cm3/scb.h>
#include <libopencm3/stm32/gpio.h>
#include <libopencm3/stm32/rcc.h>

#include "bootloader.h"
#include "buttons.h"
#include "compiler_traits.h"
#include "layout.h"
#include "memory.h"
#include "oled.h"
#include "rng.h"
#include "setup.h"
#include "signatures.h"
#include "supervise.h"
#include "usb.h"
#include "util.h"

void layoutFirmwareFingerprint(const uint8_t *hash) {
  char str[4][17] = {0};
  for (int i = 0; i < 4; i++) {
    data2hex(hash + i * 8, 8, str[i]);
  }
  layoutDialog(&bmp_icon_question, "Abort", "Continue", "Compare fingerprints",
               str[0], str[1], str[2], str[3], NULL, NULL);
}

bool get_button_response(void) {
  do {
    delay(100000);
    buttonUpdate();
  } while (!button.YesUp && !button.NoUp);
  return button.YesUp;
}

void show_halt(const char *line1, const char *line2) {
  layoutDialog(&bmp_icon_error, NULL, NULL, NULL, line1, line2, NULL,
               "Unplug your Trezor,", "reinstall firmware.", NULL);
  shutdown();
}

void show_unplug(const char *line1, const char *line2) {
  layoutDialog(&bmp_icon_ok, NULL, NULL, NULL, line1, line2, NULL,
               "You may now", "unplug your Trezor.", NULL);
}

static void show_unofficial_warning(const uint8_t *hash) {
  layoutDialog(&bmp_icon_warning, "Abort", "I'll take the risk", NULL,
               "WARNING!", NULL, "Unofficial firmware", "detected.", NULL,
               NULL);

  bool but = get_button_response();
  if (!but) {  // no button was pressed -> halt
    show_halt("Unofficial firmware", "aborted.");
  }

  layoutFirmwareFingerprint(hash);

  but = get_button_response();
  if (!but) {  // no button was pressed -> halt
    show_halt("Unofficial firmware", "aborted.");
  }

  // everything is OK, user pressed 2x Continue -> continue program
}

static void __attribute__((noreturn)) load_app(int signed_firmware) {
  // zero out SRAM
  memset_reg(_ram_start, _ram_end, 0);

  jump_to_firmware((const vector_table_t *)FLASH_PTR(FLASH_APP_START),
                   signed_firmware);
}

static void bootloader_loop(void) {
  oledClear();
  oledDrawBitmap(0, 0, &bmp_logo64_half);
  oledDrawBitmapFlip(24, 0, &bmp_logo64_half);
  if (firmware_present_new()) {
    oledDrawStringCenter(90, 10, "Trezor", FONT_STANDARD);
    oledDrawStringCenter(90, 30, "Bootloader", FONT_STANDARD);
    oledDrawStringCenter(90, 50,
                         VERSTR(VERSION_MAJOR) "." VERSTR(
                             VERSION_MINOR) "." VERSTR(VERSION_PATCH),
                         FONT_STANDARD);
  } else {
    oledDrawStringCenter(90, 10, "Welcome!", FONT_STANDARD);
    oledDrawStringCenter(90, 30, "Please visit", FONT_STANDARD);
    oledDrawStringCenter(90, 50, "trezor.io/start", FONT_STANDARD);
  }
  oledRefresh();

  usbLoop();
}

int main(void) {
  // grab "stay in bootloader" flag as soon as possible
  register uint32_t r11 __asm__("r11");
  volatile uint32_t stay_in_bootloader_flag = r11;

#ifndef APPVER
  setup();
#endif
  __stack_chk_guard = random32();  // this supports compiler provided
                                   // unpredictable stack protection checks
#ifndef APPVER
  memory_protect();
  oledInit();
#endif

  mpu_config_bootloader();

  if (stay_in_bootloader_flag == STAY_IN_BOOTLOADER_FLAG) {
    goto bootloader_loop_start;
  }

#ifndef APPVER
  bool left_pressed = (buttonRead() & BTN_PIN_NO) == 0;

  if (firmware_present_new() && !left_pressed) {
    oledClear();
    oledDrawBitmap(40, 0, &bmp_logo64_empty_half);
    oledDrawBitmapFlip(40 + 24, 0, &bmp_logo64_empty_half);
    oledRefresh();

    const image_header *hdr =
        (const image_header *)FLASH_PTR(FLASH_FWHEADER_START);

    uint8_t fingerprint[32] = {0};
    int signed_firmware = signatures_new_ok(hdr, fingerprint);
    if (SIG_OK != signed_firmware) {
      show_unofficial_warning(fingerprint);
    }

    if (SIG_OK != check_firmware_hashes(hdr)) {
      show_halt("Broken firmware", "detected.");
    }

    mpu_config_off();
    load_app(signed_firmware);
  }
#endif

bootloader_loop_start:

  bootloader_loop();

  return 0;
}
