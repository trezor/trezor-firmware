#include STM32_HAL_H

#include "common.h"
#include "display.h"
#include "rng.h"

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

void clear_peripheral_local_memory(void)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_OTGHSEN; // enable USB_OTG_HS peripheral clock so that the peripheral memory is accessible
    const uint32_t unpredictable = rng_get();
    memset_reg((volatile void *) USB_OTG_HS_DATA_FIFO_RAM, (volatile void *) (USB_OTG_HS_DATA_FIFO_RAM + USB_OTG_HS_DATA_FIFO_SIZE), unpredictable);
    memset_reg((volatile void *) USB_OTG_HS_DATA_FIFO_RAM, (volatile void *) (USB_OTG_HS_DATA_FIFO_RAM + USB_OTG_HS_DATA_FIFO_SIZE), 0);
    RCC->AHB1ENR &= ~RCC_AHB1ENR_OTGHSEN; // disable USB OTG_HS peripheral clock as the peripheral is not needed right now
}
