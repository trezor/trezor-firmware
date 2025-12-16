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

#ifdef KERNEL
#include <stdint.h>
#include "embed/io/ble/inc/io/ble.h"

#include <trezor_rtl.h>

#include <gfx/dma2d_bitblt.h>
#include <io/display.h>
#include <io/usb.h>
#include <sec/rng.h>
#include <sec/secret.h>
#include <sec/secret_keys.h>
#include <sys/bootutils.h>
#include <sys/irq.h>
#include <sys/notify.h>
#include <sys/sysevent.h>
#include <sys/systask.h>
#include <sys/system.h>
#include <sys/systick.h>
#include <util/fwutils.h>
#include <util/translations.h>
#include <util/unit_properties.h>

#ifdef USE_BLE
#include <io/ble.h>
#endif

#ifdef USE_NRF
#include <io/nrf.h>
#endif

#ifdef USE_BUTTON
#include <io/button.h>
#endif

#ifdef USE_HAPTIC
#include <io/haptic.h>
#endif

#ifdef USE_HW_JPEG_DECODER
#include <gfx/jpegdec.h>
#endif

#ifdef USE_OPTIGA
#include <sec/optiga.h>
#endif

#ifdef USE_POWER_MANAGER
#include <sys/power_manager.h>
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

#if PRODUCTION || BOOTLOADER_QA
#include <util/boot_image.h>
#endif

#include "syscall_context.h"
#include "syscall_internal.h"
#include "syscall_verifiers.h"

