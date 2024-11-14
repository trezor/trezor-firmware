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

#ifndef KERNEL_MODE

#include "syscall_internal.h"

// =============================================================================
// system.h
// =============================================================================

#include <sys/system.h>

void system_exit(int exit_code) {
  syscall_invoke1(exit_code, SYSCALL_SYSTEM_EXIT);
  while (1)
    ;
}

void system_exit_error_ex(const char *title, size_t title_len,
                          const char *message, size_t message_len,
                          const char *footer, size_t footer_len) {
  syscall_invoke6((uint32_t)title, title_len, (uint32_t)message, message_len,
                  (uint32_t)footer, footer_len, SYSCALL_SYSTEM_EXIT_ERROR);
  while (1)
    ;
}

void system_exit_fatal_ex(const char *message, size_t message_len,
                          const char *file, size_t file_len, int line) {
  syscall_invoke5((uint32_t)message, message_len, (uint32_t)file, file_len,
                  line, SYSCALL_SYSTEM_EXIT_FATAL);
  while (1)
    ;
}

// =============================================================================
// systick.h
// =============================================================================

#include <sys/systick.h>

uint64_t __attribute__((no_stack_protector)) systick_cycles(void) {
  return syscall_invoke0_ret64(SYSCALL_SYSTICK_CYCLES);
}

uint64_t systick_us(void) { return syscall_invoke0_ret64(SYSCALL_SYSTICK_US); }

uint32_t systick_ms(void) { return syscall_invoke0(SYSCALL_SYSTICK_MS); }

uint64_t systick_us_to_cycles(uint64_t us) {
  uint32_t arg0 = us & 0xFFFFFFFF;
  uint32_t arg1 = us >> 32;
  return syscall_invoke2_ret64(arg0, arg1, SYSCALL_SYSTICK_US_TO_CYCLES);
}

// =============================================================================
// bootutils.h
// =============================================================================

#include <sys/bootutils.h>

void secure_shutdown(void) {
  syscall_invoke0(SYSCALL_SECURE_SHUTDOWN);
  while (1)
    ;
}

void reboot_to_bootloader(void) {
  syscall_invoke0(SYSCALL_REBOOT_TO_BOOTLOADER);
  while (1)
    ;
}

void reboot_and_upgrade(const uint8_t hash[32]) {
  syscall_invoke1((uint32_t)hash, SYSCALL_REBOOT_AND_UPGRADE);
  while (1)
    ;
}

void reboot_device(void) {
  syscall_invoke0(SYSCALL_REBOOT_DEVICE);
  while (1)
    ;
}

// =============================================================================
// display.h
// =============================================================================

#include <io/display.h>

int display_set_backlight(int level) {
  return (int)syscall_invoke1((uint32_t)level, SYSCALL_DISPLAY_SET_BACKLIGHT);
}

int display_get_backlight(void) {
  return (int)syscall_invoke0(SYSCALL_DISPLAY_GET_BACKLIGHT);
}

int display_set_orientation(int angle) {
  return (int)syscall_invoke1((uint32_t)angle, SYSCALL_DISPLAY_SET_ORIENTATION);
}

int display_get_orientation(void) {
  return (int)syscall_invoke0(SYSCALL_DISPLAY_GET_ORIENTATION);
}

#ifdef FRAMEBUFFER

bool display_get_frame_buffer(display_fb_info_t *fb) {
  return (bool)syscall_invoke1((uint32_t)fb, SYSCALL_DISPLAY_GET_FB_INFO);
}

#else  // FRAMEBUFFER

void display_wait_for_sync(void) {
  syscall_invoke0(SYSCALL_DISPLAY_WAIT_FOR_SYNC);
}

#endif

void display_fill(const gfx_bitblt_t *bb) {
  syscall_invoke1((uint32_t)bb, SYSCALL_DISPLAY_FILL);
}

void display_copy_rgb565(const gfx_bitblt_t *bb) {
  syscall_invoke1((uint32_t)bb, SYSCALL_DISPLAY_COPY_RGB565);
}

void display_refresh(void) { syscall_invoke0(SYSCALL_DISPLAY_REFRESH); }

// =============================================================================
// usb.h
// =============================================================================

#include <io/usb.h>

secbool usb_init(const usb_dev_info_t *dev_info) {
  return (secbool)syscall_invoke1((uint32_t)dev_info, SYSCALL_USB_INIT);
}

void usb_deinit(void) { syscall_invoke0(SYSCALL_USB_DEINIT); }

