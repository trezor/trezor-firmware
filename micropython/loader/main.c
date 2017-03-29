#include STM32_HAL_H

#include "common.h"
#include "display.h"

#define FIRMWARE_START   0x08020000

#define LOADER_FGCOLOR 0xFFFF
#define LOADER_BGCOLOR 0x0000

#define LOADER_PRINT(X)   do { display_print(X, -1);      display_print_out(LOADER_FGCOLOR, LOADER_BGCOLOR); } while(0)
#define LOADER_PRINTLN(X) do { display_print(X "\n", -1); display_print_out(LOADER_FGCOLOR, LOADER_BGCOLOR); } while(0)

void pendsv_isr_handler(void) {
    __fatal_error("pendsv");
}

int main(void)
{
    periph_init();

    display_init();
    display_clear();
    display_backlight(255);

    LOADER_PRINTLN("reached loader");
    HAL_Delay(1000);
    LOADER_PRINTLN("jumping to firmware");

    jump_to(FIRMWARE_START);

    return 0;
}
