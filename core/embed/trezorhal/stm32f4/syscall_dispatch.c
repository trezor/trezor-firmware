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

#include STM32_HAL_H

#include "syscall.h"

#include "bootutils.h"
#include "button.h"
#include "display.h"
#include "entropy.h"
#include "fwutils.h"
#include "haptic.h"
#include "hash_processor.h"
#include "irq.h"
#include "mpu.h"
#include "optiga.h"
#include "rng.h"
#include "sdcard.h"
#include "secret.h"
#include "systask.h"
#include "system.h"
#include "systick.h"
#include "touch.h"
#include "translations.h"
#include "unit_variant.h"
#include "usb.h"
#include "usb_hid.h"
#include "usb_vcp.h"
#include "usb_webusb.h"

#ifdef SYSCALL_DISPATCH

static PIN_UI_WAIT_CALLBACK storage_init_callback = NULL;

static secbool storage_init_callback_wrapper(
    uint32_t wait, uint32_t progress, enum storage_ui_message_t message) {
  return (secbool)invoke_app_callback(wait, progress, message,
                                      storage_init_callback);
}

static firmware_hash_callback_t firmware_hash_callback = NULL;

static void firmware_hash_callback_wrapper(void *context, uint32_t progress,
                                           uint32_t total) {
  invoke_app_callback((uint32_t)context, progress, total,
                      firmware_hash_callback);
}

void syscall_handler(uint32_t *args, uint32_t syscall) {
  switch (syscall) {
    case SYSCALL_SYSTEM_EXIT: {
      system_exit((int)args[0]);
    } break;
    case SYSCALL_SYSTEM_EXIT_ERROR: {
      system_exit_error((const char *)args[0], (const char *)args[1],
                        (const char *)args[2]);
    } break;
    case SYSCALL_SYSTEM_EXIT_FATAL: {
      system_exit_fatal((const char *)args[0], (const char *)args[1],
                        (int)args[2]);
    } break;
    case SYSCALL_SYSTICK_CYCLES: {
      uint64_t cycles = systick_cycles();
      args[0] = cycles & 0xFFFFFFFF;
      args[1] = cycles >> 32;
    } break;

    case SYSCALL_SYSTICK_US: {
      uint64_t cycles = systick_us();
      args[0] = cycles & 0xFFFFFFFF;
      args[1] = cycles >> 32;
    } break;

    case SYSCALL_SYSTICK_MS:
      args[0] = systick_ms();
      break;

    case SYSCALL_SYSTICK_US_TO_CYCLES: {
      uint64_t us = args[0] + ((uint64_t)args[1] << 32);
      uint64_t cycles = systick_us_to_cycles(us);
      args[0] = cycles & 0xFFFFFFFF;
      args[1] = cycles >> 32;
    } break;

    case SYSCALL_SECURE_SHUTDOWN:
      secure_shutdown();
      break;
    case SYSCALL_REBOOT:
      reboot();
      break;
    case SYSCALL_REBOOT_TO_BOOTLOADER:
      reboot_to_bootloader();
      break;
    case SYSCALL_REBOOT_AND_UPGRADE:
      reboot_and_upgrade((uint8_t *)args[0]);
      break;

#ifdef STM32U5
    case SYSCALL_SHA256_INIT: {
      hash_sha265_context_t *ctx = (hash_sha265_context_t *)args[0];
      hash_processor_sha256_init(ctx);
    } break;
    case SYSCALL_SHA256_UPDATE: {
      hash_sha265_context_t *ctx = (hash_sha265_context_t *)args[0];
      const uint8_t *data = (const uint8_t *)args[1];
      uint32_t len = args[2];
      hash_processor_sha256_update(ctx, data, len);
    } break;
    case SYSCALL_SHA256_FINAL: {
      hash_sha265_context_t *ctx = (hash_sha265_context_t *)args[0];
      uint8_t *output = (uint8_t *)args[1];
      hash_processor_sha256_final(ctx, output);
    } break;
    case SYSCALL_SHA256_CALC: {
      const uint8_t *data = (const uint8_t *)args[0];
      uint32_t len = args[1];
      uint8_t *hash = (uint8_t *)args[2];
      hash_processor_sha256_calc(data, len, hash);
    } break;
#endif  // STM32U5

    case SYSCALL_DISPLAY_SET_BACKLIGHT: {
      args[0] = display_set_backlight((int)args[0]);
    } break;
    case SYSCALL_DISPLAY_GET_BACKLIGHT: {
      args[0] = display_get_backlight();
    } break;
    case SYSCALL_DISPLAY_SET_ORIENTATION: {
      args[0] = display_set_orientation((int)args[0]);
    } break;
    case SYSCALL_DISPLAY_GET_ORIENTATION: {
      args[0] = display_get_orientation();

    } break;
#if XFRAMEBUFFER
    case SYSCALL_DISPLAY_GET_FB_INFO: {
      display_fb_info_t *info = (display_fb_info_t *)args[0];
      *info = display_get_frame_buffer();
    } break;
#else
    case SYSCALL_DISPLAY_WAIT_FOR_SYNC: {
      display_wait_for_sync();
    } break;
    case SYSCALL_DISPLAY_FILL: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      display_fill(bb);
    } break;
    case SYSCALL_DISPLAY_COPY_RGB565: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      display_copy_rgb565(bb);
    } break;
