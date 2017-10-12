#include STM32_HAL_H

#include "common.h"
#include "display.h"
#include "rng.h"

void shutdown(void);

void __attribute__((noreturn)) __fatal_error(const char *expr, const char *msg, const char *file, int line, const char *func) {
    display_orientation(0);
    display_backlight(255);
    display_print_color(COLOR_WHITE, COLOR_RED128);
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
#define XSTR(s) STR(s)
#define STR(s) #s
    display_printf("rev : %s\n", XSTR(GITREV));
#endif
    shutdown();
    for (;;);
}

uint32_t __stack_chk_guard;

void __attribute__((noreturn)) __stack_chk_fail(void)
{
    ensure(0, "Stack smashing detected");
}

#ifndef NDEBUG
void __assert_func(const char *file, int line, const char *func, const char *expr) {
    __fatal_error(expr, "assert failed", file, line, func);
}
#endif

void periph_init(void) {

    // STM32F4xx HAL library initialization:
    //  - configure the Flash prefetch, instruction and data caches
    //  - configure the Systick to generate an interrupt each 1 msec
    //  - set NVIC Group Priority to 4
    //  - global MSP (MCU Support Package) initialization
    HAL_Init();

    // Enable GPIO clocks
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    // Clear the reset flags
    PWR->CR |= PWR_CR_CSBF;
    RCC->CSR |= RCC_CSR_RMVF;

    // Enable CPU ticks
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;  // Enable DWT
    DWT->CYCCNT = 0;  // Reset Cycle Count Register
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;  // Enable Cycle Count Register
}

void hal_delay(uint32_t ms)
{
    HAL_Delay(ms);
}
