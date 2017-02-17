#include STM32_HAL_H
#include "display.h"

// ### from main.c

void __attribute__((noreturn)) __fatal_error(const char *msg) {
    for (volatile uint32_t delay = 0; delay < 10000000; delay++) {
    }
    display_print("FATAL ERROR:\n", -1);
    display_print(msg, -1);
    display_print("\n", -1);
    for (;;) {
        __WFI();
    }
}

// ### from stm32_it.c

void SysTick_Handler(void) {
    extern uint32_t uwTick;
    uwTick += 1;
    SysTick->CTRL;
}

// ###
