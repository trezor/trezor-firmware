#include STM32_HAL_H

#include "common.h"
#include "display.h"
#include "crypto.h"

#define LOADER_FGCOLOR 0xFFFF
#define LOADER_BGCOLOR 0x0000

#define LOADER_PRINT(X)   do { display_print(X, -1);      display_print_out(LOADER_FGCOLOR, LOADER_BGCOLOR); } while(0)
#define LOADER_PRINTLN(X) do { display_print(X "\n", -1); display_print_out(LOADER_FGCOLOR, LOADER_BGCOLOR); } while(0)

void pendsv_isr_handler(void) {
    __fatal_error("pendsv");
}

void check_and_jump(void)
{
    LOADER_PRINTLN("checking firmware");
    if (parse_header((const uint8_t *)FIRMWARE_START, NULL, NULL, NULL)) {
        LOADER_PRINTLN("valid firmware header");
        if (check_signature((const uint8_t *)FIRMWARE_START)) {
            LOADER_PRINTLN("valid firmware signature");
            LOADER_PRINTLN("JUMP!");
            // TODO: remove debug wait
            LOADER_PRINTLN("waiting 1 second");
            HAL_Delay(1000);
            // end
            jump_to(FIRMWARE_START + HEADER_SIZE);
        } else {
            LOADER_PRINTLN("invalid firmware signature");
        }
    } else {
        LOADER_PRINTLN("invalid firmware header");
    }
}

int main(void)
{
    SCB->VTOR = LOADER_START + HEADER_SIZE;
    periph_init();

    display_init();
    display_clear();
    display_backlight(255);

    LOADER_PRINTLN("TREZOR Loader");
    LOADER_PRINTLN("=============");
    LOADER_PRINTLN("starting loader");

    check_and_jump();

    __fatal_error("halt");

    return 0;
}
