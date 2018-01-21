#include <string.h>
#include <sys/types.h>

#include "common.h"
#include "display.h"
#include "image.h"
#include "flash.h"
#include "mini_printf.h"
#include "rng.h"
#include "secbool.h"
#include "touch.h"
#include "usb.h"
#include "version.h"

#include "icon_cross.h"
#include "icon_lock.h"
#include "icon_tick.h"
#include "icon_tools.h"
#include "icon_update.h"
#include "icon_wipe.h"
#include "messages.h"
#include "style.h"

#define ICON_TOOLS  0
#define ICON_UPDATE 1
#define ICON_WIPE   2

static void display_header(int icon, const char *text)
{
    display_bar(0, 0, DISPLAY_RESX, 32, COLOR_BL_ORANGE);
    switch (icon) {
        case ICON_TOOLS :
            display_icon(8, 4, 24, 24, toi_icon_tools, sizeof(toi_icon_tools), COLOR_BLACK, COLOR_BL_ORANGE);
            break  ;
        case ICON_UPDATE:
            display_icon(8, 4, 24, 24, toi_icon_update, sizeof(toi_icon_update), COLOR_BLACK, COLOR_BL_ORANGE);
            break;
        case ICON_WIPE:
            display_icon(8, 4, 24, 24, toi_icon_wipe, sizeof(toi_icon_wipe), COLOR_BLACK, COLOR_BL_ORANGE);
            break;
    }
    display_text(8 + 24 + 8, 23, text, -1, FONT_NORMAL, COLOR_BLACK, COLOR_BL_ORANGE, 0);
}

static void display_footer(const char *text, uint16_t color, int bottom)
{
    display_bar(0, DISPLAY_RESY - bottom - 24, DISPLAY_RESX, bottom + 24, COLOR_BLACK);
    display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - bottom, text, -1, FONT_NORMAL, color, COLOR_BLACK, 0);
}

static void display_done(int restart)
{
    if (restart == 0 || restart == 3) {
        display_loader(1000, 0, COLOR_BL_GREEN, COLOR_BLACK, toi_icon_tick, sizeof(toi_icon_tick), COLOR_WHITE);
    }
    if (restart <= 3 && restart >= 1) {
        char count_str[24];
        mini_snprintf(count_str, sizeof(count_str), "Done! Restarting in %ds", restart);
        display_footer(count_str, COLOR_BL_GREEN, 20);
    } else {
        display_footer("Done! Unplug the device", COLOR_BL_GREEN, 20);
    }
}

static void display_error(void)
{
    display_loader(1000, 0, COLOR_BL_RED, COLOR_BLACK, toi_icon_cross, sizeof(toi_icon_cross), COLOR_WHITE);
    display_footer("Error! Unplug the device", COLOR_BL_RED, 20);
}

static void display_welcome(secbool firmware_present)
{
    display_clear();
    if (secfalse == firmware_present) {
        display_icon((DISPLAY_RESX - 124) / 2, (DISPLAY_RESY - 40 - 180) / 2, 124, 180, toi_icon_lock, sizeof(toi_icon_lock), COLOR_WHITE, COLOR_BLACK);
        display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 20, "Go to trezor.io/start", -1, FONT_NORMAL, COLOR_WHITE, COLOR_BLACK, 0);
    }
    if (sectrue == firmware_present) {
        display_header(ICON_TOOLS, "TREZOR Bootloader");
        // TODO: show info about installed firmware (vendor, version, etc.)
    }
    display_fade(0, BACKLIGHT_NORMAL, 1000);
}

#define VENDOR_IMAGE_RESX 120
#define VENDOR_IMAGE_RESY 120

static void display_vendor(const uint8_t *vimg, const char *vstr, uint32_t vstr_len, uint32_t fw_version, uint16_t background)
{
    display_bar(0, 0, DISPLAY_RESX, DISPLAY_RESY, background);
    if (memcmp(vimg, "TOIf", 4) != 0) {
        return;
    }
    uint16_t w = *(uint16_t *)(vimg + 4);
    uint16_t h = *(uint16_t *)(vimg + 6);
    if (w != VENDOR_IMAGE_RESX || h != VENDOR_IMAGE_RESY) {
        return;
    }
    uint32_t datalen = *(uint32_t *)(vimg + 8);
    display_image((DISPLAY_RESX - w) / 2, 32, w, h, vimg + 12, datalen);
    if (vstr && vstr_len) {
        display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 48, vstr, vstr_len, FONT_NORMAL, COLOR_WHITE, background, 0);
    }
    char ver_str[32];
    mini_snprintf(ver_str, sizeof(ver_str), "%d.%d.%d.%d",
        (int)(fw_version & 0xFF),
        (int)((fw_version >> 8) & 0xFF),
        (int)((fw_version >> 16) & 0xFF),
        (int)((fw_version >> 24) & 0xFF)
    );
    display_text_center(DISPLAY_RESX / 2, DISPLAY_RESY - 25, ver_str, -1, FONT_NORMAL, COLOR_GRAY128, background, 0);
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