#endif
    case SYSCALL_DISPLAY_REFRESH: {
      display_refresh();
    } break;
    case SYSCALL_USB_INIT: {
      const usb_dev_info_t *dev_info = (const usb_dev_info_t *)args[0];
      args[0] = usb_init(dev_info);
    } break;
    case SYSCALL_USB_DEINIT: {
      usb_deinit();
    } break;
    case SYSCALL_USB_START: {
      args[0] = usb_start();
    } break;
    case SYSCALL_USB_STOP: {
      usb_stop();
    } break;
    case SYSCALL_USB_CONFIGURED: {
      args[0] = usb_configured();
    } break;
    case SYSCALL_USB_HID_ADD: {
      args[0] = usb_hid_add((const usb_hid_info_t *)args[0]);
    } break;
    case SYSCALL_USB_HID_CAN_READ: {
      args[0] = usb_hid_can_read((uint8_t)args[0]);
    } break;
    case SYSCALL_USB_HID_CAN_WRITE: {
      args[0] = usb_hid_can_write((uint8_t)args[0]);
    } break;
    case SYSCALL_USB_HID_READ: {
      args[0] = usb_hid_read((uint8_t)args[0], (uint8_t *)args[1], args[2]);
    } break;
    case SYSCALL_USB_HID_WRITE: {
      args[0] =
          usb_hid_write((uint8_t)args[0], (const uint8_t *)args[1], args[2]);
    } break;
    case SYSCALL_USB_HID_READ_SELECT: {
      args[0] = usb_hid_read_select((uint32_t)args[0]);
    } break;
    case SYSCALL_USB_HID_READ_BLOCKING: {
      args[0] = usb_hid_read_blocking((uint8_t)args[0], (uint8_t *)args[1],
                                      args[2], (int)args[3]);
    } break;
    case SYSCALL_USB_HID_WRITE_BLOCKING: {
      args[0] = usb_hid_write_blocking(
          (uint8_t)args[0], (const uint8_t *)args[1], args[2], (int)args[3]);
    } break;
    case SYSCALL_USB_VCP_ADD: {
      args[0] = usb_vcp_add((const usb_vcp_info_t *)args[0]);
    } break;
    case SYSCALL_USB_VCP_CAN_READ: {
      args[0] = usb_vcp_can_read((uint8_t)args[0]);
    } break;
    case SYSCALL_USB_VCP_CAN_WRITE: {
      args[0] = usb_vcp_can_write((uint8_t)args[0]);
    } break;
    case SYSCALL_USB_VCP_READ: {
      args[0] = usb_vcp_read((uint8_t)args[0], (uint8_t *)args[1], args[2]);
    } break;
    case SYSCALL_USB_VCP_WRITE: {
      args[0] =
          usb_vcp_write((uint8_t)args[0], (const uint8_t *)args[1], args[2]);
    } break;
    case SYSCALL_USB_VCP_READ_BLOCKING: {
      args[0] = usb_vcp_read_blocking((uint8_t)args[0], (uint8_t *)args[1],
                                      args[2], (int)args[3]);
    } break;
    case SYSCALL_USB_VCP_WRITE_BLOCKING: {
      args[0] = usb_vcp_write_blocking(
          (uint8_t)args[0], (const uint8_t *)args[1], args[2], (int)args[3]);
    } break;
    case SYSCALL_USB_WEBUSB_ADD: {
      args[0] = usb_webusb_add((const usb_webusb_info_t *)args[0]);
    } break;
    case SYSCALL_USB_WEBUSB_CAN_READ: {
      args[0] = usb_webusb_can_read((uint8_t)args[0]);
    } break;
    case SYSCALL_USB_WEBUSB_CAN_WRITE: {
      args[0] = usb_webusb_can_write((uint8_t)args[0]);
    } break;
    case SYSCALL_USB_WEBUSB_READ: {
      args[0] = usb_webusb_read((uint8_t)args[0], (uint8_t *)args[1], args[2]);
    } break;
    case SYSCALL_USB_WEBUSB_WRITE: {
      args[0] =
          usb_webusb_write((uint8_t)args[0], (const uint8_t *)args[1], args[2]);
    } break;
    case SYSCALL_USB_WEBUSB_READ_SELECT: {
      args[0] = usb_webusb_read_select((uint32_t)args[0]);
    } break;
    case SYSCALL_USB_WEBUSB_READ_BLOCKING: {
      args[0] = usb_webusb_read_blocking((uint8_t)args[0], (uint8_t *)args[1],
                                         args[2], (int)args[3]);
    } break;
    case SYSCALL_USB_WEBUSB_WRITE_BLOCKING: {
      args[0] = usb_webusb_write_blocking(
          (uint8_t)args[0], (const uint8_t *)args[1], args[2], (int)args[3]);
    } break;
