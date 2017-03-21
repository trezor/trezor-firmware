#include STM32_HAL_H

#include "display.h"

#define FATAL_FGCOLOR 0xFFFF
#define FATAL_BGCOLOR 0x001F

void __attribute__((noreturn)) __fatal_error(const char *msg) {
    for (volatile uint32_t delay = 0; delay < 10000000; delay++) {
    }
    display_print("FATAL ERROR:\n", -1);
    display_print(msg, -1);
    display_print("\n", -1);
    display_print_out(FATAL_FGCOLOR, FATAL_BGCOLOR);
    for (;;) {
        display_backlight(255);
        HAL_Delay(950);
        display_backlight(128);
        HAL_Delay(50);
    }
}

void __attribute__((noreturn)) nlr_jump_fail(void *val) {
    __fatal_error("uncaught exception");
}