static void usb_init_all(void) {

    static const usb_dev_info_t dev_info = {
        .vendor_id     = 0x1209,
        .product_id    = 0x53C0,
        .release_num   = 0x0002,
        .manufacturer  = (const uint8_t *)"SatoshiLabs",
        .product       = (const uint8_t *)"TREZOR Bootloader",
        .serial_number = (const uint8_t *)"",
        .configuration = (const uint8_t *)"",
        .interface     = (const uint8_t *)"TREZOR Interface",
    };

    static uint8_t rx_buffer[USB_PACKET_SIZE];

#if USE_WEBUSB
    static const usb_webusb_info_t webusb_info = {
        .iface_num        = USB_IFACE_NUM,
        .ep_in            = USB_EP_DIR_IN | 0x01,
        .ep_out           = USB_EP_DIR_OUT | 0x01,
        .subclass         = 0,
        .protocol         = 0,
        .max_packet_len   = sizeof(rx_buffer),
        .rx_buffer        = rx_buffer,
        .polling_interval = 1,
    };
#else
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
        .max_packet_len   = sizeof(rx_buffer),
        .rx_buffer        = rx_buffer,
        .polling_interval = 1,
        .report_desc_len  = sizeof(hid_report_desc),
        .report_desc      = hid_report_desc,
    };
#endif

    usb_init(&dev_info);

#if USE_WEBUSB
    ensure(usb_webusb_add(&webusb_info), NULL);
#else
    ensure(usb_hid_add(&hid_info), NULL);
#endif

    usb_start();
}

static secbool bootloader_loop(secbool firmware_present)
{
    usb_init_all();

    display_welcome(firmware_present);

    uint8_t buf[USB_PACKET_SIZE];

    for (;;) {
#if USE_WEBUSB
        int r = usb_webusb_read_blocking(USB_IFACE_NUM, buf, USB_PACKET_SIZE, USB_TIMEOUT);
#else
        int r = usb_hid_read_blocking(USB_IFACE_NUM, buf, USB_PACKET_SIZE, USB_TIMEOUT);
#endif
        ensure(sectrue * (r == USB_PACKET_SIZE), NULL);
        uint16_t msg_id;
        uint32_t msg_size;
        if (sectrue != msg_parse_header(buf, &msg_id, &msg_size)) {
            // invalid header -> discard
            continue;
        }
        switch (msg_id) {
            case 0: // Initialize
                process_msg_Initialize(USB_IFACE_NUM, msg_size, buf, firmware_present);
                break;
            case 1: // Ping
                process_msg_Ping(USB_IFACE_NUM, msg_size, buf);
                break;
            case 5: // WipeDevice
                display_fade(BACKLIGHT_NORMAL, 0, 100);
                display_clear();
                display_header(ICON_WIPE, "Wiping Device");
                display_footer("Please wait ...", COLOR_WHITE, 20);
                display_fade(0, BACKLIGHT_NORMAL, 100);
                r = process_msg_WipeDevice(USB_IFACE_NUM, msg_size, buf);
                if (r < 0) { // error
                    display_error();
                    usb_stop();
                    usb_deinit();
                    return secfalse; // shutdown
                } else { // success
                    display_done(0);
                    usb_stop();
                    usb_deinit();
                    return secfalse; // shutdown
                }
                break;
            case 6: // FirmwareErase
                display_fade(BACKLIGHT_NORMAL, 0, 100);
                display_clear();
                display_header(ICON_UPDATE, "Updating Firmware");
                display_footer("Please wait ...", COLOR_WHITE, 20);
                display_fade(0, BACKLIGHT_NORMAL, 100);
                process_msg_FirmwareErase(USB_IFACE_NUM, msg_size, buf);
                break;
            case 7: // FirmwareUpload
                r = process_msg_FirmwareUpload(USB_IFACE_NUM, msg_size, buf);
                if (r < 0) { // error
                    display_error();
                    usb_stop();
                    usb_deinit();
                    return secfalse; // shutdown
                } else
                if (r == 0) { // last chunk received
                    display_done(3); hal_delay(1000);
                    display_done(2); hal_delay(1000);
                    display_done(1); hal_delay(1000);
                    usb_stop();
                    usb_deinit();
                    display_fade(BACKLIGHT_NORMAL, 0, 500);
                    return sectrue; // jump to firmware
                }
                break;
            default:
                process_msg_unknown(USB_IFACE_NUM, msg_size, buf);
                break;
        }
    }
}

secbool load_vendor_header_keys(const uint8_t * const data, vendor_header * const vhdr)
{
    return load_vendor_header(data, BOOTLOADER_KEY_M, BOOTLOADER_KEY_N, BOOTLOADER_KEYS, vhdr);
}

#define OTP_BLOCK_VENDOR_KEYS_LOCK 2

