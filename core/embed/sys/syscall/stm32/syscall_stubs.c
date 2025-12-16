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

#pragma GCC optimize("no-stack-protector")

#include <trezor_types.h>

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
// sysevent.h
// =============================================================================

#include <sys/sysevent.h>

void sysevents_poll(const sysevents_t *awaited, sysevents_t *signalled,
                    uint32_t deadline) {
  syscall_invoke3((uint32_t)awaited, (uint32_t)signalled, deadline,
                  SYSCALL_SYSEVENTS_POLL);
}

ssize_t syshandle_read(syshandle_t handle, void *buffer, size_t buffer_size) {
  return syscall_invoke3((uint32_t)handle, (uint32_t)buffer, buffer_size,
                         SYSCALL_SYSHANDLE_READ);
}

ssize_t syshandle_write(syshandle_t handle, const void *data,
                        size_t data_size) {
  return syscall_invoke3((uint32_t)handle, (uint32_t)data, data_size,
                         SYSCALL_SYSHANDLE_WRITE);
}

// =============================================================================
// dbg_console.h
// =============================================================================

#ifdef USE_DBG_CONSOLE

ssize_t dbg_console_read(void *buffer, size_t buffer_size) {
  return syscall_invoke2((uint32_t)buffer, buffer_size,
                         SYSCALL_DBG_CONSOLE_READ);
}

ssize_t dbg_console_write(const void *data, size_t data_size) {
  return syscall_invoke2((uint32_t)data, data_size, SYSCALL_DBG_CONSOLE_WRITE);
}

#endif  // USE_DBG_CONSOLE

// =============================================================================
// logging.h
// =============================================================================

#ifdef USE_DBG_CONSOLE

#include <rtl/logging.h>

bool syslog_start_record(const log_source_t *source, log_level_t level) {
  return (bool)syscall_invoke2((uint32_t)source, level,
                               SYSCALL_SYSLOG_START_RECORD);
}

ssize_t syslog_write_chunk(const char *text, size_t text_len, bool end_record) {
  return (ssize_t)syscall_invoke3((uint32_t)text, text_len, end_record,
                                  SYSCALL_SYSLOG_WRITE_CHUNK);
}

bool syslog_set_filter(const char *filter, size_t filter_len) {
  return (bool)syscall_invoke2((uint32_t)filter, filter_len,
                               SYSCALL_SYSLOG_SET_FILTER);
}

#endif

// =============================================================================
// boot_image.h
// =============================================================================

#include <util/boot_image.h>

bool boot_image_check(const boot_image_t *image) {
  return (bool)syscall_invoke1((uint32_t)image, SYSCALL_BOOT_IMAGE_CHECK);
}

void boot_image_replace(const boot_image_t *image) {
  syscall_invoke1((uint32_t)image, SYSCALL_BOOT_IMAGE_REPLACE);
}

// =============================================================================
// bootutils.h
// =============================================================================

#include <sys/bootutils.h>

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
// notify.h
// =============================================================================

#include <sys/notify.h>

void notify_send(notification_event_t event) {
  syscall_invoke1((uint32_t)event, SYSCALL_NOTIFY_SEND);
}

// =============================================================================
// display.h
// =============================================================================

#include <io/display.h>

bool display_set_backlight(uint8_t level) {
  return (bool)syscall_invoke1((uint32_t)level, SYSCALL_DISPLAY_SET_BACKLIGHT);
}

