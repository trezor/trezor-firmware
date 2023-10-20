/*
 * This file is part of the Trezor project, https://trezor.io/
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
#include "display.h"
#include "flash.h"
#include "image.h"
#include "mini_printf.h"
#include "mpu.h"
#include "random_delays.h"
#include "rng.h"
#include "secbool.h"
#ifdef USE_TOUCH
#include "touch.h"
#endif
#include "usb.h"
#include "version.h"

#include "bootui.h"
#include "messages.h"
#include "model.h"
// #include "mpu.h"

#define USB_IFACE_NUM 0

static void usb_init_all(secbool usb21_landing) {
  usb_dev_info_t dev_info = {
      .device_class = 0x00,
      .device_subclass = 0x00,
      .device_protocol = 0x00,
      .vendor_id = 0x1209,
      .product_id = 0x53C0,
      .release_num = 0x0200,
      .manufacturer = "SatoshiLabs",
      .product = "TREZOR",
      .serial_number = "000000000000000000000000",
      .interface = "TREZOR Interface",
      .usb21_enabled = sectrue,
      .usb21_landing = usb21_landing,
  };

  static uint8_t rx_buffer[USB_PACKET_SIZE];

  static const usb_webusb_info_t webusb_info = {
      .iface_num = USB_IFACE_NUM,
      .ep_in = USB_EP_DIR_IN | 0x01,
      .ep_out = USB_EP_DIR_OUT | 0x01,
      .subclass = 0,
      .protocol = 0,
      .max_packet_len = sizeof(rx_buffer),
      .rx_buffer = rx_buffer,
      .polling_interval = 1,
  };

  usb_init(&dev_info);

  ensure(usb_webusb_add(&webusb_info), NULL);

  usb_start();
}

static secbool bootloader_usb_loop(const vendor_header *const vhdr,
                                   const image_header *const hdr) {
  // if both are NULL, we don't have a firmware installed
  // let's show a webusb landing page in this case
  usb_init_all((vhdr == NULL && hdr == NULL) ? sectrue : secfalse);

  uint8_t buf[USB_PACKET_SIZE];

  for (;;) {
    int r = usb_webusb_read_blocking(USB_IFACE_NUM, buf, USB_PACKET_SIZE,
                                     USB_TIMEOUT);
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
      case 0:  // Initialize
        process_msg_Initialize(USB_IFACE_NUM, msg_size, buf, vhdr, hdr);
        break;
      case 1:  // Ping
        process_msg_Ping(USB_IFACE_NUM, msg_size, buf);
        break;
      case 5:  // WipeDevice
        ui_screen_wipe();
        r = process_msg_WipeDevice(USB_IFACE_NUM, msg_size, buf);
        if (r < 0) {  // error
          ui_screen_fail();
          usb_stop();
          usb_deinit();
          return secfalse;  // shutdown
        } else {            // success
          ui_screen_done(0, sectrue);
          usb_stop();
          usb_deinit();
          return secfalse;  // shutdown
        }
        break;
      case 6:  // FirmwareErase
        process_msg_FirmwareErase(USB_IFACE_NUM, msg_size, buf);
        break;
      case 7:  // FirmwareUpload
        r = process_msg_FirmwareUpload(USB_IFACE_NUM, msg_size, buf);
        if (r < 0 && r != UPLOAD_ERR_USER_ABORT) {  // error, but not user abort
          ui_screen_fail();
          usb_stop();
          usb_deinit();
          return secfalse;    // shutdown
        } else if (r == 0) {  // last chunk received
          ui_screen_install_progress_upload(1000);
          ui_screen_done(4, sectrue);
          ui_screen_done(3, secfalse);
          hal_delay(1000);
          ui_screen_done(2, secfalse);
          hal_delay(1000);
          ui_screen_done(1, secfalse);
          hal_delay(1000);
          usb_stop();
          usb_deinit();
          return sectrue;  // jump to firmware
        }
        break;
      case 55:  // GetFeatures
        process_msg_GetFeatures(USB_IFACE_NUM, msg_size, buf, vhdr, hdr);
        break;
      default:
        process_msg_unknown(USB_IFACE_NUM, msg_size, buf);
        break;
    }
  }
}

static secbool check_vendor_header_lock(const vendor_header *const vhdr) {
  uint8_t lock[FLASH_OTP_BLOCK_SIZE];
  ensure(flash_otp_read(FLASH_OTP_BLOCK_VENDOR_HEADER_LOCK, 0, lock,
                        FLASH_OTP_BLOCK_SIZE),
         NULL);
  if (0 ==
      memcmp(lock,
             "\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF"
             "\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF",
             FLASH_OTP_BLOCK_SIZE)) {
    return sectrue;
  }
  uint8_t hash[32];
  vendor_header_hash(vhdr, hash);
  return sectrue * (0 == memcmp(lock, hash, 32));
}

// protection against bootloader downgrade

#if PRODUCTION

static void check_bootloader_version(void) {
  uint8_t bits[FLASH_OTP_BLOCK_SIZE];
  for (int i = 0; i < FLASH_OTP_BLOCK_SIZE * 8; i++) {
    if (i < VERSION_MONOTONIC) {
      bits[i / 8] &= ~(1 << (7 - (i % 8)));
    } else {
      bits[i / 8] |= (1 << (7 - (i % 8)));
    }
  }
  ensure(flash_otp_write(FLASH_OTP_BLOCK_BOOTLOADER_VERSION, 0, bits,
                         FLASH_OTP_BLOCK_SIZE),
         NULL);

  uint8_t bits2[FLASH_OTP_BLOCK_SIZE];
  ensure(flash_otp_read(FLASH_OTP_BLOCK_BOOTLOADER_VERSION, 0, bits2,
                        FLASH_OTP_BLOCK_SIZE),
         NULL);

  ensure(sectrue * (0 == memcmp(bits, bits2, FLASH_OTP_BLOCK_SIZE)),
         "Bootloader downgraded");
}

#endif

int main(void) {
  random_delays_init();
#ifdef USE_TOUCH
  touch_init();
  touch_power_on();
#endif

  mpu_config_bootloader();

#if PRODUCTION
  check_bootloader_version();
#endif

  display_clear();

  const image_header *hdr = NULL;
  vendor_header vhdr;
  // detect whether the device contains a valid firmware
  secbool firmware_present = sectrue;

  if (sectrue != read_vendor_header((const uint8_t *)FIRMWARE_START, &vhdr)) {
    firmware_present = secfalse;
  }

  if (sectrue == firmware_present) {
    firmware_present = check_vendor_header_keys(&vhdr);
  }

  if (sectrue == firmware_present) {
    firmware_present = check_vendor_header_lock(&vhdr);
  }

  if (sectrue == firmware_present) {
    hdr = read_image_header((const uint8_t *)(FIRMWARE_START + vhdr.hdrlen),
                            FIRMWARE_IMAGE_MAGIC, FIRMWARE_IMAGE_MAXSIZE);
    if (hdr != (const image_header *)(FIRMWARE_START + vhdr.hdrlen)) {
      firmware_present = secfalse;
    }
  }
  if (sectrue == firmware_present) {
    firmware_present = check_image_model(hdr);
  }
  if (sectrue == firmware_present) {
    firmware_present =
        check_image_header_sig(hdr, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub);
  }
  if (sectrue == firmware_present) {
    firmware_present = check_image_contents(
        hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen, &FIRMWARE_AREA);
  }

  // always start bootloader even if firmware is already present
  // show intro animation

  // no ui_fadeout(); - we already start from black screen
  ui_screen_welcome_third();
  ui_fadein();

  // and start the usb loop
  if (bootloader_usb_loop(NULL, NULL) != sectrue) {
    return 1;
  }

  ensure(read_vendor_header((const uint8_t *)FIRMWARE_START, &vhdr),
         "invalid vendor header");

  ensure(check_vendor_header_keys(&vhdr), "invalid vendor header signature");

  ensure(check_vendor_header_lock(&vhdr), "unauthorized vendor keys");

  hdr = read_image_header((const uint8_t *)(FIRMWARE_START + vhdr.hdrlen),
                          FIRMWARE_IMAGE_MAGIC, FIRMWARE_IMAGE_MAXSIZE);

  ensure(hdr == (const image_header *)(FIRMWARE_START + vhdr.hdrlen) ? sectrue
                                                                     : secfalse,
         "invalid firmware header");

  ensure(check_image_model(hdr), "wrong firmware model");

  ensure(check_image_header_sig(hdr, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub),
         "invalid firmware signature");

  ensure(check_image_contents(hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen,
                              &FIRMWARE_AREA),
         "invalid firmware hash");

  // do not check any trust flags on header, proceed

  // mpu_config_firmware();
  // jump_to_unprivileged(FIRMWARE_START + vhdr.hdrlen + IMAGE_HEADER_SIZE);

  mpu_config_off();
  jump_to(FIRMWARE_START + vhdr.hdrlen + IMAGE_HEADER_SIZE);

  return 0;
}