secbool usb_start(void) { return (secbool)syscall_invoke0(SYSCALL_USB_START); }

void usb_stop(void) { syscall_invoke0(SYSCALL_USB_STOP); }

secbool usb_configured(void) {
  return (secbool)syscall_invoke0(SYSCALL_USB_CONFIGURED);
}

// =============================================================================
// usb_hid.h
// =============================================================================

#include <io/usb_hid.h>

secbool usb_hid_add(const usb_hid_info_t *hid_info) {
  return (secbool)syscall_invoke1((uint32_t)hid_info, SYSCALL_USB_HID_ADD);
}

secbool usb_hid_can_read(uint8_t iface_num) {
  return (secbool)syscall_invoke1((uint32_t)iface_num,
                                  SYSCALL_USB_HID_CAN_READ);
}

secbool usb_hid_can_write(uint8_t iface_num) {
  return (secbool)syscall_invoke1((uint32_t)iface_num,
                                  SYSCALL_USB_HID_CAN_WRITE);
}

int usb_hid_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
  return (int)syscall_invoke3((uint32_t)iface_num, (uint32_t)buf, len,
                              SYSCALL_USB_HID_READ);
}

int usb_hid_write(uint8_t iface_num, const uint8_t *buf, uint32_t len) {
  return (int)syscall_invoke3((uint32_t)iface_num, (uint32_t)buf, len,
                              SYSCALL_USB_HID_WRITE);
}

int usb_hid_read_select(uint32_t timeout) {
  return (int)syscall_invoke1(timeout, SYSCALL_USB_HID_READ_SELECT);
}

int usb_hid_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len,
                          int timeout) {
  return (int)syscall_invoke4((uint32_t)iface_num, (uint32_t)buf, len, timeout,
                              SYSCALL_USB_HID_READ_BLOCKING);
}

int usb_hid_write_blocking(uint8_t iface_num, const uint8_t *buf, uint32_t len,
                           int timeout) {
  return (int)syscall_invoke4((uint32_t)iface_num, (uint32_t)buf, len, timeout,
                              SYSCALL_USB_HID_WRITE_BLOCKING);
}

// =============================================================================
// usb_vcp.h
// =============================================================================

#include <io/usb_vcp.h>

secbool usb_vcp_add(const usb_vcp_info_t *vcp_info) {
  return (secbool)syscall_invoke1((uint32_t)vcp_info, SYSCALL_USB_VCP_ADD);
}

secbool usb_vcp_can_read(uint8_t iface_num) {
  return (secbool)syscall_invoke1((uint32_t)iface_num,
                                  SYSCALL_USB_VCP_CAN_READ);
}

secbool usb_vcp_can_write(uint8_t iface_num) {
  return (secbool)syscall_invoke1((uint32_t)iface_num,
                                  SYSCALL_USB_VCP_CAN_WRITE);
}

int usb_vcp_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
  return (int)syscall_invoke3((uint32_t)iface_num, (uint32_t)buf, len,
                              SYSCALL_USB_VCP_READ);
}

int usb_vcp_write(uint8_t iface_num, const uint8_t *buf, uint32_t len) {
  return (int)syscall_invoke3((uint32_t)iface_num, (uint32_t)buf, len,
                              SYSCALL_USB_VCP_WRITE);
}

int usb_vcp_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len,
                          int timeout) {
  return (int)syscall_invoke4((uint32_t)iface_num, (uint32_t)buf, len, timeout,
                              SYSCALL_USB_VCP_READ_BLOCKING);
}

int usb_vcp_write_blocking(uint8_t iface_num, const uint8_t *buf, uint32_t len,
                           int timeout) {
  return (int)syscall_invoke4((uint32_t)iface_num, (uint32_t)buf, len, timeout,
                              SYSCALL_USB_VCP_WRITE_BLOCKING);
}

// =============================================================================
// usb_webusb.h
// =============================================================================

#include <io/usb_webusb.h>

secbool usb_webusb_add(const usb_webusb_info_t *webusb_info) {
  return (secbool)syscall_invoke1((uint32_t)webusb_info,
                                  SYSCALL_USB_WEBUSB_ADD);
}

secbool usb_webusb_can_read(uint8_t iface_num) {
  return (secbool)syscall_invoke1((uint32_t)iface_num,
                                  SYSCALL_USB_WEBUSB_CAN_READ);
}

secbool usb_webusb_can_write(uint8_t iface_num) {
  return (secbool)syscall_invoke1((uint32_t)iface_num,
                                  SYSCALL_USB_WEBUSB_CAN_WRITE);
}

