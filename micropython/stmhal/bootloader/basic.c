#include STM32_HAL_H

// ### from main.c

void __attribute__((noreturn)) __fatal_error(const char *msg) {
    for (volatile uint32_t delay = 0; delay < 10000000; delay++) {
    }
    // TODO: printf("FATAL ERROR: %s\n", msg);
    for (;;) {
        __WFI();
    }
}

void nlr_jump_fail(void *val) {
    __fatal_error("FATAL: uncaught exception");
}

// ### from stm32_it.c

void SysTick_Handler(void) {
    extern uint32_t uwTick;
    uwTick += 1;
    SysTick->CTRL;
}

// ###
