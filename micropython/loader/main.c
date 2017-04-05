#include STM32_HAL_H

#include <string.h>

#include "common.h"
#include "display.h"
#include "image.h"

#define LOADER_FGCOLOR 0xFFFF
#define LOADER_BGCOLOR 0x0000

#define LOADER_PRINT(X)   do { display_print(X, -1);      display_print_out(LOADER_FGCOLOR, LOADER_BGCOLOR); } while(0)
#define LOADER_PRINTLN(X) do { display_print(X "\n", -1); display_print_out(LOADER_FGCOLOR, LOADER_BGCOLOR); } while(0)

#define IMAGE_MAGIC   0x465A5254 // TRZF
#define IMAGE_MAXSIZE (7 * 128 * 1024)

void pendsv_isr_handler(void) {
    __fatal_error("pendsv");
}

void display_vendor(const uint8_t *vimg, const char *vstr, uint32_t vstr_len, uint32_t fw_version)
{
    display_clear();
    if (memcmp(vimg, "TOIf", 4) != 0) {
        return;
    }
    uint16_t w = *(uint16_t *)(vimg + 4);
    uint16_t h = *(uint16_t *)(vimg + 6);
    if (w != 120 || h != 120) {
        return;
    }
    uint32_t datalen = *(uint32_t *)(vimg + 8);
    display_image(60, 32, w, h, vimg + 12, datalen);
    display_text_center(120, 192, vstr, vstr_len, FONT_BOLD, 0xFFFF, 0x0000);
    char ver_str[] = "v0.0.0.0";
    // TODO: fixme - the following does not work for values >= 10
    ver_str[1] += fw_version & 0xFF;
    ver_str[3] += (fw_version >> 8) & 0xFF;
    ver_str[5] += (fw_version >> 16) & 0xFF;
    ver_str[7] += (fw_version >> 24) & 0xFF;
    display_text_center(120, 215, ver_str, -1, FONT_NORMAL, 0x7BEF, 0x0000);
    display_refresh();
}

void check_and_jump(void)
{
    LOADER_PRINTLN("checking vendor header");

    vendor_header vhdr;
    if (vendor_parse_header((const uint8_t *)FIRMWARE_START, &vhdr)) {
        LOADER_PRINTLN("valid vendor header");
    } else {
        LOADER_PRINTLN("invalid vendor header");
        return;
    }

    if (vendor_check_signature((const uint8_t *)FIRMWARE_START, &vhdr)) {
        LOADER_PRINTLN("valid vendor header signature");
    } else {
        LOADER_PRINTLN("invalid vendor header signature");
        return;
    }

    LOADER_PRINTLN("checking firmware header");

    image_header hdr;
    if (image_parse_header((const uint8_t *)(FIRMWARE_START + vhdr.hdrlen), IMAGE_MAGIC, IMAGE_MAXSIZE, &hdr)) {
        LOADER_PRINTLN("valid firmware header");
    } else {
        LOADER_PRINTLN("invalid firmware header");
        return;
    }

    if (image_check_signature((const uint8_t *)(FIRMWARE_START + vhdr.hdrlen), &hdr, &vhdr)) {
        LOADER_PRINTLN("valid firmware signature");

        display_vendor(vhdr.vimg, (const char *)vhdr.vstr, vhdr.vstr_len, hdr.version);
        HAL_Delay(1000); // TODO: remove?
        LOADER_PRINTLN("JUMP!");
        jump_to(FIRMWARE_START + vhdr.hdrlen + HEADER_SIZE);

    } else {
        LOADER_PRINTLN("invalid firmware signature");
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
