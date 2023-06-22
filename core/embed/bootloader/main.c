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
#include "random_delays.h"
#include "secbool.h"
#ifdef TREZOR_EMULATOR
#include "emulator.h"
#else
#include "compiler_traits.h"
#include "mini_printf.h"
#include "mpu.h"
#include "stm32.h"
#endif
#ifdef USE_DMA2D
#include "dma2d.h"
#endif
#ifdef USE_I2C
#include "i2c.h"
#endif
#ifdef USE_TOUCH
#include "touch/touch.h"
#endif
#ifdef USE_BUTTON
#include "button.h"
#endif
#ifdef USE_CONSUMPTION_MASK
#include "consumption_mask.h"
#endif
#ifdef USE_RGB_LED
#include "rgb_led.h"
#endif
#include "model.h"
#include "usb.h"
#include "version.h"

#include "bootui.h"
#include "messages.h"
#include "rust_ui.h"
#include "unit_variant.h"

const uint8_t BOOTLOADER_KEY_M = 2;
const uint8_t BOOTLOADER_KEY_N = 3;
static const uint8_t * const BOOTLOADER_KEYS[] = {
#if BOOTLOADER_QA
    /*** DEVEL/QA KEYS  ***/
    (const uint8_t *)"\xd7\x59\x79\x3b\xbc\x13\xa2\x81\x9a\x82\x7c\x76\xad\xb6\xfb\xa8\xa4\x9a\xee\x00\x7f\x49\xf2\xd0\x99\x2d\x99\xb8\x25\xad\x2c\x48",
    (const uint8_t *)"\x63\x55\x69\x1c\x17\x8a\x8f\xf9\x10\x07\xa7\x47\x8a\xfb\x95\x5e\xf7\x35\x2c\x63\xe7\xb2\x57\x03\x98\x4c\xf7\x8b\x26\xe2\x1a\x56",
    (const uint8_t *)"\xee\x93\xa4\xf6\x6f\x8d\x16\xb8\x19\xbb\x9b\xeb\x9f\xfc\xcd\xfc\xdc\x14\x12\xe8\x7f\xee\x6a\x32\x4c\x2a\x99\xa1\xe0\xe6\x71\x48",
#else
    MODEL_BOOTLOADER_KEYS
#endif
};

#define USB_IFACE_NUM 0

typedef enum {
  CONTINUE = 0,
  RETURN = 1,
  SHUTDOWN = 2,
} usb_result_t;

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
#ifdef TREZOR_EMULATOR
      .emu_port = 21324,
#else
      .ep_in = USB_EP_DIR_IN | 0x01,
      .ep_out = USB_EP_DIR_OUT | 0x01,
#endif
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

