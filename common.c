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
#include "firmware/usb.h"

void shutdown(void);

void __attribute__((noreturn)) __fatal_error(const char *expr, const char *msg, const char *file, int line_num, const char *func) {
    char line[4][128] = {{0}};
    int i = 0;
    if (expr != NULL) {
        snprintf(line[i], sizeof(line[0]), "Expr: %s", expr);
        i++;
    }
    if (msg != NULL) {
        snprintf(line[i], sizeof(line[0]), "Msg: %s", msg);
        i++;
    }
    if (file != NULL) {
        snprintf(line[i], sizeof(line[0]), "File: %s:%d", file, line_num);
        i++;
    }
    if (func != NULL) {
        snprintf(line[i], sizeof(line[0]), "Func: %s", func);
        i++;
    }
    error_shutdown("FATAL ERROR:", NULL, line[0], line[1], line[2], line[3]);
}

void __attribute__((noreturn)) error_shutdown(const char *line1, const char *line2, const char *line3, const char *line4, const char *line5, const char *line6) {
    layoutDialog(&bmp_icon_error, NULL, NULL, NULL, line1, line2, line3, line4, line5, line6);
    shutdown();
    for (;;);
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