int usb_webusb_read(uint8_t iface_num, uint8_t *buf, uint32_t len) {
  return (int)syscall_invoke3((uint32_t)iface_num, (uint32_t)buf, len,
                              SYSCALL_USB_WEBUSB_READ);
}

int usb_webusb_write(uint8_t iface_num, const uint8_t *buf, uint32_t len) {
  return (int)syscall_invoke3((uint32_t)iface_num, (uint32_t)buf, len,
                              SYSCALL_USB_WEBUSB_WRITE);
}

int usb_webusb_read_select(uint32_t timeout) {
  return (int)syscall_invoke1(timeout, SYSCALL_USB_WEBUSB_READ_SELECT);
}

int usb_webusb_read_blocking(uint8_t iface_num, uint8_t *buf, uint32_t len,
                             int timeout) {
  return (int)syscall_invoke4((uint32_t)iface_num, (uint32_t)buf, len, timeout,
                              SYSCALL_USB_WEBUSB_READ_BLOCKING);
}

int usb_webusb_write_blocking(uint8_t iface_num, const uint8_t *buf,
                              uint32_t len, int timeout) {
  return (int)syscall_invoke4((uint32_t)iface_num, (uint32_t)buf, len, timeout,
                              SYSCALL_USB_WEBUSB_WRITE_BLOCKING);
}

// =============================================================================
// sdcard.h
// =============================================================================

#ifdef USE_SD_CARD

#include <io/sdcard.h>

secbool sdcard_power_on(void) {
  return (secbool)syscall_invoke0(SYSCALL_SDCARD_POWER_ON);
}

void sdcard_power_off(void) { syscall_invoke0(SYSCALL_SDCARD_POWER_OFF); }

secbool sdcard_is_present(void) {
  return (secbool)syscall_invoke0(SYSCALL_SDCARD_IS_PRESENT);
}

uint64_t sdcard_get_capacity_in_bytes(void) {
  return syscall_invoke0_ret64(SYSCALL_SDCARD_GET_CAPACITY);
}

secbool __wur sdcard_read_blocks(uint32_t *dest, uint32_t block_num,
                                 uint32_t num_blocks) {
  return (secbool)syscall_invoke3((uint32_t)dest, block_num, num_blocks,
                                  SYSCALL_SDCARD_READ_BLOCKS);
}

secbool __wur sdcard_write_blocks(const uint32_t *src, uint32_t block_num,
                                  uint32_t num_blocks) {
  return (secbool)syscall_invoke3((uint32_t)src, block_num, num_blocks,
                                  SYSCALL_SDCARD_WRITE_BLOCKS);
}

#endif  // USE_SD_CARD

// =============================================================================
// unit_properties.h
// =============================================================================

#include <util/unit_properties.h>

void unit_properties_get(unit_properties_t *props) {
  syscall_invoke1((uint32_t)props, SYSCALL_UNIT_PROPERTIES_GET);
}

// =============================================================================
// secret.h
// =============================================================================

#include <sec/secret.h>

secbool secret_bootloader_locked(void) {
  return (secbool)syscall_invoke0(SYSCALL_SECRET_BOOTLOADER_LOCKED);
}

// =============================================================================
// button.h
// =============================================================================

#ifdef USE_BUTTON

#include <io/button.h>

uint32_t button_get_event(void) {
  return syscall_invoke0(SYSCALL_BUTTON_GET_EVENT);
}

#endif

// =============================================================================
// touch.h
// =============================================================================

#ifdef USE_TOUCH

#include <io/touch.h>

uint32_t touch_get_event(void) {
  return syscall_invoke0(SYSCALL_TOUCH_GET_EVENT);
}

#endif

// =============================================================================
// rgb_led.h
// =============================================================================

#ifdef USE_RGB_LED

#include <io/rgb_led.h>
void rgb_led_set_color(uint32_t color) {
  syscall_invoke1(color, SYSCALL_RGB_LED_SET_COLOR);
}

#endif

// =============================================================================
// haptic.h
// =============================================================================

#ifdef USE_HAPTIC

#include <io/haptic.h>

void haptic_set_enabled(bool enabled) {
  syscall_invoke1((uint32_t)enabled, SYSCALL_HAPTIC_SET_ENABLED);
}

bool haptic_get_enabled(void) {
  return (bool)syscall_invoke0(SYSCALL_HAPTIC_GET_ENABLED);
}