static usb_result_t bootloader_usb_loop(const vendor_header *const vhdr,
                                        const image_header *const hdr) {
  // if both are NULL, we don't have a firmware installed
  // let's show a webusb landing page in this case
  usb_init_all((vhdr == NULL && hdr == NULL) ? sectrue : secfalse);

  uint8_t buf[USB_PACKET_SIZE];

  for (;;) {
#ifdef TREZOR_EMULATOR
    emulator_poll_events();
#endif
    int r = usb_webusb_read_blocking(USB_IFACE_NUM, buf, USB_PACKET_SIZE,
                                     USB_TIMEOUT);
    if (r != USB_PACKET_SIZE) {
      continue;
    }
    uint16_t msg_id;
    uint32_t msg_size;
    uint32_t response;
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
        response = ui_screen_wipe_confirm();
        if (INPUT_CANCEL == response) {
          send_user_abort(USB_IFACE_NUM, "Wipe cancelled");
          hal_delay(100);
          usb_stop();
          usb_deinit();
          return RETURN;
        }
        ui_screen_wipe();
        r = process_msg_WipeDevice(USB_IFACE_NUM, msg_size, buf);
        if (r < 0) {  // error
          screen_wipe_fail();
          hal_delay(100);
          usb_stop();
          usb_deinit();
          return SHUTDOWN;
        } else {  // success
          screen_wipe_success();
          hal_delay(100);
          usb_stop();
          usb_deinit();
          return SHUTDOWN;
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
          return SHUTDOWN;
        } else if (r == UPLOAD_ERR_USER_ABORT) {
          hal_delay(100);
          usb_stop();
          usb_deinit();
          return RETURN;
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
          ui_screen_boot_empty(true);
          return CONTINUE;
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

secbool check_vendor_header_keys(const vendor_header *const vhdr) {
  return check_vendor_header_sig(vhdr, BOOTLOADER_KEY_M, BOOTLOADER_KEY_N,
                                 BOOTLOADER_KEYS);
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
         "Bootloader downgrade protection");
}

#endif

#ifndef TREZOR_EMULATOR
int main(void) {
  // grab "stay in bootloader" flag as soon as possible
  register uint32_t r11 __asm__("r11");
  volatile uint32_t stay_in_bootloader_flag = r11;
#else
int bootloader_main(void) {
#endif

  random_delays_init();
  // display_init_seq();
#ifdef USE_DMA2D
  dma2d_init();
#endif

  display_reinit();

  mpu_config_bootloader();

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
    firmware_present =
        check_image_contents(hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen,
                             FIRMWARE_SECTORS, FIRMWARE_SECTORS_COUNT);
  }

#if defined TREZOR_MODEL_T
  set_core_clock(CLOCK_180_MHZ);
  display_set_little_endian();
#endif

  ui_screen_boot_empty(false);

#ifdef USE_I2C
  i2c_init();
#endif

#ifdef USE_TOUCH
  touch_power_on();
  touch_init();
#endif

#ifdef USE_BUTTON
  button_init();
#endif

#ifdef USE_CONSUMPTION_MASK
  consumption_mask_init();
#endif

#ifdef USE_RGB_LED
  rgb_led_init();
#endif

  unit_variant_init();

#if PRODUCTION
  check_bootloader_version();
#endif

  // was there reboot with request to stay in bootloader?
  secbool stay_in_bootloader = secfalse;
  if (stay_in_bootloader_flag == STAY_IN_BOOTLOADER_FLAG) {
    stay_in_bootloader = sectrue;
  }

  // delay to detect touch or skip if we know we are staying in bootloader
  // anyway
  uint32_t touched = 0;
#ifdef USE_TOUCH
  if (firmware_present == sectrue && stay_in_bootloader != sectrue) {
    for (int i = 0; i < 100; i++) {
      touched = touch_is_detected() | touch_read();
      if (touched) {
        break;
      }
#ifdef TREZOR_EMULATOR
      hal_delay(25);
#else
      hal_delay(1);
#endif
    }
  }
#elif defined USE_BUTTON
  button_read();
  if (button_state_left() == 1) {
    touched = 1;
  }
#endif

  // start the bootloader if no or broken firmware found ...
  if (firmware_present != sectrue) {
#ifdef TREZOR_EMULATOR
    // wait a bit so that the empty lock icon is visible
    // (on a real device, we are waiting for touch init which takes longer)
    hal_delay(400);
#endif
    // ignore stay in bootloader
    stay_in_bootloader = secfalse;
    touched = false;

    // show intro animation

    ui_set_initial_setup(true);

    ui_screen_welcome_model();
    hal_delay(1000);
    ui_screen_welcome();

    // erase storage
    ensure(flash_erase_sectors(STORAGE_SECTORS, STORAGE_SECTORS_COUNT, NULL),
           NULL);

    // and start the usb loop
    if (bootloader_usb_loop(NULL, NULL) != CONTINUE) {
      return 1;
    }
  }

  // ... or if user touched the screen on start
  // ... or we have stay_in_bootloader flag to force it
  if (touched || stay_in_bootloader == sectrue) {
    ui_set_initial_setup(false);

    screen_t screen = SCREEN_INTRO;

    while (true) {
      bool continue_to_firmware = false;
      uint32_t ui_result = 0;

      switch (screen) {
        case SCREEN_INTRO:
          ui_result = ui_screen_intro(&vhdr, hdr);
          if (ui_result == 1) {
            screen = SCREEN_MENU;
          }
          if (ui_result == 2) {
            screen = SCREEN_WAIT_FOR_HOST;
          }
          break;
        case SCREEN_MENU:
          ui_result = ui_screen_menu();
          if (ui_result == 1) {  // exit menu
            screen = SCREEN_INTRO;
          }
          if (ui_result == 2) {  // reboot
            ui_screen_boot_empty(true);
            continue_to_firmware = true;
          }
          if (ui_result == 3) {  // wipe
            screen = SCREEN_WIPE_CONFIRM;
          }
          break;
        case SCREEN_WIPE_CONFIRM:
          ui_result = screen_wipe_confirm();
          if (ui_result == INPUT_CANCEL) {
            // canceled
            screen = SCREEN_MENU;
          }
          if (ui_result == INPUT_CONFIRM) {
            ui_screen_wipe();
            secbool r = bootloader_WipeDevice();
            if (r != sectrue) {  // error
              screen_wipe_fail();
              return 1;
            } else {  // success
              screen_wipe_success();
              return 1;
            }
          }
          break;
        case SCREEN_WAIT_FOR_HOST:
          screen_connect();
          switch (bootloader_usb_loop(&vhdr, hdr)) {
            case CONTINUE:
              continue_to_firmware = true;
              break;
            case RETURN:
              screen = SCREEN_INTRO;
              break;
            case SHUTDOWN:
              return 1;
              break;
            default:
              break;
          }
          break;
        default:
          break;
      }

      if (continue_to_firmware) {
        break;
      }
    }
  }

  ensure(read_vendor_header((const uint8_t *)FIRMWARE_START, &vhdr),
         "Firmware is corrupted");

  ensure(check_vendor_header_keys(&vhdr), "Firmware is corrupted");

  ensure(check_vendor_header_lock(&vhdr), "Unauthorized vendor keys");

  hdr = read_image_header((const uint8_t *)(FIRMWARE_START + vhdr.hdrlen),
                          FIRMWARE_IMAGE_MAGIC, FIRMWARE_IMAGE_MAXSIZE);

  ensure(hdr == (const image_header *)(FIRMWARE_START + vhdr.hdrlen) ? sectrue
                                                                     : secfalse,
         "Firmware is corrupted");

  ensure(check_image_model(hdr), "Wrong firmware model");

  ensure(check_image_header_sig(hdr, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub),
         "Firmware is corrupted");

  ensure(check_image_contents(hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen,
                              FIRMWARE_SECTORS, FIRMWARE_SECTORS_COUNT),
         "Firmware is corrupted");

  // if all VTRUST flags are unset = ultimate trust => skip the procedure

  if ((vhdr.vtrust & VTRUST_ALL) != VTRUST_ALL) {
    ui_fadeout();
    ui_screen_boot(&vhdr, hdr);
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
    }

    ui_screen_boot_empty(false);
  }

  ensure_compatible_settings();

  // mpu_config_firmware();
  // jump_to_unprivileged(FIRMWARE_START + vhdr.hdrlen + IMAGE_HEADER_SIZE);

  mpu_config_off();
  jump_to(FIRMWARE_START + vhdr.hdrlen + IMAGE_HEADER_SIZE);

  return 0;
}

void HardFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(HF)"); }
