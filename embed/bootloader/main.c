/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <string.h>
#include <sys/types.h>

#include "common.h"
#include "image.h"
#include "flash.h"
#include "mini_printf.h"
#include "rng.h"
#include "secbool.h"
#include "touch.h"
#include "usb.h"
#include "version.h"

#include "bootui.h"
#include "messages.h"
// #include "mpu.h"

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

#define USB_IFACE_NUM   0

static void usb_init_all(void) {

    static const usb_dev_info_t dev_info = {
        .device_class    = 0x00,
        .device_subclass = 0x00,
        .device_protocol = 0x00,
        .vendor_id       = 0x1209,
        .product_id      = 0x53C0,
        .release_num     = 0x0200,
        .manufacturer    = "SatoshiLabs",
        .product         = "TREZOR",
        .serial_number   = "000000000000000000000000",
        .interface       = "TREZOR Interface",
        .usb21_enabled   = sectrue,
        .usb21_landing   = sectrue,
    };

    static uint8_t rx_buffer[USB_PACKET_SIZE];

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

    usb_init(&dev_info);

    ensure(usb_webusb_add(&webusb_info), NULL);

    usb_start();
}

static secbool bootloader_usb_loop(const vendor_header * const vhdr, const image_header * const hdr)
{
    usb_init_all();

    uint8_t buf[USB_PACKET_SIZE];

    for (;;) {
        int r = usb_webusb_read_blocking(USB_IFACE_NUM, buf, USB_PACKET_SIZE, USB_TIMEOUT);
        if (r != USB_PACKET_SIZE) {
            continue;
        }
        uint16_t msg_id;
        uint32_t msg_size;
        if (sectrue != msg_parse_header(buf, &msg_id, &msg_size)) {
            // invalid header -> discard
            continue;
        }
        switch (msg_id) {
            case 0: // Initialize
                process_msg_Initialize(USB_IFACE_NUM, msg_size, buf, vhdr, hdr);
                break;
            case 1: // Ping
                process_msg_Ping(USB_IFACE_NUM, msg_size, buf);
                break;
            case 5: // WipeDevice
                ui_fadeout();
                ui_screen_wipe_confirm();
                ui_fadein();
                int response = ui_user_input(INPUT_CONFIRM | INPUT_CANCEL);
                if (INPUT_CANCEL == response) {
                    ui_fadeout();
                    ui_screen_info(secfalse, vhdr, hdr);
                    ui_fadein();
                    send_user_abort(USB_IFACE_NUM, "Wipe cancelled");
                    break;
                }
                ui_fadeout();
                ui_screen_wipe();
                ui_fadein();
                r = process_msg_WipeDevice(USB_IFACE_NUM, msg_size, buf);
                if (r < 0) { // error
                    ui_fadeout();
                    ui_screen_fail();
                    ui_fadein();
                    usb_stop();
                    usb_deinit();
                    return secfalse; // shutdown
                } else { // success
                    ui_fadeout();
                    ui_screen_done(0, sectrue);
                    ui_fadein();
                    usb_stop();
                    usb_deinit();
                    return secfalse; // shutdown
                }
                break;
            case 6: // FirmwareErase
                process_msg_FirmwareErase(USB_IFACE_NUM, msg_size, buf);
                break;
            case 7: // FirmwareUpload
                r = process_msg_FirmwareUpload(USB_IFACE_NUM, msg_size, buf);
                if (r < 0 && r != -4) { // error, but not user abort (-4)
                    ui_fadeout();
                    ui_screen_fail();
                    ui_fadein();
                    usb_stop();
                    usb_deinit();
                    return secfalse; // shutdown
                } else
                if (r == 0) { // last chunk received
                    ui_screen_install_progress_upload(1000);
                    ui_fadeout();
                    ui_screen_done(4, sectrue);
                    ui_fadein();
                    ui_screen_done(3, secfalse);
                    hal_delay(1000);
                    ui_screen_done(2, secfalse);
                    hal_delay(1000);
                    ui_screen_done(1, secfalse);
                    hal_delay(1000);
                    usb_stop();
                    usb_deinit();
                    ui_fadeout();
                    return sectrue; // jump to firmware
                }
                break;
            case 55: // GetFeatures
                process_msg_GetFeatures(USB_IFACE_NUM, msg_size, buf, vhdr, hdr);
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
main_start:
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
    image_header hdr;
    secbool firmware_present;

    // detect whether the devices contains a valid firmware

    firmware_present = load_vendor_header_keys((const uint8_t *)FIRMWARE_START, &vhdr);
    if (sectrue == firmware_present) {
        firmware_present = check_vendor_keys_lock(&vhdr);
    }
    if (sectrue == firmware_present) {
        firmware_present = load_image_header((const uint8_t *)(FIRMWARE_START + vhdr.hdrlen), FIRMWARE_IMAGE_MAGIC, FIRMWARE_IMAGE_MAXSIZE, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub, &hdr);
    }
    if (sectrue == firmware_present) {
        firmware_present = check_image_contents(&hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen, firmware_sectors, FIRMWARE_SECTORS_COUNT);
    }

    // start the bootloader if no or broken firmware found ...
    if (firmware_present != sectrue) {
        // show intro animation

        // no ui_fadeout(); - we already start from black screen
        ui_screen_first();
        ui_fadein();

        hal_delay(1000);

        ui_fadeout();
        ui_screen_second();
        ui_fadein();

        hal_delay(1000);

        ui_fadeout();
        ui_screen_third();
        ui_fadein();

        // erase storage
        static const uint8_t sectors_storage[] = {
            FLASH_SECTOR_STORAGE_1,
            FLASH_SECTOR_STORAGE_2,
        };
        ensure(flash_erase_sectors(sectors_storage, sizeof(sectors_storage), NULL), NULL);

        // and start the usb loop
        if (bootloader_usb_loop(NULL, NULL) != sectrue) {
            return 1;
        }
    } else
    // ... or if user touched the screen on start
    if (touched) {
        // show firmware info with connect buttons

        // no ui_fadeout(); - we already start from black screen
        ui_screen_info(sectrue, &vhdr, &hdr);
        ui_fadein();

        for (;;) {
            int response = ui_user_input(INPUT_CONFIRM | INPUT_CANCEL | INPUT_INFO);
            ui_fadeout();

            // if cancel was pressed -> restart
            if (INPUT_CANCEL == response) {
                goto main_start;
            }

            // if confirm was pressed -> jump out
            if (INPUT_CONFIRM == response) {
                // show firmware info without connect buttons
                ui_screen_info(secfalse, &vhdr, &hdr);
                ui_fadein();
                break;
            }

            // if info icon was pressed -> show fingerprint
            if (INPUT_INFO == response) {
                // show fingerprint
                ui_screen_info_fingerprint(&hdr);
                ui_fadein();
                while (INPUT_LONG_CONFIRM != ui_user_input(INPUT_LONG_CONFIRM)) { }
                ui_fadeout();
                ui_screen_info(sectrue, &vhdr, &hdr);
                ui_fadein();
            }
        }

        // and start the usb loop
        if (bootloader_usb_loop(&vhdr, &hdr) != sectrue) {
            return 1;
        }
    }

    ensure(
        load_vendor_header_keys((const uint8_t *)FIRMWARE_START, &vhdr),
        "invalid vendor header");

    ensure(
        check_vendor_keys_lock(&vhdr),
        "unauthorized vendor keys");

    ensure(
        load_image_header((const uint8_t *)(FIRMWARE_START + vhdr.hdrlen), FIRMWARE_IMAGE_MAGIC, FIRMWARE_IMAGE_MAXSIZE, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub, &hdr),
        "invalid firmware header");

    ensure(
        check_image_contents(&hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen, firmware_sectors, FIRMWARE_SECTORS_COUNT),
        "invalid firmware hash");

    // if all VTRUST flags are unset = ultimate trust => skip the procedure

    if ((vhdr.vtrust & VTRUST_ALL) != VTRUST_ALL) {

        // ui_fadeout();  // no fadeout - we start from black screen
        ui_screen_boot(&vhdr, &hdr);
        ui_fadein();

        int delay = (vhdr.vtrust & VTRUST_WAIT) ^ VTRUST_WAIT;
        if (delay > 1) {
            while (delay > 0) {
                ui_screen_boot_wait(delay);
                hal_delay(1000);
                delay--;
            }
        } else if (delay == 1) {
            hal_delay(1000);
        }

        if ((vhdr.vtrust & VTRUST_CLICK) == 0) {
            ui_screen_boot_click();
            touch_click();
        }

        ui_fadeout();
    }

    // mpu_config();
    // jump_to_unprivileged(FIRMWARE_START + vhdr.hdrlen + IMAGE_HEADER_SIZE);

    jump_to(FIRMWARE_START + vhdr.hdrlen + IMAGE_HEADER_SIZE);

    return 0;
}