#ifdef USE_SD_CARD
    case SYSCALL_SDCARD_POWER_ON: {
      args[0] = sdcard_power_on();
    } break;
    case SYSCALL_SDCARD_POWER_OFF: {
      sdcard_power_off();
    } break;
    case SYSCALL_SDCARD_IS_PRESENT: {
      args[0] = sdcard_is_present();
    } break;
    case SYSCALL_SDCARD_GET_CAPACITY: {
      args[0] = sdcard_get_capacity_in_bytes();
    } break;
    case SYSCALL_SDCARD_READ_BLOCKS: {
      args[0] = sdcard_read_blocks((uint32_t *)args[0], args[1], args[2]);
    } break;
    case SYSCALL_SDCARD_WRITE_BLOCKS: {
      args[0] =
          sdcard_write_blocks((const uint32_t *)args[0], args[1], args[2]);
    } break;
#endif

    case SYSCALL_UNIT_VARIANT_PRESENT: {
      args[0] = unit_variant_present();
    } break;
    case SYSCALL_UNIT_VARIANT_GET_COLOR: {
      args[0] = unit_variant_get_color();
    } break;
    case SYSCALL_UNIT_VARIANT_GET_PACKAGING: {
      args[0] = unit_variant_get_packaging();
    } break;
    case SYSCALL_UNIT_VARIANT_GET_BTCONLY: {
      args[0] = unit_variant_get_btconly();
    } break;
    case SYSCALL_UNIT_VARIANT_IS_SD_HOTSWAP_ENABLED: {
      args[0] = unit_variant_is_sd_hotswap_enabled();
    } break;
    case SYSCALL_SECRET_BOOTLOADER_LOCKED: {
      args[0] = secret_bootloader_locked();
    } break;
