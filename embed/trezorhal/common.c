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

#include STM32_HAL_H

#include "common.h"
#include "display.h"
#include "rng.h"

void shutdown(void);

#define COLOR_FATAL_ERROR RGB16(0x7F, 0x00, 0x00)

void __attribute__((noreturn)) __fatal_error(const char *expr, const char *msg, const char *file, int line, const char *func) {
    display_orientation(0);
    display_backlight(255);
    display_print_color(COLOR_WHITE, COLOR_FATAL_ERROR);
    display_printf("\nFATAL ERROR:\n");
    if (expr) {
        display_printf("expr: %s\n", expr);
    }
    if (msg) {
        display_printf("msg : %s\n", msg);
    }
    if (file) {
        display_printf("file: %s:%d\n", file, line);
    }
    if (func) {
        display_printf("func: %s\n", func);
    }
#ifdef GITREV
    display_printf("rev : %s\n", XSTR(GITREV));
#endif
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
    HAL_Delay(ms);
}

// reference RM0090 section 35.12.1 Figure 413
#define USB_OTG_HS_DATA_FIFO_RAM  (USB_OTG_HS_PERIPH_BASE + 0x20000U)
#define USB_OTG_HS_DATA_FIFO_SIZE (4096U)

void clear_otg_hs_memory(void)
{
    // use the HAL version due to section 2.1.6 of STM32F42xx Errata sheet
    __HAL_RCC_USB_OTG_HS_CLK_ENABLE(); // enable USB_OTG_HS peripheral clock so that the peripheral memory is accessible
    memset_reg((volatile void *) USB_OTG_HS_DATA_FIFO_RAM, (volatile void *) (USB_OTG_HS_DATA_FIFO_RAM + USB_OTG_HS_DATA_FIFO_SIZE), 0);
    __HAL_RCC_USB_OTG_HS_CLK_DISABLE(); // disable USB OTG_HS peripheral clock as the peripheral is not needed right now
}

uint32_t __stack_chk_guard = 0;

void __attribute__((noreturn)) __stack_chk_fail(void)
{
    ensure(secfalse, "Stack smashing detected");
}
