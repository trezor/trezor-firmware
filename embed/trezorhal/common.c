#include STM32_HAL_H

#include "common.h"
#include "display.h"

void __attribute__((noreturn)) __fatal_error(const char *msg, const char *file, int line, const char *func) {
    for (volatile uint32_t delay = 0; delay < 10000000; delay++) {}
    display_orientation(0);
    display_backlight(255);
    display_print_color(COLOR_WHITE, COLOR_RED128);
    display_printf("\nFATAL ERROR:\n%s\n", msg);
    if (file) {
        display_printf("File: %s:%d\n", file, line);
    }
    if (func) {
        display_printf("Func: %s\n", func);
    }
    for (;;);
}

#ifndef NDEBUG
void __assert_func(const char *file, int line, const char *func, const char *expr) {
    display_printf("\nassert(%s)\n", expr);
    __fatal_error("Assertion failed", file, line, func);
}
#endif

void __attribute__((noreturn)) nlr_jump_fail(void *val) {
    __fatal_error("uncaught exception", __FILE__, __LINE__, __FUNCTION__);
}

extern void SystemClock_Config(void);

void periph_init(void) {

    // STM32F4xx HAL library initialization:
    //  - configure the Flash prefetch, instruction and data caches
    //  - configure the Systick to generate an interrupt each 1 msec
    //  - set NVIC Group Priority to 4
    //  - global MSP (MCU Support Package) initialization
    HAL_Init();

    // Set the system clock to be HSE
    SystemClock_Config();

    // Enable GPIO clocks
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    // Enable the CCM RAM
    __HAL_RCC_CCMDATARAMEN_CLK_ENABLE();

    // Clear the reset flags
    PWR->CR |= PWR_CR_CSBF;
    RCC->CSR |= RCC_CSR_RMVF;

    // Enable CPU ticks
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;  // Enable DWT
    DWT->CYCCNT = 0;  // Reset Cycle Count Register
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;  // Enable Cycle Count Register
}

void jump_to(uint32_t start)
{
    SCB->VTOR = start;
    __asm__ volatile("msr msp, %0"::"g" (*(volatile uint32_t *)start));
    (*(void (**)())(start + 4))();
}
