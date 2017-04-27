#include STM32_HAL_H

#include <string.h>
#include <sys/types.h>

#include "common.h"
#include "display.h"
#include "image.h"
#include "flash.h"
#include "touch.h"
#include "usb.h"
#include "version.h"

#include "messages.h"
#include "protobuf.h"

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
        .manufacturer_str  = (const uint8_t *)"SatoshiLabs",
        .product_str       = (const uint8_t *)"TREZOR Bootloader",
        .serial_number_str = (const uint8_t *)"",
        .configuration_str = (const uint8_t *)"",
        .interface_str     = (const uint8_t *)"",
    };
    static uint8_t hid_rx_buffer[64];
    static const uint8_t hid_report_desc[] = {
        0x06, 0x00, 0xff,  // USAGE_PAGE (Vendor Defined)
        0x09, 0x01,        // USAGE (1)
        0xa1, 0x01,        // COLLECTION (Application)
        0x09, 0x20,        // USAGE (Input Report Data)
        0x15, 0x00,        // LOGICAL_MINIMUM (0)
        0x26, 0xff, 0x00,  // LOGICAL_MAXIMUM (255)
        0x75, 0x08,        // REPORT_SIZE (8)
        0x95, 0x40,        // REPORT_COUNT (64)
        0x81, 0x02,        // INPUT (Data,Var,Abs)
        0x09, 0x21,        // USAGE (Output Report Data)
        0x15, 0x00,        // LOGICAL_MINIMUM (0)
        0x26, 0xff, 0x00,  // LOGICAL_MAXIMUM (255)
        0x75, 0x08,        // REPORT_SIZE (8)
        0x95, 0x40,        // REPORT_COUNT (64)
        0x91, 0x02,        // OUTPUT (Data,Var,Abs)
        0xc0               // END_COLLECTION
    };
    static const usb_hid_info_t hid_info = {
        .iface_num        = 0x00,
        .ep_in            = USB_EP_DIR_IN | 0x01,
        .ep_out           = USB_EP_DIR_OUT | 0x01,
        .subclass         = 0,
        .protocol         = 0,
        .max_packet_len   = sizeof(hid_rx_buffer),
        .rx_buffer        = hid_rx_buffer,
        .polling_interval = 1,
        .report_desc_len  = sizeof(hid_report_desc),
        .report_desc      = hid_report_desc,
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

void mainloop(void)
{
    if (0 != flash_init()) {
        __fatal_error("flash_init failed");
    }

    if (0 != usb_init_all()) {
        __fatal_error("usb_init_all failed");
    }

    uint8_t buf[64];

    for (;;) {
        int iface = usb_hid_read_select(1); // 1ms timeout
        if (iface < 0) {
            continue;
        }
        ssize_t r = usb_hid_read(iface, buf, sizeof(buf));
        // invalid length
        if (r != sizeof(buf)) {
            continue;
        }
        uint16_t msg_id;
        uint32_t msg_size;
        // invalid header
        if (!pb_parse_header(buf, &msg_id, &msg_size)) {
            continue;
        }
        static uint32_t chunk = 0;
        switch (msg_id) {
            case 0: // Initialize
                DPRINTLN("received Initialize");
                send_msg_Features(iface, false);
                break;
            case 1: // Ping
                DPRINTLN("received Ping");
                send_msg_Success(iface);
                break;
            case 6: // FirmwareErase
                DPRINTLN("received FirmwareErase");
                send_msg_FirmwareRequest(iface, 0, 128 * 1024);
                chunk = 0;
                break;
            case 7: // FirmwareUpload
                DPRINTLN("received FirmwareUpload");
                // TODO: process chunk
                chunk++;
                if (chunk <= 3) {
                    send_msg_FirmwareRequest(iface, chunk * 128 * 1024, 128 * 1024);
                } else {
                    send_msg_Success(iface);
                }
                break;
            default:
                DPRINTLN("received unknown message");
                send_msg_Failure(iface);
                break;
        }
    }
}

int main(void)
{
    periph_init();

    if (0 != display_init()) {
        __fatal_error("display_init failed");
    }

    if (0 != touch_init()) {
        __fatal_error("touch_init failed");
    }

    display_clear();
    display_backlight(255);

    DPRINTLN("TREZOR Bootloader " VERSION_STR);
    DPRINTLN("=================");
    DPRINTLN("starting bootloader");

    if (touch_read() != 0) {
        mainloop();
    } else {
        check_and_jump();
    }

    __fatal_error("halt");

    return 0;
}

#ifndef NDEBUG
void __assert_func(const char *file, int line, const char *func, const char *expr) {
    // printf("Assertion '%s' failed, at file %s:%d\n", expr, file, line);
    __fatal_error("Assertion failed");
}
#endif
