#include STM32_HAL_H

#include "display.h"

// ### from main.c

void flash_error(int n) {
    for (int i = 0; i < n; i++) {
        // blink(on)
        HAL_Delay(250);
        // blink(off)
        HAL_Delay(250);
    }
}

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

void SystemClock_Config(void);

// ###

// ### from timer.c

uint32_t timer_get_source_freq(uint32_t tim_id) {
    uint32_t source;
    if (tim_id == 1 || (8 <= tim_id && tim_id <= 11)) {
        // TIM{1,8,9,10,11} are on APB2
        source = HAL_RCC_GetPCLK2Freq();
        if ((uint32_t)((RCC->CFGR & RCC_CFGR_PPRE2) >> 3) != RCC_HCLK_DIV1) {
            source *= 2;
        }
    } else {
        // TIM{2,3,4,5,6,7,12,13,14} are on APB1
        source = HAL_RCC_GetPCLK1Freq();
        if ((uint32_t)(RCC->CFGR & RCC_CFGR_PPRE1) != RCC_HCLK_DIV1) {
            source *= 2;
        }
    }
    return source;
}

// ###

int main(void) {

    HAL_Init();

    SystemClock_Config();

    __GPIOA_CLK_ENABLE();
    __GPIOB_CLK_ENABLE();
    __GPIOC_CLK_ENABLE();
    __GPIOD_CLK_ENABLE();


    display_init();
    display_bar(0, 0, RESX, RESY, 0x0000);
    display_text(0, 0, "TREZOR", 6, 0, 0xFFFF, 0x0000);
    display_backlight(255);

    __fatal_error("end");

    return 0;
}
