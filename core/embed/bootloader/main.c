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

#include "boot_args.h"
#include "common.h"
#include "display.h"
#include "display_utils.h"
#include "fault_handlers.h"
#include "flash.h"
#include "flash_otp.h"
#include "image.h"
#include "lowlevel.h"
#include "messages.pb.h"
#include "random_delays.h"
#include "secbool.h"
#include "secret.h"

#ifdef USE_DMA2D
#ifdef NEW_RENDERING
#include "dma2d_bitblt.h"
#else
#include "dma2d.h"
#endif
#endif
#ifdef USE_I2C
#include "i2c.h"
#endif
#ifdef USE_OPTIGA
#include "optiga_hal.h"
#endif
#ifdef USE_TOUCH
#include "touch.h"
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
#ifdef USE_HASH_PROCESSOR
#include "hash_processor.h"
#endif

#include "model.h"
#include "usb.h"
#include "version.h"

#include "bootui.h"
#include "messages.h"
#include "monoctr.h"
#include "rust_ui.h"
#include "unit_variant.h"
#include "version_check.h"

#ifdef TREZOR_EMULATOR
#include "emulator.h"
#else
#include "compiler_traits.h"
#include "mpu.h"
#include "platform.h"
#endif

#define USB_IFACE_NUM 0

typedef enum {
  SHUTDOWN = 0,
  CONTINUE_TO_FIRMWARE = 0xAABBCCDD,
  RETURN_TO_MENU = 0x55667788,
} usb_result_t;

void failed_jump_to_firmware(void);

CONFIDENTIAL volatile secbool dont_optimize_out_true = sectrue;
CONFIDENTIAL volatile void (*firmware_jump_fn)(void) = failed_jump_to_firmware;

