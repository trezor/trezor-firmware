#include STM32_HAL_H

#include "common.h"
#include "display.h"

#define FIRMWARE_START   0x08020000

void pendsv_isr_handler(void) {
    __fatal_error("pendsv");
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
