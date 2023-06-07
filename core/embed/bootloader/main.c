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

#include "boot_internal.h"
#include "common.h"
#include "display.h"
#include "flash.h"
#include "image.h"
#include "messages.pb.h"
#include "random_delays.h"
#include "secbool.h"
#include "secret.h"

#ifdef USE_DMA2D
#include "dma2d.h"
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
#ifdef USE_BLE
#include "ble/messages.h"
#include "ble/state.h"
#include "ble_hal.h"
#endif

#include "model.h"
#include "usb.h"
#include "version.h"

#include "bootui.h"
#include "messages.h"
#include "messages.pb.h"
#include "protob_helpers.h"
#include "rust_ui.h"
#include "unit_variant.h"

#ifdef TREZOR_EMULATOR
#include "emulator.h"
#else
#include "compiler_traits.h"
#include "mini_printf.h"
#include "mpu.h"
#include "platform.h"
#endif

#define USB_IFACE_NUM 0

typedef enum {
  SHUTDOWN = 0,
  CONTINUE_TO_FIRMWARE = 0xAABBCCDD,
  RETURN_TO_MENU = 0x55667788,
  NO_RESULT = -1,
} comm_result_t;

volatile secbool dont_optimize_out_true = sectrue;
void failed_jump_to_firmware(void);
volatile void (*firmware_jump_fn)(void) = failed_jump_to_firmware;

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

void stop_comm(void) {
  hal_delay(100);
  usb_stop();
  usb_deinit();
#ifdef USE_BLE
  stop_advertising();
#endif
}

static comm_result_t process_common_messages(uint8_t iface, uint8_t *buf,
                                             const vendor_header *const vhdr,
                                             const image_header *const hdr) {
  uint16_t msg_id;
  uint32_t msg_size;
  uint32_t response;
  int32_t upload_response;
  if (sectrue != msg_parse_header(buf, &msg_id, &msg_size)) {
    // invalid header -> discard
    return NO_RESULT;
  }
  switch (msg_id) {
    case MessageType_MessageType_Initialize:
      process_msg_Initialize(iface, msg_size, buf, vhdr, hdr);
      break;
    case MessageType_MessageType_Ping:
      process_msg_Ping(iface, msg_size, buf);
      break;
    case MessageType_MessageType_WipeDevice:
      response = ui_screen_wipe_confirm();
      if (INPUT_CANCEL == response) {
        send_user_abort(iface, "Wipe cancelled");
        stop_comm();
        return RETURN_TO_MENU;
      }
      ui_screen_wipe();
      upload_response = process_msg_WipeDevice(iface, msg_size, buf);
      if (upload_response < 0) {  // error
        screen_wipe_fail();
        stop_comm();
        return SHUTDOWN;
      } else {  // success
        screen_wipe_success();
        stop_comm();
        return SHUTDOWN;
      }
      break;
    case MessageType_MessageType_FirmwareErase:
      process_msg_FirmwareErase(iface, msg_size, buf);
      break;
    case MessageType_MessageType_FirmwareUpload:
      upload_response = process_msg_FirmwareUpload(iface, msg_size, buf);
      if (upload_response < 0 &&
          upload_response !=
              UPLOAD_ERR_USER_ABORT) {  // error, but not user abort
        if (upload_response == UPLOAD_ERR_BOOTLOADER_LOCKED) {
          ui_screen_install_restricted();
        } else {
          ui_screen_fail();
        }
        stop_comm();
        return SHUTDOWN;
      } else if (upload_response == UPLOAD_ERR_USER_ABORT) {
        stop_comm();
        return RETURN_TO_MENU;
      } else if (upload_response == 0) {  // last chunk received
        ui_screen_install_progress_upload(1000);
        ui_screen_done(4, sectrue);
        ui_screen_done(3, secfalse);
        hal_delay(1000);
        ui_screen_done(2, secfalse);
        hal_delay(1000);
        ui_screen_done(1, secfalse);
        hal_delay(1000);
        stop_comm();
        ui_screen_boot_empty(true);
        return CONTINUE_TO_FIRMWARE;
      }
      break;
    case MessageType_MessageType_GetFeatures:
      process_msg_GetFeatures(iface, msg_size, buf, vhdr, hdr);
      break;
#ifdef USE_OPTIGA
    case MessageType_MessageType_UnlockBootloader:
      response = ui_screen_unlock_bootloader_confirm();
      if (INPUT_CANCEL == response) {
        send_user_abort(USB_IFACE_NUM, "Bootloader unlock cancelled");
        stop_comm();
        return RETURN_TO_MENU;
      }
      process_msg_UnlockBootloader(USB_IFACE_NUM, msg_size, buf);
      screen_unlock_bootloader_success();
      stop_comm();
      return SHUTDOWN;
      break;
#endif
    default:
      process_msg_unknown(iface, msg_size, buf);
      break;
  }

  return NO_RESULT;
}

