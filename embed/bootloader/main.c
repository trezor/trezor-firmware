#include <string.h>
#include <sys/types.h>

#include "common.h"
#include "display.h"
#include "image.h"
#include "flash.h"
#include "rng.h"
#include "touch.h"
#include "usb.h"
#include "version.h"
#include "mini_printf.h"

#include "messages.h"

#define IMAGE_MAGIC   0x465A5254 // TRZF
#define IMAGE_MAXSIZE (7 * 128 * 1024)

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
    display_text_center(120, 192, vstr, vstr_len, FONT_BOLD, COLOR_WHITE, COLOR_BLACK);
    char ver_str[32];
    mini_snprintf(ver_str, sizeof(ver_str), "%d.%d.%d.%d",
        (int)(fw_version & 0xFF),
        (int)((fw_version >> 8) & 0xFF),
        (int)((fw_version >> 16) & 0xFF),
        (int)((fw_version >> 24) & 0xFF)
    );
    display_text_center(120, 215, ver_str, -1, FONT_BOLD, COLOR_GRAY128, COLOR_BLACK);
    display_refresh();
}

const uint8_t BOOTLOADER_KEY_M = 2;
const uint8_t BOOTLOADER_KEY_N = 3;
static const uint8_t * const BOOTLOADER_KEYS[] = {
#if PRODUCTION
    (const uint8_t *)"\xc2\xc8\x7a\x49\xc5\xa3\x46\x09\x77\xfb\xb2\xec\x9d\xfe\x60\xf0\x6b\xd6\x94\xdb\x82\x44\xbd\x49\x81\xfe\x3b\x7a\x26\x30\x7f\x3f",
    (const uint8_t *)"\x80\xd0\x36\xb0\x87\x39\xb8\x46\xf4\xcb\x77\x59\x30\x78\xde\xb2\x5d\xc9\x48\x7a\xed\xcf\x52\xe3\x0b\x4f\xb7\xcd\x70\x24\x17\x8a",
    (const uint8_t *)"\xb8\x30\x7a\x71\xf5\x52\xc6\x0a\x4c\xbb\x31\x7f\xf4\x8b\x82\xcd\xbf\x6b\x6b\xb5\xf0\x4c\x92\x0f\xec\x7b\xad\xf0\x17\x88\x37\x51",
#else
    (const uint8_t *)"\xd7\x59\x79\x3b\xbc\x13\xa2\x81\x9a\x82\x7c\x76\xad\xb6\xfb\xa8\xa4\x9a\xee\x00\x7f\x49\xf2\xd0\x99\x2d\x99\xb8\x25\xad\x2c\x48",
    (const uint8_t *)"\x63\x55\x69\x1c\x17\x8a\x8f\xf9\x10\x07\xa7\x47\x8a\xfb\x95\x5e\xf7\x35\x2c\x63\xe7\xb2\x57\x03\x98\x4c\xf7\x8b\x26\xe2\x1a\x56",
    (const uint8_t *)"\xee\x93\xa4\xf6\x6f\x8d\x16\xb8\x19\xbb\x9b\xeb\x9f\xfc\xcd\xfc\xdc\x14\x12\xe8\x7f\xee\x6a\x32\x4c\x2a\x99\xa1\xe0\xe6\x71\x48",
#endif
};

void check_and_jump(void)
{
    vendor_header vhdr;
    if (!vendor_parse_header((const uint8_t *)FIRMWARE_START, &vhdr)) {
        display_printf("invalid vendor header\n");
        return;
    }

    if (!vendor_check_signature((const uint8_t *)FIRMWARE_START, &vhdr, BOOTLOADER_KEY_M, BOOTLOADER_KEY_N, BOOTLOADER_KEYS)) {
        display_printf("invalid vendor header signature\n");
        return;
    }

    image_header hdr;
    if (!image_parse_header((const uint8_t *)(FIRMWARE_START + vhdr.hdrlen), IMAGE_MAGIC, IMAGE_MAXSIZE, &hdr)) {
        display_printf("invalid firmware header\n");
        return;
    }

    if (image_check_signature((const uint8_t *)(FIRMWARE_START + vhdr.hdrlen), &hdr, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub)) {
        display_vendor(vhdr.vimg, (const char *)vhdr.vstr, vhdr.vstr_len, hdr.version);
        if (vhdr.vtrust < 50) {
            touch_click();
        } else {
            hal_delay(1000);
        }
        jump_to(FIRMWARE_START + vhdr.hdrlen + HEADER_SIZE);
    } else {
        display_printf("invalid firmware signature\n");
    }
}