bool haptic_test(uint16_t duration_ms) {
  return (bool)syscall_invoke1(duration_ms, SYSCALL_HAPTIC_TEST);
}

bool haptic_play(haptic_effect_t effect) {
  return (bool)syscall_invoke1((uint32_t)effect, SYSCALL_HAPTIC_PLAY);
}

bool haptic_play_custom(int8_t amplitude_pct, uint16_t duration_ms) {
  return (bool)syscall_invoke2((uint32_t)amplitude_pct, duration_ms,
                               SYSCALL_HAPTIC_PLAY_CUSTOM);
}

#endif  // USE_HAPTIC

// =============================================================================
// optiga.h
// =============================================================================

#ifdef USE_OPTIGA

#include <sec/optiga.h>

optiga_sign_result optiga_sign(uint8_t index, const uint8_t *digest,
                               size_t digest_size, uint8_t *signature,
                               size_t max_sig_size, size_t *sig_size) {
  return (optiga_sign_result)syscall_invoke6(
      index, (uint32_t)digest, digest_size, (uint32_t)signature, max_sig_size,
      (uint32_t)sig_size, SYSCALL_OPTIGA_SIGN);
}

bool optiga_cert_size(uint8_t index, size_t *cert_size) {
  return (bool)syscall_invoke2(index, (uint32_t)cert_size,
                               SYSCALL_OPTIGA_CERT_SIZE);
}

bool optiga_read_cert(uint8_t index, uint8_t *cert, size_t max_cert_size,
                      size_t *cert_size) {
  return (bool)syscall_invoke4(index, (uint32_t)cert, max_cert_size,
                               (uint32_t)cert_size, SYSCALL_OPTIGA_READ_CERT);
}

bool optiga_read_sec(uint8_t *sec) {
  return (bool)syscall_invoke1((uint32_t)sec, SYSCALL_OPTIGA_READ_SEC);
}

bool optiga_random_buffer(uint8_t *dest, size_t size) {
  return (bool)syscall_invoke2((uint32_t)dest, size,
                               SYSCALL_OPTIGA_RANDOM_BUFFER);
}

#if PYOPT == 0
void optiga_set_sec_max(void) { syscall_invoke0(SYSCALL_OPTIGA_SET_SEC_MAX); }

#endif

#endif  // USE_OPTIGA

// =============================================================================
// storage.h
// =============================================================================

#include "storage.h"

static PIN_UI_WAIT_CALLBACK storage_init_callback = NULL;

static void storage_init_callback_wrapper(uint32_t wait, uint32_t progress,
                                          enum storage_ui_message_t message) {
  secbool retval = storage_init_callback(wait, progress, message);
  syscall_return_from_callback(retval);
}

void storage_init(PIN_UI_WAIT_CALLBACK callback, const uint8_t *salt,
                  const uint16_t salt_len) {
  storage_init_callback = callback;

  syscall_invoke3((uint32_t)storage_init_callback_wrapper, (uint32_t)salt,
                  salt_len, SYSCALL_STORAGE_INIT);
}

void storage_wipe(void) { syscall_invoke0(SYSCALL_STORAGE_WIPE); }
secbool storage_is_unlocked(void) {
  return (secbool)syscall_invoke0(SYSCALL_STORAGE_IS_UNLOCKED);
}

void storage_lock(void) { syscall_invoke0(SYSCALL_STORAGE_LOCK); }

secbool storage_unlock(const uint8_t *pin, size_t pin_len,
                       const uint8_t *ext_salt) {
  return (secbool)syscall_invoke3((uint32_t)pin, pin_len, (uint32_t)ext_salt,
                                  SYSCALL_STORAGE_UNLOCK);
}

secbool storage_has_pin(void) {
  return (secbool)syscall_invoke0(SYSCALL_STORAGE_HAS_PIN);
}
secbool storage_pin_fails_increase(void) {
  return (secbool)syscall_invoke0(SYSCALL_STORAGE_PIN_FAILS_INCREASE);
}

uint32_t storage_get_pin_rem(void) {
  return syscall_invoke0(SYSCALL_STORAGE_GET_PIN_REM);
}

secbool storage_change_pin(const uint8_t *oldpin, size_t oldpin_len,
                           const uint8_t *newpin, size_t newpin_len,
                           const uint8_t *old_ext_salt,
                           const uint8_t *new_ext_salt) {
  return (secbool)syscall_invoke6(
      (uint32_t)oldpin, oldpin_len, (uint32_t)newpin, newpin_len,
      (uint32_t)old_ext_salt, (uint32_t)new_ext_salt,
      SYSCALL_STORAGE_CHANGE_PIN);
}