__attribute((no_stack_protector)) void syscall_handler(uint32_t *args,
                                                       uint32_t syscall,
                                                       void *applet) {
  syscall_set_context((applet_t *)applet);

  switch (syscall) {
    case SYSCALL_RETURN_FROM_CALLBACK: {
      syscall_get_context()->task.in_callback = false;
      systask_yield_to(systask_kernel());
      break;
    }

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

    case SYSCALL_SYSEVENTS_POLL: {
      const sysevents_t *awaited = (sysevents_t *)args[0];
      sysevents_t *signalled = (sysevents_t *)args[1];
      uint32_t deadline = args[2];
      if (!syscall_get_context()->task.in_callback) {
        sysevents_poll__verified(awaited, signalled, deadline);
      }
    } break;

    case SYSCALL_SYSHANDLE_READ: {
      syshandle_t handle = (syshandle_t)args[0];
      void *buffer = (void *)args[1];
      size_t buffer_size = (size_t)args[2];
      args[0] = syshandle_read__verified(handle, buffer, buffer_size);
    } break;

    case SYSCALL_SYSHANDLE_WRITE: {
      syshandle_t handle = (syshandle_t)args[0];
      const void *data = (const void *)args[1];
      size_t data_size = (size_t)args[2];
      args[0] = syshandle_write__verified(handle, data, data_size);
    } break;

#ifdef USE_DBG_CONSOLE
    case SYSCALL_DBG_CONSOLE_READ: {
      void *buffer = (void *)args[0];
      size_t buffer_size = (size_t)args[1];
      args[0] = dbg_console_read__verified(buffer, buffer_size);
    } break;

    case SYSCALL_DBG_CONSOLE_WRITE: {
      const void *data = (const void *)args[0];
      size_t data_size = (size_t)args[1];
      args[0] = dbg_console_write__verified(data, data_size);
    } break;

    case SYSCALL_SYSLOG_START_RECORD: {
      const log_source_t *source = (const log_source_t *)args[0];
      uint8_t level = (uint8_t)args[1];
      args[0] = syslog_start_record__verified(source, level);
    } break;

    case SYSCALL_SYSLOG_WRITE_CHUNK: {
      const char *text = (const char *)args[0];
      size_t text_len = (size_t)args[1];
      bool end_record = (bool)args[2];
      args[0] = syslog_write_chunk__verified(text, text_len, end_record);
    } break;

    case SYSCALL_SYSLOG_SET_FILTER: {
      const char *filter = (const char *)args[0];
      size_t filter_len = (size_t)args[1];
      args[0] = syslog_set_filter__verified(filter, filter_len);
    } break;

#endif

    case SYSCALL_BOOT_IMAGE_CHECK: {
      const boot_image_t *image = (const boot_image_t *)args[0];
      args[0] = boot_image_check__verified(image);
    } break;

    case SYSCALL_BOOT_IMAGE_REPLACE: {
      const boot_image_t *image = (const boot_image_t *)args[0];
      boot_image_replace__verified(image);
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

    case SYSCALL_NOTIFY_SEND: {
      notification_event_t event = (notification_event_t)args[0];
      notify_send(event);
    } break;

    case SYSCALL_DISPLAY_SET_BACKLIGHT: {
      uint8_t level = (uint8_t)args[0];
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

    case SYSCALL_USB_START: {
      const usb_start_params_t *params = (const usb_start_params_t *)args[0];
      args[0] = usb_start__verified(params);
    } break;

    case SYSCALL_USB_STOP: {
      usb_stop();
    } break;

    case SYSCALL_USB_GET_EVENT: {
      args[0] = usb_get_event();
    } break;

    case SYSCALL_USB_GET_STATE: {
      usb_state_t *state = (usb_state_t *)args[0];
      usb_get_state__verified(state);
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

    case SYSCALL_UNIT_PROPERTIES_GET_SN: {
      uint8_t *device_sn = (uint8_t *)args[0];
      size_t max_device_sn_size = args[1];
      size_t *device_sn_size = (size_t *)args[2];
      args[0] = unit_properties_get_sn__verified(device_sn, max_device_sn_size,
                                                 device_sn_size);
    } break;

#ifdef LOCKABLE_BOOTLOADER
    case SYSCALL_SECRET_BOOTLOADER_LOCKED: {
      args[0] = secret_bootloader_locked();
    } break;
#endif

#ifdef USE_BUTTON
    case SYSCALL_BUTTON_GET_EVENT: {
      button_event_t *event = (button_event_t *)args[0];
      args[0] = button_get_event__verified(event);
    } break;
#endif

#ifdef USE_TOUCH
    case SYSCALL_TOUCH_GET_EVENT: {
      args[0] = touch_get_event();
    } break;
#endif

#ifdef USE_RGB_LED
    case SYSCALL_RGB_LED_SET_ENABLED: {
      bool enabled = (args[0] != 0);
      rgb_led_set_enabled(enabled);
    } break;

    case SYSCALL_RGB_LED_GET_ENABLED: {
      args[0] = rgb_led_get_enabled();
    } break;

    case SYSCALL_RGB_LED_SET_COLOR: {
      uint32_t color = args[0];
      rgb_led_set_color(color);
    } break;

    case SYSCALL_RGB_LED_EFFECT_START: {
      rgb_led_effect_type_t effect_type = (rgb_led_effect_type_t)args[0];
      uint32_t requested_cycles = args[1];
      rgb_led_effect_start(effect_type, requested_cycles);
    } break;

    case SYSCALL_RGB_LED_EFFECT_STOP: {
      rgb_led_effect_stop();
    } break;

    case SYSCALL_RGB_LED_EFFECT_ONGOING: {
      args[0] = rgb_led_effect_ongoing();
    } break;

    case SYSCALL_RGB_LED_EFFECT_GET_TYPE: {
      args[0] = rgb_led_effect_get_type();
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

#if PYOPT == 0
    case SYSCALL_OPTIGA_SET_SEC_MAX: {
      optiga_set_sec_max();
    } break;
#endif
#endif  // USE_OPTIGA

    case SYSCALL_SECRET_KEYS_GET_DELEGATED_IDENTITY_KEY: {
      uint8_t *dest = (uint8_t *)args[0];
      args[0] = secret_key_delegated_identity__verified(dest);
    } break;

    case SYSCALL_STORAGE_SETUP: {
      PIN_UI_WAIT_CALLBACK callback = (PIN_UI_WAIT_CALLBACK)args[0];
      storage_setup__verified(callback);
    } break;

    case SYSCALL_STORAGE_WIPE: {
      storage_wipe();
    } break;

    case SYSCALL_STORAGE_IS_UNLOCKED: {
      args[0] = storage_is_unlocked();
    } break;

    case SYSCALL_STORAGE_LOCK: {
      storage_lock();
    } break;

    case SYSCALL_STORAGE_UNLOCK: {
      const uint8_t *pin = (const uint8_t *)args[0];
      size_t pin_len = args[1];
      const uint8_t *ext_salt = (const uint8_t *)args[2];
      args[0] = storage_unlock__verified(pin, pin_len, ext_salt);
    } break;

    case SYSCALL_STORAGE_HAS_PIN: {
      args[0] = storage_has_pin();
    } break;

    case SYSCALL_STORAGE_PIN_FAILS_INCREASE: {
      args[0] = storage_pin_fails_increase();
    } break;

    case SYSCALL_STORAGE_GET_PIN_REM: {
      args[0] = storage_get_pin_rem();
    } break;

    case SYSCALL_STORAGE_CHANGE_PIN: {
      const uint8_t *oldpin = (const uint8_t *)args[0];
      size_t oldpin_len = args[1];
      const uint8_t *newpin = (const uint8_t *)args[2];
      size_t newpin_len = args[3];
      const uint8_t *old_ext_salt = (const uint8_t *)args[4];
      const uint8_t *new_ext_salt = (const uint8_t *)args[5];
      args[0] = storage_change_pin__verified(
          oldpin, oldpin_len, newpin, newpin_len, old_ext_salt, new_ext_salt);
    } break;

    case SYSCALL_STORAGE_ENSURE_NOT_WIPE_CODE: {
      const uint8_t *pin = (const uint8_t *)args[0];
      size_t pin_len = args[1];
      storage_ensure_not_wipe_code__verified(pin, pin_len);
    } break;

    case SYSCALL_STORAGE_HAS_WIPE_CODE: {
      args[0] = storage_has_wipe_code();
    } break;

    case SYSCALL_STORAGE_CHANGE_WIPE_CODE: {
      const uint8_t *pin = (const uint8_t *)args[0];
      size_t pin_len = args[1];
      const uint8_t *ext_salt = (const uint8_t *)args[2];
      const uint8_t *wipe_code = (const uint8_t *)args[3];
      size_t wipe_code_len = args[4];
      args[0] = storage_change_wipe_code__verified(pin, pin_len, ext_salt,
                                                   wipe_code, wipe_code_len);
    } break;

    case SYSCALL_STORAGE_HAS: {
      uint16_t key = (uint16_t)args[0];
      args[0] = storage_has(key);
    } break;

    case SYSCALL_STORAGE_GET: {
      uint16_t key = (uint16_t)args[0];
      void *val = (void *)args[1];
      uint16_t max_len = (uint16_t)args[2];
      uint16_t *len = (uint16_t *)args[3];
      args[0] = storage_get__verified(key, val, max_len, len);
    } break;

    case SYSCALL_STORAGE_SET: {
      uint16_t key = (uint16_t)args[0];
      const void *val = (const void *)args[1];
      uint16_t len = (uint16_t)args[2];
      args[0] = storage_set__verified(key, val, len);
    } break;

    case SYSCALL_STORAGE_DELETE: {
      uint16_t key = (uint16_t)args[0];
      args[0] = storage_delete(key);
    } break;

    case SYSCALL_STORAGE_SET_COUNTER: {
      uint16_t key = (uint16_t)args[0];
      uint32_t count = args[1];
      args[0] = storage_set_counter(key, count);
    } break;

    case SYSCALL_STORAGE_NEXT_COUNTER: {
      uint16_t key = (uint16_t)args[0];
      uint32_t *count = (uint32_t *)args[1];
      args[0] = storage_next_counter__verified(key, count);
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

    case SYSCALL_RNG_FILL_BUFFER: {
      void *buffer = (void *)args[0];
      size_t buffer_size = (size_t)args[1];
      rng_fill_buffer__verified(buffer, buffer_size);
    } break;

    case SYSCALL_RNG_FILL_BUFFER_STRONG: {
      void *buffer = (void *)args[0];
      size_t buffer_size = (size_t)args[1];
      args[0] = rng_fill_buffer_strong__verified(buffer, buffer_size);
    } break;

    case SYSCALL_FIRMWARE_GET_VENDOR: {
      char *buff = (char *)args[0];
      size_t buff_size = args[1];
      args[0] = firmware_get_vendor__verified(buff, buff_size);
    } break;

    case SYSCALL_FIRMWARE_HASH_START: {
      const uint8_t *challenge = (const uint8_t *)args[0];
      size_t challenge_len = args[1];
      args[0] = firmware_hash_start__verified(challenge, challenge_len);
    } break;

    case SYSCALL_FIRMWARE_HASH_CONTINUE: {
      uint8_t *hash = (uint8_t *)args[0];
      size_t hash_len = args[1];
      args[0] = firmware_hash_continue__verified(hash, hash_len);
    } break;

#ifdef USE_BLE
    case SYSCALL_BLE_START: {
      ble_start();
    } break;

    case SYSCALL_BLE_SWITCH_ON: {
      args[0] = ble_switch_on();
    } break;

    case SYSCALL_BLE_SWITCH_OFF: {
      args[0] = ble_switch_off();
    } break;

    case SYSCALL_BLE_ENTER_PAIRING_MODE: {
      const uint8_t *name = (const uint8_t *)args[0];
      size_t name_len = (size_t)args[1];
      args[0] = ble_enter_pairing_mode__verified(name, name_len);
    } break;

    case SYSCALL_BLE_DISCONNECT: {
      args[0] = ble_disconnect();
    } break;

    case SYSCALL_BLE_ERASE_BONDS: {
      args[0] = ble_erase_bonds();
    } break;

    case SYSCALL_BLE_ALLOW_PAIRING: {
      const uint8_t *code = (const uint8_t *)args[0];
      args[0] = ble_allow_pairing__verified(code);
    } break;

    case SYSCALL_BLE_REJECT_PAIRING: {
      args[0] = ble_reject_pairing();
    } break;

    case SYSCALL_BLE_GET_STATE: {
      ble_state_t *state = (ble_state_t *)args[0];
      ble_get_state__verified(state);
    } break;

    case SYSCALL_BLE_GET_EVENT: {
      ble_event_t *event = (ble_event_t *)args[0];
      args[0] = ble_get_event__verified(event);
    } break;

    case SYSCALL_BLE_CAN_WRITE: {
      args[0] = ble_can_write();
    } break;

    case SYSCALL_BLE_WRITE: {
      uint8_t *data = (uint8_t *)args[0];
      size_t len = args[1];
      args[0] = ble_write__verified(data, len);
    } break;

    case SYSCALL_BLE_CAN_READ: {
      args[0] = ble_can_read();
    } break;

    case SYSCALL_BLE_READ: {
      uint8_t *data = (uint8_t *)args[0];
      size_t len = args[1];
      args[0] = ble_read__verified(data, len);
    } break;

    case SYSCALL_BLE_SET_NAME: {
      const uint8_t *name = (const uint8_t *)args[0];
      size_t len = args[1];
      ble_set_name__verified(name, len);
    } break;

    case SYSCALL_BLE_UNPAIR: {
      const bt_le_addr_t *addr = (const bt_le_addr_t *)args[0];
      args[0] = ble_unpair__verified(addr);
    } break;

    case SYSCALL_BLE_GET_BOND_LIST: {
      bt_le_addr_t *list = (bt_le_addr_t *)args[0];
      size_t list_size = args[1];
      args[0] = ble_get_bond_list__verified(list, list_size);
    } break;

    case SYSCALL_BLE_SET_HIGH_SPEED: {
      bool enable = args[0];
      ble_set_high_speed(enable);
    } break;

    case SYSCALL_BLE_SET_ENABLED: {
      bool enabled = (args[0] != 0);
      ble_set_enabled(enabled);
    } break;

    case SYSCALL_BLE_GET_ENABLED: {
      args[0] = ble_get_enabled();
    } break;

#endif

#ifdef USE_NRF

    case SYSCALL_NRF_UPDATE_REQUIRED: {
      const uint8_t *data = (const uint8_t *)args[0];
      size_t len = args[1];
      args[0] = nrf_update_required__verified(data, len);
    } break;

    case SYSCALL_NRF_UPDATE: {
      const uint8_t *data = (const uint8_t *)args[0];
      size_t len = args[1];
      args[0] = nrf_update__verified(data, len);
    } break;

    case SYSCALL_NRF_GET_VERSION: {
      args[0] = nrf_get_version();
    } break;

    case SYSCALL_NRF_AUTHENTICATE: {
      args[0] = nrf_authenticate();
    } break;

    case SYSCALL_NRF_REBOOT: {
      nrf_reboot();
    } break;

#endif

#ifdef USE_POWER_MANAGER
    case SYSCALL_POWER_MANAGER_SUSPEND: {
      wakeup_flags_t *wakeup_flags = (wakeup_flags_t *)args[0];
      args[0] = pm_suspend__verified(wakeup_flags);
    } break;

    case SYSCALL_POWER_MANAGER_HIBERNATE: {
      args[0] = pm_hibernate();
    } break;

    case SYSCALL_POWER_MANAGER_CHARGING_ENABLE: {
      args[0] = pm_charging_enable();
    } break;

    case SYSCALL_POWER_MANAGER_CHARGING_DISABLE: {
      args[0] = pm_charging_disable();
    } break;

    case SYSCALL_POWER_MANAGER_GET_STATE: {
      pm_state_t *status = (pm_state_t *)args[0];
      args[0] = pm_get_state__verified(status);
    } break;

    case SYSCALL_POWER_MANAGER_GET_EVENTS: {
      pm_event_t *status = (pm_event_t *)args[0];
      args[0] = pm_get_events__verified(status);
    } break;
#endif

#ifdef USE_HW_JPEG_DECODER
    case SYSCALL_JPEGDEC_OPEN: {
      args[0] = jpegdec_open();
    } break;

    case SYSCALL_JPEGDEC_CLOSE: {
      jpegdec_close();
    } break;

    case SYSCALL_JPEGDEC_PROCESS: {
      args[0] = jpegdec_process__verified((jpegdec_input_t *)args[0]);
    } break;

    case SYSCALL_JPEGDEC_GET_INFO: {
      args[0] = jpegdec_get_info__verified((jpegdec_image_t *)args[0]);
      break;
    }

    case SYSCALL_JPEGDEC_GET_SLICE_RGBA8888: {
      args[0] = jpegdec_get_slice_rgba8888__verified(
          (void *)args[0], (jpegdec_slice_t *)args[1]);
      break;
    }

    case SYSCALL_JPEGDEC_GET_SLICE_MONO8: {
      args[0] = jpegdec_get_slice_mono8__verified((void *)args[0],
                                                  (jpegdec_slice_t *)args[1]);
      break;
    }
#endif  // USE_HW_JPEG_DECODER

#ifdef USE_DMA2D
    case SYSCALL_DMA2D_WAIT: {
      dma2d_wait();
    } break;

    case SYSCALL_DMA2D_RGB565_FILL: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      args[0] = dma2d_rgb565_fill__verified(bb);
    } break;

    case SYSCALL_DMA2D_RGB565_COPY_MONO4: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      args[0] = dma2d_rgb565_copy_mono4__verified(bb);
    } break;

    case SYSCALL_DMA2D_RGB565_COPY_RGB565: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      args[0] = dma2d_rgb565_copy_rgb565__verified(bb);
    } break;

    case SYSCALL_DMA2D_RGB565_BLEND_MONO4: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      args[0] = dma2d_rgb565_blend_mono4__verified(bb);
    } break;

    case SYSCALL_DMA2D_RGB565_BLEND_MONO8: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      args[0] = dma2d_rgb565_blend_mono8__verified(bb);
    } break;

    case SYSCALL_DMA2D_RGBA8888_FILL: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      args[0] = dma2d_rgba8888_fill__verified(bb);
    } break;

    case SYSCALL_DMA2D_RGBA8888_COPY_MONO4: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      args[0] = dma2d_rgba8888_copy_mono4__verified(bb);
    } break;

    case SYSCALL_DMA2D_RGBA8888_COPY_RGB565: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      args[0] = dma2d_rgba8888_copy_rgb565__verified(bb);
    } break;

    case SYSCALL_DMA2D_RGBA8888_COPY_RGBA8888: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      args[0] = dma2d_rgba8888_copy_rgba8888__verified(bb);
    } break;

    case SYSCALL_DMA2D_RGBA8888_BLEND_MONO4: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      args[0] = dma2d_rgba8888_blend_mono4__verified(bb);
    } break;

    case SYSCALL_DMA2D_RGBA8888_BLEND_MONO8: {
      const gfx_bitblt_t *bb = (const gfx_bitblt_t *)args[0];
      args[0] = dma2d_rgba8888_blend_mono8__verified(bb);
    } break;