uint8_t display_get_backlight(void) {
  return (uint8_t)syscall_invoke0(SYSCALL_DISPLAY_GET_BACKLIGHT);
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

secbool usb_start(const usb_start_params_t *params) {
  return (secbool)syscall_invoke1((uint32_t)params, SYSCALL_USB_START);
}

void usb_stop(void) { syscall_invoke0(SYSCALL_USB_STOP); }

usb_event_t usb_get_event(void) {
  return (usb_event_t)syscall_invoke0(SYSCALL_USB_GET_EVENT);
}

void usb_get_state(usb_state_t *state) {
  syscall_invoke1((uint32_t)state, SYSCALL_USB_GET_STATE);
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

bool unit_properties_get_sn(uint8_t *device_sn, size_t max_device_sn_size,
                            size_t *device_sn_size) {
  return (bool)syscall_invoke3((uint32_t)device_sn, max_device_sn_size,
                               (uint32_t)device_sn_size,
                               SYSCALL_UNIT_PROPERTIES_GET_SN);
}

// =============================================================================
// secret.h
// =============================================================================

#ifdef LOCKABLE_BOOTLOADER
#include <sec/secret.h>

secbool secret_bootloader_locked(void) {
  return (secbool)syscall_invoke0(SYSCALL_SECRET_BOOTLOADER_LOCKED);
}
#endif

// =============================================================================
// button.h
// =============================================================================

#ifdef USE_BUTTON

#include <io/button.h>

bool button_get_event(button_event_t *event) {
  return (bool)syscall_invoke1((uint32_t)event, SYSCALL_BUTTON_GET_EVENT);
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

void rgb_led_set_enabled(bool enabled) {
  syscall_invoke1((uint32_t)enabled, SYSCALL_RGB_LED_SET_ENABLED);
}

bool rgb_led_get_enabled(void) {
  return (bool)syscall_invoke0(SYSCALL_RGB_LED_GET_ENABLED);
}

void rgb_led_set_color(uint32_t color) {
  syscall_invoke1(color, SYSCALL_RGB_LED_SET_COLOR);
}

void rgb_led_effect_start(rgb_led_effect_type_t effect_type,
                          uint32_t requested_cycles) {
  syscall_invoke2((uint32_t)effect_type, requested_cycles,
                  SYSCALL_RGB_LED_EFFECT_START);
}

void rgb_led_effect_stop(void) { syscall_invoke0(SYSCALL_RGB_LED_EFFECT_STOP); }

bool rgb_led_effect_ongoing(void) {
  return (bool)syscall_invoke0(SYSCALL_RGB_LED_EFFECT_ONGOING);
}

rgb_led_effect_type_t rgb_led_effect_get_type(void) {
  return (rgb_led_effect_type_t)syscall_invoke0(
      SYSCALL_RGB_LED_EFFECT_GET_TYPE);
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

#if PYOPT == 0
void optiga_set_sec_max(void) { syscall_invoke0(SYSCALL_OPTIGA_SET_SEC_MAX); }

#endif

#endif  // USE_OPTIGA

// =============================================================================
// secret_keys.h
// =============================================================================

#include <sec/secret_keys.h>

secbool secret_key_delegated_identity(uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
  return (secbool)syscall_invoke1(
      (uint32_t)dest, SYSCALL_SECRET_KEYS_GET_DELEGATED_IDENTITY_KEY);
}

// =============================================================================
// storage.h
// =============================================================================

#include <sec/storage.h>

static PIN_UI_WAIT_CALLBACK storage_init_callback = NULL;

static void storage_callback_wrapper(uint32_t wait, uint32_t progress,
                                     enum storage_ui_message_t message) {
  secbool retval = storage_init_callback(wait, progress, message);
  return_from_unprivileged_callback(retval);
}

void storage_setup(PIN_UI_WAIT_CALLBACK callback) {
  storage_init_callback = callback;

  syscall_invoke1((uint32_t)storage_callback_wrapper, SYSCALL_STORAGE_SETUP);
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

void rng_fill_buffer(void *buffer, size_t buffer_size) {
  syscall_invoke2((uint32_t)buffer, buffer_size, SYSCALL_RNG_FILL_BUFFER);
}

bool rng_fill_buffer_strong(void *buffer, size_t buffer_size) {
  return (bool)syscall_invoke2((uint32_t)buffer, buffer_size,
                               SYSCALL_RNG_FILL_BUFFER_STRONG);
}

// =============================================================================
// fwutils.h
// =============================================================================

#include <util/fwutils.h>

secbool firmware_get_vendor(char *buff, size_t buff_size) {
  return syscall_invoke2((uint32_t)buff, buff_size,
                         SYSCALL_FIRMWARE_GET_VENDOR);
}

int firmware_hash_start(const uint8_t *challenge, size_t challenge_len) {
  return (int)syscall_invoke2((uint32_t)challenge, challenge_len,
                              SYSCALL_FIRMWARE_HASH_START);
}

int firmware_hash_continue(uint8_t *hash, size_t hash_len) {
  return (int)syscall_invoke2((uint32_t)hash, hash_len,
                              SYSCALL_FIRMWARE_HASH_CONTINUE);
}

#ifdef USE_BLE

// =============================================================================
// ble.h
// =============================================================================

#include <io/ble.h>

void ble_start(void) { syscall_invoke0(SYSCALL_BLE_START); }

bool ble_switch_off(void) {
  return (bool)syscall_invoke0(SYSCALL_BLE_SWITCH_OFF);
}

bool ble_switch_on(void) {
  return (bool)syscall_invoke0(SYSCALL_BLE_SWITCH_ON);
}

bool ble_enter_pairing_mode(const uint8_t *name, size_t name_len) {
  return (bool)syscall_invoke2((uint32_t)name, name_len,
                               SYSCALL_BLE_ENTER_PAIRING_MODE);
}

bool ble_disconnect(void) {
  return (bool)syscall_invoke0(SYSCALL_BLE_DISCONNECT);
}

bool ble_erase_bonds(void) {
  return (bool)syscall_invoke0(SYSCALL_BLE_ERASE_BONDS);
}

bool ble_allow_pairing(const uint8_t *pairing_code) {
  return (bool)syscall_invoke1((uint32_t)pairing_code,
                               SYSCALL_BLE_ALLOW_PAIRING);
}

bool ble_reject_pairing(void) {
  return (bool)syscall_invoke0(SYSCALL_BLE_REJECT_PAIRING);
}

bool ble_get_event(ble_event_t *event) {
  return (bool)syscall_invoke1((uint32_t)event, SYSCALL_BLE_GET_EVENT);
}

void ble_get_state(ble_state_t *state) {
  syscall_invoke1((uint32_t)state, SYSCALL_BLE_GET_STATE);
}

bool ble_can_write(void) { return syscall_invoke0(SYSCALL_BLE_CAN_WRITE); }

bool ble_write(const uint8_t *data, uint16_t len) {
  return syscall_invoke2((uint32_t)data, len, SYSCALL_BLE_WRITE);
}

bool ble_can_read(void) { return syscall_invoke0(SYSCALL_BLE_CAN_READ); }

uint32_t ble_read(uint8_t *data, uint16_t len) {
  return (uint32_t)syscall_invoke2((uint32_t)data, len, SYSCALL_BLE_READ);
}

void ble_set_name(const uint8_t *name, size_t len) {
  syscall_invoke2((uint32_t)name, len, SYSCALL_BLE_SET_NAME);
}

bool ble_unpair(const bt_le_addr_t *addr) {
  return (bool)syscall_invoke1((uint32_t)addr, SYSCALL_BLE_UNPAIR);
}

uint8_t ble_get_bond_list(bt_le_addr_t *bonds, size_t count) {
  return (uint8_t)syscall_invoke2((uint32_t)bonds, count,
                                  SYSCALL_BLE_GET_BOND_LIST);
}

void ble_set_high_speed(bool enable) {
  syscall_invoke1((uint32_t)enable, SYSCALL_BLE_SET_HIGH_SPEED);
}

void ble_set_enabled(bool enabled) {
  syscall_invoke1((uint32_t)enabled, SYSCALL_BLE_SET_ENABLED);
}

bool ble_get_enabled(void) {
  return (bool)syscall_invoke0(SYSCALL_BLE_GET_ENABLED);
}

#endif

#ifdef USE_NRF

// =============================================================================
// nrf.h
// =============================================================================

bool nrf_update_required(const uint8_t *data, size_t len) {
  return (bool)syscall_invoke2((uint32_t)data, (uint32_t)len,
                               SYSCALL_NRF_UPDATE_REQUIRED);
}

bool nrf_update(const uint8_t *data, size_t len) {
  return (bool)syscall_invoke2((uint32_t)data, (uint32_t)len,
                               SYSCALL_NRF_UPDATE);
}

uint32_t nrf_get_version(void) {
  return syscall_invoke0(SYSCALL_NRF_GET_VERSION);
}

bool nrf_authenticate(void) {
  return (bool)syscall_invoke0(SYSCALL_NRF_AUTHENTICATE);
}

void nrf_reboot(void) { syscall_invoke0(SYSCALL_NRF_REBOOT); }

#endif

// =============================================================================
// power_manager.h
// =============================================================================

#ifdef USE_POWER_MANAGER

#include <sys/power_manager.h>

pm_status_t pm_suspend(wakeup_flags_t *wakeup_reason) {
  return (pm_status_t)syscall_invoke1((uint32_t)wakeup_reason,
                                      SYSCALL_POWER_MANAGER_SUSPEND);
}

pm_status_t pm_hibernate(void) {
  return (pm_status_t)syscall_invoke0(SYSCALL_POWER_MANAGER_HIBERNATE);
}

pm_status_t pm_charging_enable(void) {
  return (pm_status_t)syscall_invoke0(SYSCALL_POWER_MANAGER_CHARGING_ENABLE);
}

pm_status_t pm_charging_disable(void) {
  return (pm_status_t)syscall_invoke0(SYSCALL_POWER_MANAGER_CHARGING_DISABLE);
}

pm_status_t pm_get_state(pm_state_t *state) {
  return (pm_status_t)syscall_invoke1((uint32_t)state,
                                      SYSCALL_POWER_MANAGER_GET_STATE);
}

bool pm_get_events(pm_event_t *events) {
  return (bool)syscall_invoke1((uint32_t)events,
                               SYSCALL_POWER_MANAGER_GET_EVENTS);
}

#endif  // USE_POWER_MANAGER

// =============================================================================
// jpegdec.h
// =============================================================================

#ifdef USE_HW_JPEG_DECODER

#include <gfx/jpegdec.h>

bool jpegdec_open(void) { return (bool)syscall_invoke0(SYSCALL_JPEGDEC_OPEN); }

void jpegdec_close(void) { syscall_invoke0(SYSCALL_JPEGDEC_CLOSE); }

jpegdec_state_t jpegdec_process(jpegdec_input_t *input) {
  return (jpegdec_state_t)syscall_invoke1((uint32_t)input,
                                          SYSCALL_JPEGDEC_PROCESS);
}

bool jpegdec_get_info(jpegdec_image_t *info) {
  return (bool)syscall_invoke1((uint32_t)info, SYSCALL_JPEGDEC_GET_INFO);
}

bool jpegdec_get_slice_rgba8888(uint32_t *rgba8888, jpegdec_slice_t *slice) {
  return (bool)syscall_invoke2((uint32_t)rgba8888, (uint32_t)slice,
                               SYSCALL_JPEGDEC_GET_SLICE_RGBA8888);
}

bool jpegdec_get_slice_mono8(uint32_t *mono8, jpegdec_slice_t *slice) {
  return (bool)syscall_invoke2((uint32_t)mono8, (uint32_t)slice,
                               SYSCALL_JPEGDEC_GET_SLICE_MONO8);
}

#endif  // USE_HW_JPEG_DECODER

// =============================================================================
// gfx_bitblt.h
// =============================================================================

#ifdef USE_DMA2D

#include <gfx/dma2d_bitblt.h>

void dma2d_wait(void) { syscall_invoke0(SYSCALL_DMA2D_WAIT); }

bool dma2d_rgb565_fill(const gfx_bitblt_t *bb) {
  return (bool)syscall_invoke1((uint32_t)bb, SYSCALL_DMA2D_RGB565_FILL);
}

bool dma2d_rgb565_copy_mono4(const gfx_bitblt_t *bb) {
  return (bool)syscall_invoke1((uint32_t)bb, SYSCALL_DMA2D_RGB565_COPY_MONO4);
}

bool dma2d_rgb565_copy_rgb565(const gfx_bitblt_t *bb) {
  return (bool)syscall_invoke1((uint32_t)bb, SYSCALL_DMA2D_RGB565_COPY_RGB565);
}

bool dma2d_rgb565_blend_mono4(const gfx_bitblt_t *bb) {
  return (bool)syscall_invoke1((uint32_t)bb, SYSCALL_DMA2D_RGB565_BLEND_MONO4);
}

bool dma2d_rgb565_blend_mono8(const gfx_bitblt_t *bb) {
  return (bool)syscall_invoke1((uint32_t)bb, SYSCALL_DMA2D_RGB565_BLEND_MONO8);
}

bool dma2d_rgba8888_fill(const gfx_bitblt_t *bb) {
  return (bool)syscall_invoke1((uint32_t)bb, SYSCALL_DMA2D_RGBA8888_FILL);
}

bool dma2d_rgba8888_copy_mono4(const gfx_bitblt_t *bb) {
  return (bool)syscall_invoke1((uint32_t)bb, SYSCALL_DMA2D_RGBA8888_COPY_MONO4);
}

bool dma2d_rgba8888_copy_rgb565(const gfx_bitblt_t *bb) {
  return (bool)syscall_invoke1((uint32_t)bb,
                               SYSCALL_DMA2D_RGBA8888_COPY_RGB565);
}

bool dma2d_rgba8888_copy_rgba8888(const gfx_bitblt_t *bb) {
  return (bool)syscall_invoke1((uint32_t)bb,
                               SYSCALL_DMA2D_RGBA8888_COPY_RGBA8888);
}

bool dma2d_rgba8888_blend_mono4(const gfx_bitblt_t *bb) {
  return (bool)syscall_invoke1((uint32_t)bb,
                               SYSCALL_DMA2D_RGBA8888_BLEND_MONO4);
}

bool dma2d_rgba8888_blend_mono8(const gfx_bitblt_t *bb) {
  return (bool)syscall_invoke1((uint32_t)bb,
                               SYSCALL_DMA2D_RGBA8888_BLEND_MONO8);
}

#endif  // USE_DMA2D

#ifdef USE_TROPIC

bool tropic_ping(const uint8_t *msg_in, uint8_t *msg_out, uint16_t msg_len) {
  return (bool)syscall_invoke3((uint32_t)msg_in, (uint32_t)msg_out, msg_len,
                               SYSCALL_TROPIC_PING);
}

bool tropic_ecc_key_generate(uint16_t slot_index) {
  return (bool)syscall_invoke1((uint32_t)slot_index,
                               SYSCALL_TROPIC_ECC_KEY_GENERATE);
}

bool tropic_ecc_sign(uint16_t key_slot_index, const uint8_t *dig,
                     uint16_t dig_len, uint8_t *sig) {
  return (bool)syscall_invoke4((uint32_t)key_slot_index, (uint32_t)dig, dig_len,
                               (uint32_t)sig, SYSCALL_TROPIC_ECC_SIGN);
}

bool tropic_data_read(uint16_t udata_slot, uint8_t *data, uint16_t *size) {
  return (bool)syscall_invoke3((uint32_t)udata_slot, (uint32_t)data,
                               (uint32_t)size, SYSCALL_TROPIC_DATA_READ);
}

#endif

#endif  // KERNEL_MODE