#ifdef USE_BUTTON
    case SYSCALL_BUTTON_READ: {
      args[0] = button_read();
    } break;
    case SYSCALL_BUTTON_STATE_LEFT: {
      args[0] = button_state_left();
    } break;
    case SYSCALL_BUTTON_STATE_RIGHT: {
      args[0] = button_state_right();
    } break;
#endif
#ifdef USE_TOUCH
    case SYSCALL_TOUCH_GET_EVENT: {
      args[0] = touch_get_event();
    } break;
#endif
#ifdef USE_HAPTIC
    case SYSCALL_HAPTIC_SET_ENABLED: {
      haptic_set_enabled(args[0]);
    } break;
    case SYSCALL_HAPTIC_GET_ENABLED: {
      args[0] = haptic_get_enabled();
    } break;
    case SYSCALL_HAPTIC_TEST: {
      args[0] = haptic_test(args[0]);
    } break;
    case SYSCALL_HAPTIC_PLAY: {
      args[0] = haptic_play(args[0]);
    } break;
    case SYSCALL_HAPTIC_PLAY_CUSTOM: {
      args[0] = haptic_play_custom(args[0], args[1]);
    } break;
#endif

#ifdef USE_OPTIGA
      /*optiga_sign_result optiga_sign(uint8_t index, const uint8_t *digest,
                                           size_t digest_size, uint8_t
         *signature, size_t max_sig_size, size_t *sig_size);

      */
    case SYSCALL_OPTIGA_CERT_SIZE: {
      uint8_t index = args[0];
      size_t *cert_size = (size_t *)args[1];
      args[0] = optiga_cert_size(index, cert_size);
    } break;
    case SYSCALL_OPTIGA_READ_CERT: {
      uint8_t index = args[0];
      uint8_t *cert = (uint8_t *)args[1];
      size_t max_cert_size = args[2];
      size_t *cert_size = (size_t *)args[3];
      args[0] = optiga_read_cert(index, cert, max_cert_size, cert_size);
    } break;
    case SYSCALL_OPTIGA_READ_SEC: {
      uint8_t *sec = (uint8_t *)args[0];
      args[0] = optiga_read_sec(sec);
    } break;
    case SYSCALL_OPTIGA_RANDOM_BUFFER: {
      uint8_t *dest = (uint8_t *)args[0];
      size_t size = args[1];
      args[0] = optiga_random_buffer(dest, size);
    } break;