static comm_result_t bootloader_usb_loop(const vendor_header *const vhdr,
                                         const image_header *const hdr) {
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

    comm_result_t res = process_common_messages(USB_IFACE_NUM, buf, vhdr, hdr);

    if (res != NO_RESULT) {
      return res;
    }
  }
}

#ifdef USE_BLE
static comm_result_t bootloader_ble_loop(const vendor_header *const vhdr,
                                         const image_header *const hdr) {
  ble_comm_start();
  if (!ble_initialize() || !ble_initialized()) {
    error_shutdown("INTERNAL ERROR", "BLE NOT AVAILABLE");
  }

  auto_start_advertising();

  uint8_t buf[BLE_PACKET_SIZE];

  uint8_t active_iface = 0;
  int r = 0;

  for (;;) {
    for (;;) {
      if ((button_read() & (BTN_EVT_DOWN | BTN_POWER)) ==
          (BTN_EVT_DOWN | BTN_POWER)) {
        start_advertising(false);
      }

      r = ble_ext_comm_receive(buf, sizeof(buf));

      if (r == BLE_PACKET_SIZE) {
        active_iface = BLE_EXT_IFACE_NUM;
        break;
      }

      r = ble_int_comm_receive(buf, sizeof(buf));
      if (r != 0) {
        active_iface = BLE_INT_IFACE_NUM;
        break;
      }
    }

    if (active_iface == BLE_INT_IFACE_NUM) {
      for (;;) {
        bool next = false;
        if (r == 0) {
          r = ble_int_comm_receive(buf, sizeof(buf));

          if (r == 0) {
            continue;
          }
        }

        r = 0;

        uint16_t msg_id;
        uint32_t msg_size;
        uint32_t response;
        if (sectrue != msg_parse_header(buf, &msg_id, &msg_size)) {
          // invalid header -> discard
          continue;
        }
        switch (msg_id) {
          case MessageType_MessageType_ComparisonRequest:  // pairing request
            response =
                process_msg_ComparisonRequest(active_iface, msg_size, buf);
            if (response != INPUT_CONFIRM) {
              stop_comm();
              return RETURN_TO_MENU;
            }
            ui_screen_connect();
            next = true;

            break;
          case MessageType_MessageType_PairingRequest:  // pairing request
            response = process_msg_Pairing(active_iface, msg_size, buf);
            if (response != INPUT_CONFIRM) {
              stop_comm();
              return RETURN_TO_MENU;
            }
            ui_screen_connect();
            next = true;

            break;
          case MessageType_MessageType_RepairRequest:  // repairing request
            response = process_msg_Repair(active_iface, msg_size, buf);
            if (response != INPUT_CONFIRM) {
              stop_comm();
              return RETURN_TO_MENU;
            }
            ui_screen_connect();
            break;
          default:
            process_msg_unknown(active_iface, msg_size, buf);
            break;
        }
        if (next) {
          break;
        }
      }
    }

    if (active_iface == BLE_EXT_IFACE_NUM) {
      for (;;) {
        if (r == 0) {
          r = ble_ext_comm_receive(buf, sizeof(buf));

          if (r != BLE_PACKET_SIZE) {
            continue;
          }
        }
        r = 0;

        comm_result_t res =
            process_common_messages(active_iface, buf, vhdr, hdr);

        if (res != NO_RESULT) {
          return res;
        }
      }
    }
  }
}
#endif

