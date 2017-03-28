#include STM32_HAL_H

#include <string.h>

#include "common.h"
#include "display.h"
#include "image.h"
#include "flash.h"
#include "touch.h"
#include "usb.h"
#include "version.h"

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
    DPRINTLN("checking vendor header");

    vendor_header vhdr;
    if (vendor_parse_header((const uint8_t *)FIRMWARE_START, &vhdr)) {
        DPRINTLN("valid vendor header");
    } else {
        DPRINTLN("invalid vendor header");
        return;
    }

    if (vendor_check_signature((const uint8_t *)FIRMWARE_START, &vhdr)) {
        DPRINTLN("valid vendor header signature");
    } else {
        DPRINTLN("invalid vendor header signature");
        return;
    }

    DPRINTLN("checking firmware header");

    image_header hdr;
    if (image_parse_header((const uint8_t *)(FIRMWARE_START + vhdr.hdrlen), IMAGE_MAGIC, IMAGE_MAXSIZE, &hdr)) {
        DPRINTLN("valid firmware header");
    } else {
        DPRINTLN("invalid firmware header");
        return;
    }

    if (image_check_signature((const uint8_t *)(FIRMWARE_START + vhdr.hdrlen), &hdr, &vhdr)) {
        DPRINTLN("valid firmware signature");

        display_vendor(vhdr.vimg, (const char *)vhdr.vstr, vhdr.vstr_len, hdr.version);
        HAL_Delay(1000); // TODO: remove?
        DPRINTLN("JUMP!");
        jump_to(FIRMWARE_START + vhdr.hdrlen + HEADER_SIZE);

    } else {
        DPRINTLN("invalid firmware signature");
    }
}

int usb_init_all(void) {
    static const usb_dev_info_t dev_info = {
        .vendor_id         = 0x1209,
        .product_id        = 0x53C0,
        .release_num       = 0x0002,
        .manufacturer_str  = (const uint8_t *)"manufacturer_str",
        .product_str       = (const uint8_t *)"product_str",
        .serial_number_str = (const uint8_t *)"serial_number_str",
        .configuration_str = (const uint8_t *)"configuration_str",
        .interface_str     = (const uint8_t *)"interface_str",
    };
    static uint8_t hid_rx_buffer[64];
    static const usb_hid_info_t hid_info = {
        .iface_num        = 0x00,
        .ep_in            = USB_EP_DIR_IN | 0x01,
        .ep_out           = USB_EP_DIR_OUT | 0x01,
        .subclass         = 0,
        .protocol         = 0,
        .rx_buffer        = hid_rx_buffer,
        .max_packet_len   = sizeof(hid_rx_buffer),
        .polling_interval = 1,
        .report_desc_len  = 34,
        .report_desc      = (const uint8_t *)"\x06\x00\xff\x09\x01\xa1\x01\x09\x20\x15\x00\x26\xff\x00\x75\x08\x95\x40\x81\x02\x09\x21\x15\x00\x26\xff\x00\x75\x08\x95\x40\x91\x02\xc0",
    };

    if (0 != usb_init(&dev_info)) {
        __fatal_error("usb_init failed");
    }
    if (0 != usb_hid_add(&hid_info)) {
        __fatal_error("usb_hid_add failed");
    }
    if (0 != usb_start()) {
        __fatal_error("usb_start failed");
    }

    return 0;
}

int main(void)
{
    SCB->VTOR = LOADER_START + HEADER_SIZE;
    periph_init();

    if (0 != display_init()) {
        __fatal_error("display_init failed");
    }

    if (0 != flash_init()) {
        __fatal_error("flash_init failed");
    }

    if (0 != touch_init()) {
        __fatal_error("touch_init failed");
    }

    if (0 != usb_init_all()) {
        __fatal_error("usb_init_all failed");
    }

    display_clear();
    display_backlight(255);

    DPRINTLN("TREZOR Loader " VERSION_STR);
    DPRINTLN("=============");
    DPRINTLN("starting loader");

    if (touch_read() != 0) {
        mainloop();
    } else {
        check_and_jump();
    }

    __fatal_error("halt");

    return 0;
}