#endif
    case SYSCALL_STORAGE_INIT: {
      storage_init_callback = (PIN_UI_WAIT_CALLBACK)args[0];
      const uint8_t *salt = (const uint8_t *)args[1];
      uint16_t salt_len = args[2];
      mpu_reconfig(MPU_MODE_STORAGE);
      storage_init(storage_init_callback_wrapper, salt, salt_len);
    } break;
    case SYSCALL_STORAGE_WIPE: {
      mpu_reconfig(MPU_MODE_STORAGE);
      storage_wipe();
    } break;
    case SYSCALL_STORAGE_IS_UNLOCKED: {
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_is_unlocked();
    } break;
    case SYSCALL_STORAGE_LOCK: {
      mpu_reconfig(MPU_MODE_STORAGE);
      storage_lock();
    } break;
    case SYSCALL_STORAGE_UNLOCK: {
      const uint8_t *pin = (const uint8_t *)args[0];
      size_t pin_len = args[1];
      const uint8_t *ext_salt = (const uint8_t *)args[2];
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_unlock(pin, pin_len, ext_salt);
    } break;
    case SYSCALL_STORAGE_HAS_PIN: {
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_has_pin();
    } break;
    case SYSCALL_STORAGE_PIN_FAILS_INCREASE: {
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_pin_fails_increase();
    } break;
    case SYSCALL_STORAGE_GET_PIN_REM: {
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_get_pin_rem();
    } break;
    case SYSCALL_STORAGE_CHANGE_PIN: {
      const uint8_t *oldpin = (const uint8_t *)args[0];
      size_t oldpin_len = args[1];
      const uint8_t *newpin = (const uint8_t *)args[2];
      size_t newpin_len = args[3];
      const uint8_t *old_ext_salt = (const uint8_t *)args[4];
      const uint8_t *new_ext_salt = (const uint8_t *)args[5];
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_change_pin(oldpin, oldpin_len, newpin, newpin_len,
                                   old_ext_salt, new_ext_salt);
    } break;
    case SYSCALL_STORAGE_ENSURE_NOT_WIPE_CODE: {
      const uint8_t *pin = (const uint8_t *)args[0];
      size_t pin_len = args[1];
      mpu_reconfig(MPU_MODE_STORAGE);
      storage_ensure_not_wipe_code(pin, pin_len);
    } break;
    case SYSCALL_STORAGE_HAS_WIPE_CODE: {
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_has_wipe_code();
    } break;
    case SYSCALL_STORAGE_CHANGE_WIPE_CODE: {
      const uint8_t *pin = (const uint8_t *)args[0];
      size_t pin_len = args[1];
      const uint8_t *ext_salt = (const uint8_t *)args[2];
      const uint8_t *wipe_code = (const uint8_t *)args[3];
      size_t wipe_code_len = args[4];
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_change_wipe_code(pin, pin_len, ext_salt, wipe_code,
                                         wipe_code_len);
    } break;
    case SYSCALL_STORAGE_HAS: {
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_has((uint16_t)args[0]);
    } break;

    case SYSCALL_STORAGE_GET: {
      uint16_t key = (uint16_t)args[0];
      void *val = (void *)args[1];
      uint16_t max_len = (uint16_t)args[2];
      uint16_t *len = (uint16_t *)args[3];
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_get(key, val, max_len, len);
    } break;
    case SYSCALL_STORAGE_SET: {
      uint16_t key = (uint16_t)args[0];
      const void *val = (const void *)args[1];
      uint16_t len = (uint16_t)args[2];
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_set(key, val, len);
    } break;
    case SYSCALL_STORAGE_DELETE: {
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_delete((uint16_t)args[0]);
    } break;
    case SYSCALL_STORAGE_SET_COUNTER: {
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_set_counter((uint16_t)args[0], args[1]);
    } break;
    case SYSCALL_STORAGE_NEXT_COUNTER: {
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_next_counter((uint16_t)args[0], (uint32_t *)args[1]);
    } break;
    case SYSCALL_ENTROPY_GET: {
      uint8_t *buf = (uint8_t *)args[0];
      entropy_get(buf);
    } break;
    case SYSCALL_TRANSLATIONS_WRITE: {
      const uint8_t *data = (const uint8_t *)args[0];
      uint32_t offset = args[1];
      uint32_t len = args[2];
      args[0] = translations_write(data, offset, len);
    } break;
    case SYSCALL_TRANSLATIONS_READ: {
      uint32_t *len = (uint32_t *)args[0];
      uint32_t offset = args[1];
      args[0] = (uint32_t)translations_read(len, offset);
    } break;
    case SYSCALL_TRANSLATIONS_ERASE: {
      translations_erase();
    } break;
    case SYSCALL_TRANSLATIONS_AREA_BYTESIZE: {
      args[0] = translations_area_bytesize();
    } break;
    case SYSCALL_RNG_GET: {
      args[0] = rng_get();
    } break;
    case SYSCALL_FIRMWARE_GET_VENDOR: {
      args[0] = firmware_get_vendor((char *)args[0], args[1]);
    } break;
    case SYSCALL_FIRMWARE_CALC_HASH: {
      const uint8_t *challenge = (const uint8_t *)args[0];
      size_t challenge_len = args[1];
      uint8_t *hash = (uint8_t *)args[2];
      size_t hash_len = args[3];
      firmware_hash_callback = (firmware_hash_callback_t)args[4];
      void *callback_context = (void *)args[5];

      args[0] =
          firmware_calc_hash(challenge, challenge_len, hash, hash_len,
                             firmware_hash_callback_wrapper, callback_context);
    } break;
    default:
      args[0] = 0xffffffff;
      break;
  }
}

#endif  // SYSCALL_DISPATCH