#endif  // USE_DMA2D

#ifdef USE_TROPIC
    case SYSCALL_TROPIC_PING: {
      const uint8_t *msg_out = (const uint8_t *)args[0];
      uint8_t *msg_in = (uint8_t *)args[1];
      uint16_t msg_len = (uint16_t)args[2];
      args[0] = tropic_ping__verified(msg_out, msg_in, msg_len);
    } break;

    case SYSCALL_TROPIC_ECC_KEY_GENERATE: {
      uint16_t slot_index = (uint16_t)args[0];
      args[0] = tropic_ecc_key_generate__verified(slot_index);
    } break;

    case SYSCALL_TROPIC_ECC_SIGN: {
      uint16_t key_slot_index = (uint16_t)args[0];
      const uint8_t *dig = (const uint8_t *)args[1];
      uint16_t dig_len = (uint16_t)args[2];
      uint8_t *sig = (uint8_t *)args[3];
      args[0] = tropic_ecc_sign__verified(key_slot_index, dig, dig_len, sig);
    } break;

    case SYSCALL_TROPIC_DATA_READ: {
      uint16_t udata_slot = (uint16_t)args[0];
      uint8_t *data = (uint8_t *)args[1];
      uint16_t *size = (uint16_t *)args[2];
      args[0] = tropic_data_read__verified(udata_slot, data, size);
    } break;
#endif

    default:
      system_exit_fatal("Invalid syscall", __FILE__, __LINE__);
      break;
  }
}

#endif  // KERNEL