static secbool check_vendor_keys_lock(const vendor_header * const vhdr) {
    uint8_t lock[FLASH_OTP_BLOCK_SIZE];
    ensure(flash_otp_read(OTP_BLOCK_VENDOR_KEYS_LOCK, 0, lock, FLASH_OTP_BLOCK_SIZE), NULL);
    if (0 == memcmp(lock, "\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF", FLASH_OTP_BLOCK_SIZE)) {
        return sectrue;
    }
    uint8_t hash[32];
    vendor_keys_hash(vhdr, hash);
    return sectrue * (0 == memcmp(lock, hash, 32));
}

// protection against bootloader downgrade

#if PRODUCTION

#define OTP_BLOCK_BOOTLOADER_VERSION 1

static void check_bootloader_version(void)
{
    uint8_t bits[FLASH_OTP_BLOCK_SIZE];
    for (int i = 0; i < FLASH_OTP_BLOCK_SIZE * 8; i++) {
        if (i < VERSION_MONOTONIC) {
             bits[i / 8] &= ~(1 << (7 - (i % 8)));
        } else {
             bits[i / 8] |= (1 << (7 - (i % 8)));
        }
    }
    ensure(flash_otp_write(OTP_BLOCK_BOOTLOADER_VERSION, 0, bits, FLASH_OTP_BLOCK_SIZE), NULL);

    uint8_t bits2[FLASH_OTP_BLOCK_SIZE];
    ensure(flash_otp_read(OTP_BLOCK_BOOTLOADER_VERSION, 0, bits2, FLASH_OTP_BLOCK_SIZE), NULL);

    ensure(sectrue * (0 == memcmp(bits, bits2, FLASH_OTP_BLOCK_SIZE)), "Bootloader downgraded");
}

#endif

int main(void)
{
#if PRODUCTION
    check_bootloader_version();
#endif

    touch_init();

    // delay to detect touch
    uint32_t touched = 0;
    for (int i = 0; i < 100; i++) {
        touched = touch_read();
        if (touched) {
            break;
        }
        hal_delay(1);
    }

    vendor_header vhdr;

    // start the bootloader if user touched the screen or no firmware installed
    secbool firmware_present = load_vendor_header_keys((const uint8_t *)FIRMWARE_START, &vhdr);
    if (touched || firmware_present != sectrue) {
        if (bootloader_loop(firmware_present) != sectrue) {
            return 1;
        }
    }

    ensure(
        load_vendor_header_keys((const uint8_t *)FIRMWARE_START, &vhdr),
        "invalid vendor header");

    ensure(
        check_vendor_keys_lock(&vhdr),
        "unauthorized vendor keys");

    image_header hdr;

    ensure(
        load_image_header((const uint8_t *)(FIRMWARE_START + vhdr.hdrlen), FIRMWARE_IMAGE_MAGIC, FIRMWARE_IMAGE_MAXSIZE, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub, &hdr),
        "invalid firmware header");

    const uint8_t sectors[] = {
        FLASH_SECTOR_FIRMWARE_START,
        7,
        8,
        9,
        10,
        FLASH_SECTOR_FIRMWARE_END,
        FLASH_SECTOR_FIRMWARE_EXTRA_START,
        18,
        19,
        20,
        21,
        22,
        FLASH_SECTOR_FIRMWARE_EXTRA_END,
    };
    ensure(
        check_image_contents(&hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen, sectors, 13),
        "invalid firmware hash");

    // if all VTRUST flags are unset = ultimate trust => skip the procedure

    if ((vhdr.vtrust & VTRUST_ALL) != VTRUST_ALL) {

        display_vendor(
            vhdr.vimg,
            ((vhdr.vtrust & VTRUST_STRING) == 0) ? (const char *)vhdr.vstr : 0,
            ((vhdr.vtrust & VTRUST_STRING) == 0) ? vhdr.vstr_len : 0,
            hdr.version,
            ((vhdr.vtrust & VTRUST_RED) == 0) ? COLOR_BL_RED : COLOR_BLACK
        );

        display_fade(0, BACKLIGHT_NORMAL, 1000);

        int start_delay = (vhdr.vtrust & VTRUST_WAIT) ^ VTRUST_WAIT;
        while (start_delay > 0) {
            char wait_str[16];
            mini_snprintf(wait_str, sizeof(wait_str), "waiting for %ds", start_delay);
            display_footer(wait_str, COLOR_GRAY64, 2);
            hal_delay(1000);
            start_delay--;
        }

        if ((vhdr.vtrust & VTRUST_CLICK) == 0) {
            display_footer("click to continue ...", COLOR_GRAY64, 2);
            touch_click();
        }

        display_fade(BACKLIGHT_NORMAL, 0, 500);
        display_clear();
    }

    jump_to(FIRMWARE_START + vhdr.hdrlen + IMAGE_HEADER_SIZE);

    return 0;
}
