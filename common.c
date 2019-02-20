/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include <stdio.h>
#include "common.h"
#include "rng.h"
#include "layout.h"
#include "oled.h"
#include "util.h"
#include "firmware/usb.h"

uint8_t HW_ENTROPY_DATA[HW_ENTROPY_LEN];

void __attribute__((noreturn)) __fatal_error(const char *expr, const char *msg, const char *file, int line_num, const char *func) {
    const BITMAP *icon = &bmp_icon_error;
    char line[128] = {0};
    int y = icon->height + 3;
    oledClear();

    oledDrawBitmap(0, 0, icon);
    oledDrawStringCenter(OLED_WIDTH / 2, (icon->height - FONT_HEIGHT)/2 + 1, "FATAL  ERROR", FONT_STANDARD);

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

    oledDrawString(0, y, "Contact TREZOR support.", FONT_STANDARD);
    oledRefresh();

    shutdown();
}

void __attribute__((noreturn)) error_shutdown(const char *line1, const char *line2, const char *line3, const char *line4) {
    layoutDialog(&bmp_icon_error, NULL, NULL, NULL, line1, line2, line3, line4, "Please unplug", "the device.");
    shutdown();
}

#ifndef NDEBUG
void __assert_func(const char *file, int line, const char *func, const char *expr) {
    __fatal_error(expr, "assert failed", file, line, func);
}
#endif

void hal_delay(uint32_t ms)
{
    usbSleep(ms);
}
