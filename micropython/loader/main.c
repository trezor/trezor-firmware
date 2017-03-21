#include STM32_HAL_H

#include "common.h"
#include "display.h"

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