static void usb_init_all(secbool usb21_landing) {
  usb_dev_info_t dev_info = {
      .device_class = 0x00,
      .device_subclass = 0x00,
      .device_protocol = 0x00,
      .vendor_id = 0x1209,
      .product_id = 0x53C0,
      .release_num = 0x0200,
      .manufacturer = MODEL_USB_MANUFACTURER,
      .product = MODEL_USB_PRODUCT,
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
      .ep_in = 0x01,
      .ep_out = 0x01,
#endif
      .subclass = 0,
      .protocol = 0,
      .max_packet_len = sizeof(rx_buffer),
      .rx_buffer = rx_buffer,
      .polling_interval = 1,
  };

  ensure(usb_init(&dev_info), NULL);

  ensure(usb_webusb_add(&webusb_info), NULL);

  ensure(usb_start(), NULL);
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
      case MessageType_MessageType_Initialize:
        process_msg_Initialize(USB_IFACE_NUM, msg_size, buf, vhdr, hdr);
        break;
      case MessageType_MessageType_Ping:
        process_msg_Ping(USB_IFACE_NUM, msg_size, buf);
        break;
      case MessageType_MessageType_WipeDevice:
        response = ui_screen_wipe_confirm();
        if (INPUT_CANCEL == response) {
          send_user_abort(USB_IFACE_NUM, "Wipe cancelled");
          hal_delay(100);
          usb_deinit();
          return RETURN_TO_MENU;
        }
        ui_screen_wipe();
        r = process_msg_WipeDevice(USB_IFACE_NUM, msg_size, buf);
        if (r < 0) {  // error
          screen_wipe_fail();
          hal_delay(100);
          usb_deinit();
          return SHUTDOWN;
        } else {  // success
          screen_wipe_success();
          hal_delay(100);
          usb_deinit();
          return SHUTDOWN;
        }
        break;
      case MessageType_MessageType_FirmwareErase:
        process_msg_FirmwareErase(USB_IFACE_NUM, msg_size, buf);
        break;
      case MessageType_MessageType_FirmwareUpload:
        r = process_msg_FirmwareUpload(USB_IFACE_NUM, msg_size, buf);
        if (r < 0 && r != UPLOAD_ERR_USER_ABORT) {  // error, but not user abort
          if (r == UPLOAD_ERR_BOOTLOADER_LOCKED) {
            // This function does not return
            show_install_restricted_screen();
          } else {
            ui_screen_fail();
          }
          usb_deinit();
          return SHUTDOWN;
        } else if (r == UPLOAD_ERR_USER_ABORT) {
          hal_delay(100);
          usb_deinit();
          return RETURN_TO_MENU;
        } else if (r == 0) {  // last chunk received
          ui_screen_install_progress_upload(1000);
          ui_screen_done(4, sectrue);
          ui_screen_done(3, secfalse);
          hal_delay(1000);
          ui_screen_done(2, secfalse);
          hal_delay(1000);
          ui_screen_done(1, secfalse);
          hal_delay(1000);
          usb_deinit();
          return CONTINUE_TO_FIRMWARE;
        }
        break;
      case MessageType_MessageType_GetFeatures:
        process_msg_GetFeatures(USB_IFACE_NUM, msg_size, buf, vhdr, hdr);
        break;
#if defined USE_OPTIGA
      case MessageType_MessageType_UnlockBootloader:
        response = ui_screen_unlock_bootloader_confirm();
        if (INPUT_CANCEL == response) {
          send_user_abort(USB_IFACE_NUM, "Bootloader unlock cancelled");
          hal_delay(100);
          usb_deinit();
          return RETURN_TO_MENU;
        }
        process_msg_UnlockBootloader(USB_IFACE_NUM, msg_size, buf);
        screen_unlock_bootloader_success();
        hal_delay(100);
        usb_deinit();
        return SHUTDOWN;
        break;
#endif
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

void failed_jump_to_firmware(void) { error_shutdown("(glitch)"); }

void real_jump_to_firmware(void) {
  const image_header *hdr = NULL;
  vendor_header vhdr = {0};

  ensure(read_vendor_header((const uint8_t *)FIRMWARE_START, &vhdr),
         "Firmware is corrupted");

  ensure(check_vendor_header_keys(&vhdr), "Firmware is corrupted");

  ensure(check_vendor_header_lock(&vhdr), "Unauthorized vendor keys");

  hdr =
      read_image_header((const uint8_t *)(size_t)(FIRMWARE_START + vhdr.hdrlen),
                        FIRMWARE_IMAGE_MAGIC, FIRMWARE_IMAGE_MAXSIZE);

  ensure(hdr == (const image_header *)(size_t)(FIRMWARE_START + vhdr.hdrlen)
             ? sectrue
             : secfalse,
         "Firmware is corrupted");

  ensure(check_image_model(hdr), "Wrong firmware model");

  ensure(check_image_header_sig(hdr, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub),
         "Firmware is corrupted");

  ensure(check_firmware_min_version(hdr->version),
         "Firmware downgrade protection");
  ensure_firmware_min_version(hdr->version);

  ensure(check_image_contents(hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen,
                              &FIRMWARE_AREA),
         "Firmware is corrupted");

  secret_prepare_fw(
      ((vhdr.vtrust & VTRUST_SECRET_MASK) == VTRUST_SECRET_ALLOW) * sectrue,
      ((vhdr.vtrust & VTRUST_NO_WARNING) == VTRUST_NO_WARNING) * sectrue);

  // if all warnings are disabled in VTRUST flags then skip the procedure
  if ((vhdr.vtrust & VTRUST_NO_WARNING) != VTRUST_NO_WARNING) {
    ui_fadeout();
    ui_screen_boot(&vhdr, hdr, 0);
    ui_fadein();

    // The delay is encoded in bitwise complement form.
    int delay = (vhdr.vtrust & VTRUST_WAIT_MASK) ^ VTRUST_WAIT_MASK;
    if (delay > 1) {
      while (delay > 0) {
        ui_screen_boot(&vhdr, hdr, delay);
        hal_delay(1000);
        delay--;
      }
    } else if (delay == 1) {
      hal_delay(1000);
    }

    if ((vhdr.vtrust & VTRUST_NO_CLICK) == 0) {
      ui_screen_boot(&vhdr, hdr, -1);
      ui_click();
    }

    ui_screen_boot_stage_1(false);
  }

  display_finish_actions();
  ensure_compatible_settings();

  mpu_config_off();
  jump_to(IMAGE_CODE_ALIGN(FIRMWARE_START + vhdr.hdrlen + IMAGE_HEADER_SIZE));
}

#ifdef STM32U5
__attribute__((noreturn)) void jump_to_fw_through_reset(void) {
  display_finish_actions();
  display_fade(display_backlight(-1), 0, 200);

  __disable_irq();
  delete_secrets();
  NVIC_SystemReset();
  for (;;)
    ;
}
#endif

#ifndef TREZOR_EMULATOR
int main(void) {
#else
int bootloader_main(void) {
#endif
  secbool stay_in_bootloader = secfalse;

  random_delays_init();

#if defined TREZOR_MODEL_T
  set_core_clock(CLOCK_180_MHZ);
#endif

#ifdef USE_HASH_PROCESSOR
  hash_processor_init();
#endif

#ifdef USE_I2C
  i2c_init();
#endif

  display_reinit();

#ifdef USE_DMA2D
  dma2d_init();
#endif

  unit_variant_init();

#ifdef USE_TOUCH
#ifdef TREZOR_MODEL_T3T1
  // on T3T1, tester needs to run without touch, so making an exception
  // until unit variant is written in OTP
  if (unit_variant_present()) {
    ensure(touch_init(), "Touch screen panel was not loaded properly.");
  } else {
    touch_init();
  }
#else
  ensure(touch_init(), "Touch screen panel was not loaded properly.");
#endif
#endif

  ui_screen_boot_stage_1(false);

  mpu_config_bootloader();

  fault_handlers_init();

#ifdef TREZOR_EMULATOR
  // wait a bit so that the empty lock icon is visible
  // (on a real device, we are waiting for touch init which takes longer)
  hal_delay(400);
#endif

  const image_header *hdr = NULL;
  vendor_header vhdr;

  // detect whether the device contains a valid firmware
  volatile secbool vhdr_present = secfalse;
  volatile secbool vhdr_keys_ok = secfalse;
  volatile secbool vhdr_lock_ok = secfalse;
  volatile secbool img_hdr_ok = secfalse;
  volatile secbool model_ok = secfalse;
  volatile secbool signatures_ok = secfalse;
  volatile secbool version_ok = secfalse;
  volatile secbool header_present = secfalse;
  volatile secbool firmware_present = secfalse;
  volatile secbool firmware_present_backup = secfalse;
  volatile secbool auto_upgrade = secfalse;

  vhdr_present = read_vendor_header((const uint8_t *)FIRMWARE_START, &vhdr);

  if (sectrue == vhdr_present) {
    vhdr_keys_ok = check_vendor_header_keys(&vhdr);
  }

  if (sectrue == vhdr_keys_ok) {
    vhdr_lock_ok = check_vendor_header_lock(&vhdr);
  }

  if (sectrue == vhdr_lock_ok) {
    hdr = read_image_header(
        (const uint8_t *)(size_t)(FIRMWARE_START + vhdr.hdrlen),
        FIRMWARE_IMAGE_MAGIC, FIRMWARE_IMAGE_MAXSIZE);
    if (hdr == (const image_header *)(size_t)(FIRMWARE_START + vhdr.hdrlen)) {
      img_hdr_ok = sectrue;
    }
  }
  if (sectrue == img_hdr_ok) {
    model_ok = check_image_model(hdr);
  }

  if (sectrue == model_ok) {
    signatures_ok =
        check_image_header_sig(hdr, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub);
  }

  if (sectrue == signatures_ok) {
    version_ok = check_firmware_min_version(hdr->monotonic);
  }

  if (sectrue == version_ok) {
    header_present = version_ok;
  }

  if (sectrue == header_present) {
    ensure_firmware_min_version(hdr->monotonic);
    firmware_present = check_image_contents(
        hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen, &FIRMWARE_AREA);
    firmware_present_backup = firmware_present;
  }

#ifdef USE_OPTIGA
  optiga_hal_init();
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

#if PRODUCTION && !defined STM32U5
  // for STM32U5, this check is moved to boardloader
  ensure_bootloader_min_version();
#endif

  switch (bootargs_get_command()) {
    case BOOT_COMMAND_STOP_AND_WAIT:
      // firmware requested to stay in bootloader
      stay_in_bootloader = sectrue;
      break;
    case BOOT_COMMAND_INSTALL_UPGRADE:
      if (firmware_present == sectrue) {
        // continue without user interaction
        auto_upgrade = sectrue;
      }
      break;
    default:
      break;
  }

  ensure(dont_optimize_out_true * (firmware_present == firmware_present_backup),
         NULL);

  // delay to detect touch or skip if we know we are staying in bootloader
  // anyway
  uint32_t touched = 0;
#ifdef USE_TOUCH
  if (firmware_present == sectrue && stay_in_bootloader != sectrue) {
    // Wait until the touch controller is ready
    // (on hardware this may take a while)
    while (touch_ready() != sectrue) {
      hal_delay(1);
    }
#ifdef TREZOR_EMULATOR
    hal_delay(500);
#endif
    // Give the touch controller time to report events
    // if someone touches the screen
    for (int i = 0; i < 10; i++) {
      if (touch_activity() == sectrue) {
        touched = 1;
        break;
      }
      hal_delay(5);
    }
  }
#elif defined USE_BUTTON
  button_read();
  if (button_state_left() == 1) {
    touched = 1;
  }
#endif

  ensure(dont_optimize_out_true * (firmware_present == firmware_present_backup),
         NULL);

  // start the bootloader ...
  // ... if user touched the screen on start
  // ... or we have stay_in_bootloader flag to force it
  // ... or strict upgrade was confirmed in the firmware (auto_upgrade flag)
  // ... or there is no valid firmware
  if (touched || stay_in_bootloader == sectrue || firmware_present != sectrue ||
      auto_upgrade == sectrue) {
    screen_t screen;
    ui_set_initial_setup(true);
    if (header_present == sectrue) {
      if (auto_upgrade == sectrue) {
        screen = SCREEN_WAIT_FOR_HOST;
      } else {
        ui_set_initial_setup(false);
        screen = SCREEN_INTRO;
      }

    } else {
      screen = SCREEN_WELCOME;

#ifdef STM32U5
      secret_bhk_regenerate();
#endif
      // erase storage
      ensure(flash_area_erase_bulk(STORAGE_AREAS, STORAGE_AREAS_COUNT, NULL),
             NULL);

      // keep the model screen up for a while
#ifndef USE_BACKLIGHT
      hal_delay(1500);
#else
      // backlight fading takes some time so the explicit delay here is
      // shorter
      hal_delay(1000);
#endif
    }

    while (true) {
      volatile secbool continue_to_firmware = secfalse;
      volatile secbool continue_to_firmware_backup = secfalse;
      uint32_t ui_result = 0;

      switch (screen) {
        case SCREEN_WELCOME:

          ui_screen_welcome();

          // and start the usb loop
          switch (bootloader_usb_loop(NULL, NULL)) {
            case CONTINUE_TO_FIRMWARE:
              continue_to_firmware = sectrue;
              continue_to_firmware_backup = sectrue;
              break;
            case RETURN_TO_MENU:
              break;
            default:
            case SHUTDOWN:
              return 1;
              break;
          }
          break;

        case SCREEN_INTRO:
          ui_result = ui_screen_intro(&vhdr, hdr, firmware_present);
          if (ui_result == 1) {
            screen = SCREEN_MENU;
          }
          if (ui_result == 2) {
            screen = SCREEN_WAIT_FOR_HOST;
          }
          break;
        case SCREEN_MENU:
          ui_result = ui_screen_menu(firmware_present);
          if (ui_result == 0xAABBCCDD) {  // exit menu
            screen = SCREEN_INTRO;
          }
          if (ui_result == 0x11223344) {  // reboot
#ifndef STM32U5
            ui_screen_boot_stage_1(true);
#endif
            continue_to_firmware = firmware_present;
            continue_to_firmware_backup = firmware_present_backup;
          }
          if (ui_result == 0x55667788) {  // wipe
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
          screen_connect(auto_upgrade == sectrue);
          switch (bootloader_usb_loop(&vhdr, hdr)) {
            case CONTINUE_TO_FIRMWARE:
              continue_to_firmware = sectrue;
              continue_to_firmware_backup = sectrue;
              break;
            case RETURN_TO_MENU:
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

      if (continue_to_firmware != continue_to_firmware_backup) {
        // erase storage if we saw flips randomly flip, most likely due to
        // glitch

#ifdef STM32U5
        secret_bhk_regenerate();
#endif
        ensure(flash_area_erase_bulk(STORAGE_AREAS, STORAGE_AREAS_COUNT, NULL),
               NULL);
      }
      ensure(dont_optimize_out_true *
                 (continue_to_firmware == continue_to_firmware_backup),
             NULL);
      if (sectrue == continue_to_firmware) {
#ifdef STM32U5
        firmware_jump_fn = jump_to_fw_through_reset;
#else
        ui_screen_boot_stage_1(true);
        firmware_jump_fn = real_jump_to_firmware;
#endif
        break;
      }
    }
  }

  ensure(dont_optimize_out_true * (firmware_present == firmware_present_backup),
         NULL);

#ifdef STM32U5
  if (sectrue == firmware_present &&
      firmware_jump_fn != jump_to_fw_through_reset) {
    firmware_jump_fn = real_jump_to_firmware;
  }
#else
  if (sectrue == firmware_present) {
    firmware_jump_fn = real_jump_to_firmware;
  }
#endif

  firmware_jump_fn();

  return 0;
}
