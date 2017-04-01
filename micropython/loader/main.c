#include STM32_HAL_H

#include <string.h>

#include "common.h"
#include "display.h"
#include "image.h"

#define LOADER_FGCOLOR 0xFFFF
#define LOADER_BGCOLOR 0x0000

#define LOADER_PRINT(X)   do { display_print(X, -1);      display_print_out(LOADER_FGCOLOR, LOADER_BGCOLOR); } while(0)
#define LOADER_PRINTLN(X) do { display_print(X "\n", -1); display_print_out(LOADER_FGCOLOR, LOADER_BGCOLOR); } while(0)

void pendsv_isr_handler(void) {
    __fatal_error("pendsv");
}

void display_vendor(const uint8_t *vimg)
{
    if (memcmp(vimg, "TOIf", 4) != 0) {
        return;
    }
    uint16_t w = *(uint16_t *)(vimg + 4);
    uint16_t h = *(uint16_t *)(vimg + 6);
    uint32_t datalen = *(uint32_t *)(vimg + 8);
    display_image(0, 0, w, h, vimg + 12, datalen);
}

void check_and_jump(void)
{
    LOADER_PRINTLN("checking firmware");

    vendor_header vhdr;
    if (!vendor_parse_header((const uint8_t *)(FIRMWARE_START), &vhdr)) {
        LOADER_PRINTLN("invalid vendor header");
        return;
    }
    if (!vendor_check_signature((const uint8_t *)(FIRMWARE_START))) {
        LOADER_PRINTLN("unsigned vendor header");
        return;
    }

    // TODO: use keys from vendor header in image_check_signature
    if (image_check_signature((const uint8_t *)(FIRMWARE_START + vhdr.hdrlen))) {
        LOADER_PRINTLN("valid firmware image");
        // TODO: remove debug wait
        display_vendor(vhdr.vimg);
        HAL_Delay(1000);
        // end
        LOADER_PRINTLN("JUMP!");
        jump_to(FIRMWARE_START + vhdr.hdrlen + HEADER_SIZE);
    } else {
        LOADER_PRINTLN("invalid firmware image");
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
