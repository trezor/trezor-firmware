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

#include "common.h"
#include <stdio.h>
#include "bitmaps.h"
#include "firmware/usb.h"
#include "hmac_drbg.h"
#include "layout.h"
#include "oled.h"
#include "rng.h"
#include "util.h"

uint8_t HW_ENTROPY_DATA[HW_ENTROPY_LEN];

static HMAC_DRBG_CTX drbg_ctx;

void __attribute__((noreturn))
__fatal_error(const char *expr, const char *msg, const char *file, int line_num,
              const char *func) {
  const BITMAP *icon = &bmp_icon_error;
  char line[128] = {0};
  int y = icon->height + 3;
  oledClear();

  oledDrawBitmap(0, 0, icon);
  oledDrawStringCenter(OLED_WIDTH / 2, (icon->height - FONT_HEIGHT) / 2 + 1,
                       "FATAL  ERROR", FONT_STANDARD);

  snprintf(line, sizeof(line), "Expr: %s", expr ? expr : "(null)");
  oledDrawString(0, y, line, FONT_STANDARD);
  y += FONT_HEIGHT + 1;

  snprintf(line, sizeof(line), "Msg: %s", msg ? msg : "(null)");
  oledDrawString(0, y, line, FONT_STANDARD);
  y += FONT_HEIGHT + 1;

  const char *label = "File: ";
  snprintf(line, sizeof(line), "%s:%d", file ? file : "(null)", line_num);
  oledDrawStringRight(OLED_WIDTH - 1, y, line, FONT_STANDARD);
  oledBox(0, y, oledStringWidth(label, FONT_STANDARD), y + FONT_HEIGHT, false);
  oledDrawString(0, y, label, FONT_STANDARD);
  y += FONT_HEIGHT + 1;

  snprintf(line, sizeof(line), "Func: %s", func ? func : "(null)");
  oledDrawString(0, y, line, FONT_STANDARD);
  y += FONT_HEIGHT + 1;

  oledDrawString(0, y, "Contact Trezor support.", FONT_STANDARD);
  oledRefresh();

  shutdown();
}

void __attribute__((noreturn))
error_shutdown(const char *line1, const char *line2, const char *line3,
               const char *line4) {
  layoutDialog(&bmp_icon_error, NULL, NULL, NULL, line1, line2, line3, line4,
               "Please unplug", "the device.");
  shutdown();
}

#ifndef NDEBUG
void __assert_func(const char *file, int line, const char *func,
                   const char *expr) {
  __fatal_error(expr, "assert failed", file, line, func);
}
#endif

void hal_delay(uint32_t ms) { usbSleep(ms); }

void drbg_init() {
  uint8_t entropy[48] = {0};
  random_buffer(entropy, sizeof(entropy));
  hmac_drbg_init(&drbg_ctx, entropy, sizeof(entropy), NULL, 0);
}

void drbg_reseed(const uint8_t *entropy, size_t len) {
  hmac_drbg_reseed(&drbg_ctx, entropy, len, NULL, 0);
}

void drbg_generate(uint8_t *buf, size_t len) {
  hmac_drbg_generate(&drbg_ctx, buf, len);
}

uint32_t drbg_random32(void) {
  uint32_t value = 0;
  drbg_generate((uint8_t *)&value, sizeof(value));
  return value;
}
