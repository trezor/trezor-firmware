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
#include <stdlib.h>
#include <unistd.h>

#include "common.h"
#include "display.h"

void __shutdown(void)
{
    printf("SHUTDOWN\n");
    exit(3);
}

#define COLOR_FATAL_ERROR RGB16(0x7F, 0x00, 0x00)

void __attribute__((noreturn)) __fatal_error(const char *expr, const char *msg, const char *file, int line, const char *func)
{
    display_orientation(0);
    display_backlight(255);
    display_print_color(COLOR_WHITE, COLOR_FATAL_ERROR);
    display_printf("\nFATAL ERROR:\n");
    printf("\nFATAL ERROR:\n");
    if (expr) {
        display_printf("expr: %s\n", expr);
        printf("expr: %s\n", expr);
    }
    if (msg) {
        display_printf("msg : %s\n", msg);
        printf("msg : %s\n", msg);
    }
    if (file) {
        display_printf("file: %s:%d\n", file, line);
        printf("file: %s:%d\n", file, line);
    }
    if (func) {
        display_printf("func: %s\n", func);
        printf("func: %s\n", func);
    }
#ifdef GITREV
    display_printf("rev : %s\n", XSTR(GITREV));
    printf("rev : %s\n", XSTR(GITREV));
#endif
    hal_delay(3000);
    __shutdown();
    for (;;);
}

void hal_delay(uint32_t ms)
{
    usleep(1000 * ms);
}