void storage_ensure_not_wipe_code(const uint8_t *pin, size_t pin_len) {
  syscall_invoke2((uint32_t)pin, pin_len, SYSCALL_STORAGE_ENSURE_NOT_WIPE_CODE);
}

secbool storage_has_wipe_code(void) {
  return (secbool)syscall_invoke0(SYSCALL_STORAGE_HAS_WIPE_CODE);
}

secbool storage_change_wipe_code(const uint8_t *pin, size_t pin_len,
                                 const uint8_t *ext_salt,
                                 const uint8_t *wipe_code,
                                 size_t wipe_code_len) {
  return (secbool)syscall_invoke5((uint32_t)pin, pin_len, (uint32_t)ext_salt,
                                  (uint32_t)wipe_code, wipe_code_len,
                                  SYSCALL_STORAGE_CHANGE_WIPE_CODE);
}

secbool storage_has(const uint16_t key) {
  return (secbool)syscall_invoke1(key, SYSCALL_STORAGE_HAS);
}

secbool storage_get(const uint16_t key, void *val, const uint16_t max_len,
                    uint16_t *len) {
  return (secbool)syscall_invoke4(key, (uint32_t)val, max_len, (uint32_t)len,
                                  SYSCALL_STORAGE_GET);
}

secbool storage_set(const uint16_t key, const void *val, const uint16_t len) {
  return (secbool)syscall_invoke3(key, (uint32_t)val, len, SYSCALL_STORAGE_SET);
}

secbool storage_delete(const uint16_t key) {
  return (secbool)syscall_invoke1(key, SYSCALL_STORAGE_DELETE);
}

secbool storage_set_counter(const uint16_t key, const uint32_t count) {
  return (secbool)syscall_invoke2(key, count, SYSCALL_STORAGE_SET_COUNTER);
}

secbool storage_next_counter(const uint16_t key, uint32_t *count) {
  return (secbool)syscall_invoke2(key, (uint32_t)count,
                                  SYSCALL_STORAGE_NEXT_COUNTER);
}

// =============================================================================
// entropy.h
// =============================================================================

void entropy_get(uint8_t *buf) {
  syscall_invoke1((uint32_t)buf, SYSCALL_ENTROPY_GET);
}

// =============================================================================
// translations.h
// =============================================================================

#include <util/translations.h>

bool translations_write(const uint8_t *data, uint32_t offset, uint32_t len) {
  return (bool)syscall_invoke3((uint32_t)data, offset, len,
                               SYSCALL_TRANSLATIONS_WRITE);
}

const uint8_t *translations_read(uint32_t *len, uint32_t offset) {
  return (const uint8_t *)syscall_invoke2((uint32_t)len, offset,
                                          SYSCALL_TRANSLATIONS_READ);
}

void translations_erase(void) { syscall_invoke0(SYSCALL_TRANSLATIONS_ERASE); }

uint32_t translations_area_bytesize(void) {
  return syscall_invoke0(SYSCALL_TRANSLATIONS_AREA_BYTESIZE);
}

// =============================================================================
// rng.h
// =============================================================================

#include <sec/rng.h>

uint32_t rng_get(void) { return syscall_invoke0(SYSCALL_RNG_GET); }

// =============================================================================
// fwutils.h
// =============================================================================

#include <util/fwutils.h>

secbool firmware_get_vendor(char *buff, size_t buff_size) {
  return syscall_invoke2((uint32_t)buff, buff_size,
                         SYSCALL_FIRMWARE_GET_VENDOR);
}

static firmware_hash_callback_t firmware_hash_callback = NULL;

static void firmware_hash_callback_wrapper(void *context, uint32_t progress,
                                           uint32_t total) {
  firmware_hash_callback(context, progress, total);
  syscall_return_from_callback(0);
}

secbool firmware_calc_hash(const uint8_t *challenge, size_t challenge_len,
                           uint8_t *hash, size_t hash_len,
                           firmware_hash_callback_t callback,
                           void *callback_context) {
  firmware_hash_callback = callback;

  return syscall_invoke6((uint32_t)challenge, challenge_len, (uint32_t)hash,
                         hash_len, (uint32_t)firmware_hash_callback_wrapper,
                         (uint32_t)callback_context,
                         SYSCALL_FIRMWARE_CALC_HASH);
}

#endif  // KERNEL_MODE
