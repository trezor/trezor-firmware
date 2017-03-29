#include STM32_HAL_H

#include "display.h"

#define FATAL_FGCOLOR 0xFFFF
#define FATAL_BGCOLOR 0x7800

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
