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

#ifdef SYSCALL_DISPATCH

#include <trezor_rtl.h>

#include <io/display.h>
#include <io/usb.h>
#include <io/usb_hid.h>
#include <io/usb_vcp.h>
#include <io/usb_webusb.h>
#include <sec/entropy.h>
#include <sec/rng.h>
#include <sec/secret.h>
#include <sys/bootutils.h>
#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/systask.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <util/fwutils.h>
#include <util/translations.h>
#include <util/unit_properties.h>

#ifdef USE_BUTTON
#include <io/button.h>
#endif

#ifdef USE_HAPTIC
#include <io/haptic.h>
#endif

#ifdef USE_OPTIGA
#include <sec/optiga.h>
#endif

#ifdef USE_RGB_LED
#include <io/rgb_led.h>
#endif

#ifdef USE_SD_CARD
#include <io/sdcard.h>
#endif

#ifdef USE_TOUCH
#include <io/touch.h>
#endif

#include "syscall_internal.h"
#include "syscall_verifiers.h"

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

__attribute((no_stack_protector)) void syscall_handler(uint32_t *args,
                                                       uint32_t syscall) {
  switch (syscall) {
    case SYSCALL_SYSTEM_EXIT: {
      int exit_code = (int)args[0];
      system_exit__verified(exit_code);
    } break;

    case SYSCALL_SYSTEM_EXIT_ERROR: {
      const char *title = (const char *)args[0];
      size_t title_len = (size_t)args[1];
      const char *message = (const char *)args[2];
      size_t message_len = (size_t)args[3];
      const char *footer = (const char *)args[4];
      size_t footer_len = (size_t)args[5];
      system_exit_error__verified(title, title_len, message, message_len,
                                  footer, footer_len);
    } break;

    case SYSCALL_SYSTEM_EXIT_FATAL: {
      const char *message = (const char *)args[0];
      size_t message_len = (size_t)args[1];
      const char *file = (const char *)args[2];
      size_t file_len = (size_t)args[3];
      int line = (int)args[4];
      system_exit_fatal__verified(message, message_len, file, file_len, line);
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

    case SYSCALL_SYSTICK_MS: {
      args[0] = systick_ms();
    } break;

    case SYSCALL_SYSTICK_US_TO_CYCLES: {
      uint64_t us = args[0] + ((uint64_t)args[1] << 32);
      uint64_t cycles = systick_us_to_cycles(us);
      args[0] = cycles & 0xFFFFFFFF;
      args[1] = cycles >> 32;
    } break;

    case SYSCALL_SECURE_SHUTDOWN: {
      secure_shutdown();
    } break;

    case SYSCALL_REBOOT_DEVICE: {
      reboot_device();
    } break;

    case SYSCALL_REBOOT_TO_BOOTLOADER: {
      reboot_to_bootloader();
    } break;

    case SYSCALL_REBOOT_AND_UPGRADE: {
      const uint8_t *hash = (const uint8_t *)args[0];
      reboot_and_upgrade__verified(hash);
    } break;

    case SYSCALL_DISPLAY_SET_BACKLIGHT: {
      int level = (int)args[0];
      args[0] = display_set_backlight(level);
    } break;

    case SYSCALL_DISPLAY_GET_BACKLIGHT: {
      args[0] = display_get_backlight();
    } break;

    case SYSCALL_DISPLAY_SET_ORIENTATION: {
      int angle = (int)args[0];
      args[0] = display_set_orientation(angle);
    } break;

    case SYSCALL_DISPLAY_GET_ORIENTATION: {
      args[0] = display_get_orientation();
    } break;

#if FRAMEBUFFER
    case SYSCALL_DISPLAY_GET_FB_INFO: {
      display_fb_info_t *fb = (display_fb_info_t *)args[0];
      args[0] = (uint32_t)display_get_frame_buffer__verified(fb);
    } break;
#else
    case SYSCALL_DISPLAY_WAIT_FOR_SYNC: {
      display_wait_for_sync();
    } break;
#endif

    case SYSCALL_DISPLAY_FILL: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      display_fill__verified(bb);
    } break;

#ifdef USE_RGB_COLORS
    case SYSCALL_DISPLAY_COPY_RGB565: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      display_copy_rgb565__verified(bb);
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
      const usb_hid_info_t *hid_info = (const usb_hid_info_t *)args[0];
      args[0] = usb_hid_add(hid_info);
    } break;

    case SYSCALL_USB_HID_CAN_READ: {
      uint8_t iface_num = (uint8_t)args[0];
      args[0] = usb_hid_can_read(iface_num);
    } break;

    case SYSCALL_USB_HID_CAN_WRITE: {
      uint8_t iface_num = (uint8_t)args[0];
      args[0] = usb_hid_can_write(iface_num);
    } break;

    case SYSCALL_USB_HID_READ: {
      uint8_t iface_num = (uint8_t)args[0];
      uint8_t *buf = (uint8_t *)args[1];
      uint32_t len = args[2];
      args[0] = usb_hid_read__verified(iface_num, buf, len);
    } break;

    case SYSCALL_USB_HID_WRITE: {
      uint8_t iface_num = (uint8_t)args[0];
      const uint8_t *buf = (const uint8_t *)args[1];
      uint32_t len = args[2];
      args[0] = usb_hid_write__verified(iface_num, buf, len);
    } break;

    case SYSCALL_USB_HID_READ_SELECT: {
      uint32_t timeout = args[0];
      args[0] = usb_hid_read_select(timeout);
    } break;

    case SYSCALL_USB_HID_READ_BLOCKING: {
      uint8_t iface_num = (uint8_t)args[0];
      uint8_t *buf = (uint8_t *)args[1];
      uint32_t len = args[2];
      int timeout = (int)args[3];
      args[0] = usb_hid_read_blocking__verified(iface_num, buf, len, timeout);
    } break;

    case SYSCALL_USB_HID_WRITE_BLOCKING: {
      uint8_t iface_num = (uint8_t)args[0];
      const uint8_t *buf = (const uint8_t *)args[1];
      uint32_t len = args[2];
      int timeout = (int)args[3];
      args[0] = usb_hid_write_blocking__verified(iface_num, buf, len, timeout);
    } break;

    case SYSCALL_USB_VCP_ADD: {
      const usb_vcp_info_t *vcp_info = (const usb_vcp_info_t *)args[0];
      args[0] = usb_vcp_add(vcp_info);
    } break;

    case SYSCALL_USB_VCP_CAN_READ: {
      uint8_t iface_num = (uint8_t)args[0];
      args[0] = usb_vcp_can_read(iface_num);
    } break;

    case SYSCALL_USB_VCP_CAN_WRITE: {
      uint8_t iface_num = (uint8_t)args[0];
      args[0] = usb_vcp_can_write(iface_num);
    } break;

    case SYSCALL_USB_VCP_READ: {
      uint8_t iface_num = (uint8_t)args[0];
      uint8_t *buf = (uint8_t *)args[1];
      uint32_t len = args[2];
      args[0] = usb_vcp_read__verified(iface_num, buf, len);
    } break;

    case SYSCALL_USB_VCP_WRITE: {
      uint8_t iface_num = (uint8_t)args[0];
      const uint8_t *buf = (const uint8_t *)args[1];
      uint32_t len = args[2];
      args[0] = usb_vcp_write__verified(iface_num, buf, len);
    } break;

    case SYSCALL_USB_VCP_READ_BLOCKING: {
      uint8_t iface_num = (uint8_t)args[0];
      uint8_t *buf = (uint8_t *)args[1];
      uint32_t len = args[2];
      int timeout = (int)args[3];
      args[0] = usb_vcp_read_blocking__verified(iface_num, buf, len, timeout);
    } break;

    case SYSCALL_USB_VCP_WRITE_BLOCKING: {
      uint8_t iface_num = (uint8_t)args[0];
      const uint8_t *buf = (const uint8_t *)args[1];
      uint32_t len = args[2];
      int timeout = (int)args[3];
      args[0] = usb_vcp_write_blocking__verified(iface_num, buf, len, timeout);
    } break;

    case SYSCALL_USB_WEBUSB_ADD: {
      const usb_webusb_info_t *webusb_info = (const usb_webusb_info_t *)args[0];
      args[0] = usb_webusb_add(webusb_info);
    } break;

    case SYSCALL_USB_WEBUSB_CAN_READ: {
      uint8_t iface_num = (uint8_t)args[0];
      args[0] = usb_webusb_can_read(iface_num);
    } break;

    case SYSCALL_USB_WEBUSB_CAN_WRITE: {
      uint8_t iface_num = (uint8_t)args[0];
      args[0] = usb_webusb_can_write(iface_num);
    } break;

    case SYSCALL_USB_WEBUSB_READ: {
      uint8_t iface_num = (uint8_t)args[0];
      uint8_t *buf = (uint8_t *)args[1];
      uint32_t len = args[2];
      args[0] = usb_webusb_read__verified(iface_num, buf, len);
    } break;

    case SYSCALL_USB_WEBUSB_WRITE: {
      uint8_t iface_num = (uint8_t)args[0];
      const uint8_t *buf = (const uint8_t *)args[1];
      uint32_t len = args[2];
      args[0] = usb_webusb_write__verified(iface_num, buf, len);
    } break;

    case SYSCALL_USB_WEBUSB_READ_SELECT: {
      uint32_t timeout = args[0];
      args[0] = usb_webusb_read_select(timeout);
    } break;

    case SYSCALL_USB_WEBUSB_READ_BLOCKING: {
      uint8_t iface_num = (uint8_t)args[0];
      uint8_t *buf = (uint8_t *)args[1];
      uint32_t len = args[2];
      int timeout = (int)args[3];
      args[0] =
          usb_webusb_read_blocking__verified(iface_num, buf, len, timeout);
    } break;

    case SYSCALL_USB_WEBUSB_WRITE_BLOCKING: {
      uint8_t iface_num = (uint8_t)args[0];
      const uint8_t *buf = (const uint8_t *)args[1];
      uint32_t len = args[2];
      int timeout = (int)args[3];
      args[0] =
          usb_webusb_write_blocking__verified(iface_num, buf, len, timeout);
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
      uint32_t *dest = (uint32_t *)args[0];
      uint32_t block_num = args[1];
      uint32_t num_blocks = args[2];
      args[0] = sdcard_read_blocks__verified(dest, block_num, num_blocks);
    } break;

    case SYSCALL_SDCARD_WRITE_BLOCKS: {
      const uint32_t *src = (const uint32_t *)args[0];
      uint32_t block_num = args[1];
      uint32_t num_blocks = args[2];
      args[0] = sdcard_write_blocks__verified(src, block_num, num_blocks);
    } break;
#endif

    case SYSCALL_UNIT_PROPERTIES_GET: {
      unit_properties_t *props = (unit_properties_t *)args[0];
      unit_properties_get__verified(props);
    } break;

    case SYSCALL_SECRET_BOOTLOADER_LOCKED: {
      args[0] = secret_bootloader_locked();
    } break;

#ifdef USE_BUTTON
    case SYSCALL_BUTTON_GET_EVENT: {
      args[0] = button_get_event();
    } break;
#endif

#ifdef USE_TOUCH
    case SYSCALL_TOUCH_GET_EVENT: {
      args[0] = touch_get_event();
    } break;
#endif

#ifdef USE_RGB_LED
    case SYSCALL_RGB_LED_SET_COLOR: {
      uint32_t color = args[0];
      rgb_led_set_color(color);
    } break;
#endif

#ifdef USE_HAPTIC
    case SYSCALL_HAPTIC_SET_ENABLED: {
      bool enabled = (args[0] != 0);
      haptic_set_enabled(enabled);
    } break;

    case SYSCALL_HAPTIC_GET_ENABLED: {
      args[0] = haptic_get_enabled();
    } break;

    case SYSCALL_HAPTIC_TEST: {
      uint16_t duration_ms = (uint16_t)args[0];
      args[0] = haptic_test(duration_ms);
    } break;

    case SYSCALL_HAPTIC_PLAY: {
      haptic_effect_t effect = (haptic_effect_t)args[0];
      args[0] = haptic_play(effect);
    } break;

    case SYSCALL_HAPTIC_PLAY_CUSTOM: {
      int8_t amplitude_pct = (int8_t)args[0];
      uint16_t duration_ms = (uint16_t)args[1];
      args[0] = haptic_play_custom(amplitude_pct, duration_ms);
    } break;
#endif

#ifdef USE_OPTIGA
    case SYSCALL_OPTIGA_SIGN: {
      uint8_t index = args[0];
      const uint8_t *digest = (const uint8_t *)args[1];
      size_t digest_size = args[2];
      uint8_t *signature = (uint8_t *)args[3];
      size_t max_sig_size = args[4];
      size_t *sig_size = (size_t *)args[5];
      args[0] = optiga_sign__verified(index, digest, digest_size, signature,
                                      max_sig_size, sig_size);
    } break;

    case SYSCALL_OPTIGA_CERT_SIZE: {
      uint8_t index = args[0];
      size_t *cert_size = (size_t *)args[1];
      args[0] = optiga_cert_size__verified(index, cert_size);
    } break;

    case SYSCALL_OPTIGA_READ_CERT: {
      uint8_t index = args[0];
      uint8_t *cert = (uint8_t *)args[1];
      size_t max_cert_size = args[2];
      size_t *cert_size = (size_t *)args[3];
      args[0] =
          optiga_read_cert__verified(index, cert, max_cert_size, cert_size);
    } break;

    case SYSCALL_OPTIGA_READ_SEC: {
      uint8_t *sec = (uint8_t *)args[0];
      args[0] = optiga_read_sec__verified(sec);
    } break;

    case SYSCALL_OPTIGA_RANDOM_BUFFER: {
      uint8_t *dest = (uint8_t *)args[0];
      size_t size = args[1];
      args[0] = optiga_random_buffer__verified(dest, size);
    } break;

#if PYOPT == 0
    case SYSCALL_OPTIGA_SET_SEC_MAX: {
      optiga_set_sec_max();
    } break;
#endif
#endif

    case SYSCALL_STORAGE_INIT: {
      storage_init_callback = (PIN_UI_WAIT_CALLBACK)args[0];
      const uint8_t *salt = (const uint8_t *)args[1];
      uint16_t salt_len = args[2];
      mpu_reconfig(MPU_MODE_STORAGE);
      storage_init__verified(storage_init_callback_wrapper, salt, salt_len);
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
      args[0] = storage_unlock__verified(pin, pin_len, ext_salt);
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
      args[0] = storage_change_pin__verified(
          oldpin, oldpin_len, newpin, newpin_len, old_ext_salt, new_ext_salt);
    } break;

    case SYSCALL_STORAGE_ENSURE_NOT_WIPE_CODE: {
      const uint8_t *pin = (const uint8_t *)args[0];
      size_t pin_len = args[1];
      mpu_reconfig(MPU_MODE_STORAGE);
      storage_ensure_not_wipe_code__verified(pin, pin_len);
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
      args[0] = storage_change_wipe_code__verified(pin, pin_len, ext_salt,
                                                   wipe_code, wipe_code_len);
    } break;

    case SYSCALL_STORAGE_HAS: {
      uint16_t key = (uint16_t)args[0];
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_has(key);
    } break;

    case SYSCALL_STORAGE_GET: {
      uint16_t key = (uint16_t)args[0];
      void *val = (void *)args[1];
      uint16_t max_len = (uint16_t)args[2];
      uint16_t *len = (uint16_t *)args[3];
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_get__verified(key, val, max_len, len);
    } break;

    case SYSCALL_STORAGE_SET: {
      uint16_t key = (uint16_t)args[0];
      const void *val = (const void *)args[1];
      uint16_t len = (uint16_t)args[2];
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_set__verified(key, val, len);
    } break;

    case SYSCALL_STORAGE_DELETE: {
      uint16_t key = (uint16_t)args[0];
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_delete(key);
    } break;

    case SYSCALL_STORAGE_SET_COUNTER: {
      uint16_t key = (uint16_t)args[0];
      uint32_t count = args[1];
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_set_counter(key, count);
    } break;

    case SYSCALL_STORAGE_NEXT_COUNTER: {
      uint16_t key = (uint16_t)args[0];
      uint32_t *count = (uint32_t *)args[1];
      mpu_reconfig(MPU_MODE_STORAGE);
      args[0] = storage_next_counter__verified(key, count);
    } break;

    case SYSCALL_ENTROPY_GET: {
      uint8_t *buf = (uint8_t *)args[0];
      entropy_get__verified(buf);
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
      char *buff = (char *)args[0];
      size_t buff_size = args[1];
      args[0] = firmware_get_vendor__verified(buff, buff_size);
    } break;

    case SYSCALL_FIRMWARE_CALC_HASH: {
      const uint8_t *challenge = (const uint8_t *)args[0];
      size_t challenge_len = args[1];
      uint8_t *hash = (uint8_t *)args[2];
      size_t hash_len = args[3];
      firmware_hash_callback = (firmware_hash_callback_t)args[4];
      void *callback_context = (void *)args[5];

      args[0] = firmware_calc_hash__verified(
          challenge, challenge_len, hash, hash_len,
          firmware_hash_callback_wrapper, callback_context);
    } break;

    default:
      args[0] = 0xffffffff;
      break;
  }
}

#endif  // SYSCALL_DISPATCH
