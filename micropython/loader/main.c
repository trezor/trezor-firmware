#include STM32_HAL_H

#include "display.h"

void SystemClock_Config(void);

void __attribute__((noreturn)) nlr_jump_fail(void *val) {
    for (;;) {}
}

void __attribute__((noreturn)) __fatal_error(const char *msg) {
    for (volatile uint32_t delay = 0; delay < 10000000; delay++) {
    }
    display_print("FATAL ERROR:\n", -1);
    display_print(msg, -1);
    display_print("\n", -1);
    display_print_out(0xFFFF, 0x001F);
    for (;;) {
        __WFI();
    }
}

void mp_hal_stdout_tx_str(const char *str) {
}

void periph_init(void)
{
    HAL_Init();

    SystemClock_Config();

    __GPIOA_CLK_ENABLE();
    __GPIOB_CLK_ENABLE();
    __GPIOC_CLK_ENABLE();
    __GPIOD_CLK_ENABLE();

    display_init();
    display_clear();
    display_backlight(255);
}

int main(void)
{
    periph_init();

    __fatal_error("end reached");

    return 0;
}