static comm_result_t bootloader_comm_select(const vendor_header *const vhdr,
                                            const image_header *const hdr,
                                            bool show_connect_screen) {
  // if both are NULL, we don't have a firmware installed
  // let's show a webusb landing page in this case
  usb_init_all((vhdr == NULL && hdr == NULL) ? sectrue : secfalse);

#ifdef USE_BLE
  bool usb = false;

  for (int i = 0; i < 2000; i++) {
    hal_delay_us(1000);
    if (usb_configured_now() == sectrue) {
      usb = true;
      break;
    }
  }

  if (usb) {
    return bootloader_usb_loop(vhdr, hdr);
  } else {
    usb_stop();
    usb_deinit();
    ui_set_interface(1);
    if (show_connect_screen) {
      ui_screen_connect();
    }
    return bootloader_ble_loop(vhdr, hdr);
  }
#else
  return bootloader_usb_loop(vhdr, hdr);
#endif
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

void failed_jump_to_firmware(void) {
  error_shutdown("INTERNAL ERROR", "(glitch)");
}

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

  ensure(check_image_contents(hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen,
                              &FIRMWARE_AREA),
         "Firmware is corrupted");

#ifdef USE_OPTIGA
  if (((vhdr.vtrust & VTRUST_SECRET) != 0) && (sectrue != secret_wiped())) {
    ui_screen_install_restricted();
    trezor_shutdown();
  }
#endif

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
}

#ifndef TREZOR_EMULATOR
int main(void) {
#else
int bootloader_main(void) {
#endif
  secbool stay_in_bootloader = secfalse;

  random_delays_init();
  // display_init_seq();
#ifdef USE_DMA2D
  dma2d_init();
#endif

  display_reinit();

  ui_screen_boot_empty(false);

  mpu_config_bootloader();

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
    header_present =
        check_image_header_sig(hdr, vhdr.vsig_m, vhdr.vsig_n, vhdr.vpub);
  }

  if (sectrue == header_present) {
    firmware_present = check_image_contents(
        hdr, IMAGE_HEADER_SIZE + vhdr.hdrlen, &FIRMWARE_AREA);
    firmware_present_backup = firmware_present;
  }

#if defined TREZOR_MODEL_T
  set_core_clock(CLOCK_180_MHZ);
  display_set_little_endian();
#endif

#ifdef USE_I2C
  i2c_init();
#endif

#ifdef USE_OPTIGA
  optiga_hal_init();
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
#ifdef USE_BLE
  ble_comm_init();
#endif

  unit_variant_init();

#if PRODUCTION
  check_bootloader_version();
#endif

  switch (g_boot_command) {
    case BOOT_COMMAND_STOP_AND_WAIT:
      // firmare requested to stay in bootloader
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
          ui_set_interface(0);
          switch (bootloader_comm_select(NULL, NULL, false)) {
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
            ui_screen_boot_empty(true);
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
          screen_connect(auto_upgrade == sectrue, 0);
          ui_set_interface(1);
          switch (bootloader_comm_select(&vhdr, hdr, true)) {
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
        ensure(flash_area_erase_bulk(STORAGE_AREAS, STORAGE_AREAS_COUNT, NULL),
               NULL);
      }
      ensure(dont_optimize_out_true *
                 (continue_to_firmware == continue_to_firmware_backup),
             NULL);
      if (sectrue == continue_to_firmware) {
        firmware_jump_fn = real_jump_to_firmware;
        break;
      }
    }
  }

#ifdef USE_BLE
  ble_stop_all_comm();
#endif

  ensure(dont_optimize_out_true * (firmware_present == firmware_present_backup),
         NULL);
  if (sectrue == firmware_present) {
    firmware_jump_fn = real_jump_to_firmware;
  }

  firmware_jump_fn();

  return 0;
}

void HardFault_Handler(void) { error_shutdown("INTERNAL ERROR", "(HF)"); }