int usb_init_all(void) {
    static const usb_dev_info_t dev_info = {
        .vendor_id     = 0x1209,
        .product_id    = 0x53C0,
        .release_num   = 0x0002,
        .manufacturer  = (const uint8_t *)"SatoshiLabs",
        .product       = (const uint8_t *)"TREZOR Bootloader",
        .serial_number = (const uint8_t *)"",
    };
    static uint8_t hid_rx_buffer[USB_PACKET_SIZE];
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
        .iface_num        = USB_IFACE_NUM,
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

    ensure(0 == usb_init(&dev_info), NULL);
    ensure(0 == usb_hid_add(&hid_info), NULL);
    ensure(0 == usb_start(), NULL);

    return 0;
}

void mainloop(void)
{
    ensure(0 == flash_init(), NULL);
    ensure(0 == usb_init_all(), NULL);

    display_clear();

    uint8_t buf[USB_PACKET_SIZE];

    for (;;) {
        int r = usb_hid_read_blocking(USB_IFACE_NUM, buf, USB_PACKET_SIZE, 100);
        if (r != USB_PACKET_SIZE) {
            continue;
        }
        ensure(r == USB_PACKET_SIZE, NULL);
        uint16_t msg_id;
        uint32_t msg_size;
        if (!msg_parse_header(buf, &msg_id, &msg_size)) {
            // invalid header -> discard
            continue;
        }
        switch (msg_id) {
            case 0: // Initialize
                process_msg_Initialize(USB_IFACE_NUM, msg_size, buf);
                break;
            case 1: // Ping
                process_msg_Ping(USB_IFACE_NUM, msg_size, buf);
                break;
            case 6: // FirmwareErase
                process_msg_FirmwareErase(USB_IFACE_NUM, msg_size, buf);
                break;
            case 7: // FirmwareUpload
                process_msg_FirmwareUpload(USB_IFACE_NUM, msg_size, buf);
                break;
            default:
                process_msg_unknown(USB_IFACE_NUM, msg_size, buf);
                break;
        }
    }
}

// protection against bootloader downgrade

#define BOOTLOADER_VERSION_OTP_BLOCK 1

void check_bootloader_version(void)
{
    uint8_t bits[FLASH_OTP_BLOCK_SIZE];
    for (int i = 0; i < FLASH_OTP_BLOCK_SIZE * 8; i++) {
        if (i < VERSION_MONOTONIC) {
             bits[i / 8] &= ~(1 << (7 - (i % 8)));
        } else {
             bits[i / 8] |= (1 << (7 - (i % 8)));
        }
    }
    ensure(true == flash_otp_write(BOOTLOADER_VERSION_OTP_BLOCK, 0, bits, FLASH_OTP_BLOCK_SIZE), NULL);

    uint8_t bits2[FLASH_OTP_BLOCK_SIZE];
    ensure(true == flash_otp_read(BOOTLOADER_VERSION_OTP_BLOCK, 0, bits2, FLASH_OTP_BLOCK_SIZE), NULL);

    ensure(0 == memcmp(bits, bits2, FLASH_OTP_BLOCK_SIZE), "Bootloader downgraded");
}

int main(void)
{
    __stack_chk_guard = rng_get();

#if PRODUCTION
    check_bootloader_version();
#endif

    periph_init();

    display_pwm_init();
    display_orientation(0);
    display_backlight(255);

    ensure(0 == touch_init(), NULL);

    uint32_t touched = 0;
    for (int i = 0; i < 10; i++) {
        touched |= touch_read();
    }

    if (touched != 0) {
        mainloop();
    } else {
        check_and_jump();
    }

    ensure(0, "halt");

    return 0;
}
