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

// Turning off the stack protector for this file improves
// the performance of syscall dispatching.
#pragma GCC optimize("no-stack-protector")

#include <trezor_rtl.h>

#include <sys/systask.h>

#include "syscall_probe.h"
#include "syscall_verifiers.h"

#ifdef KERNEL

// Checks if bitblt destination is accessible
#define CHECK_BB_DST(_bb)                                       \
  if (!probe_write_access((_bb)->dst_row,                       \
                          (_bb)->dst_stride * (_bb)->height)) { \
    goto access_violation;                                      \
  }

// Checks if bitblt source is accessible
#define CHECK_BB_SRC(_bb)                                                      \
  if (!probe_read_access((_bb)->src_row, (_bb)->src_stride * (_bb)->height)) { \
    goto access_violation;                                                     \
  }

// ---------------------------------------------------------------------

void sysevents_poll__verified(const sysevents_t *awaited,
                              sysevents_t *signalled, uint32_t deadline) {
  if (!probe_read_access(awaited, sizeof(*awaited))) {
    goto access_violation;
  }

  if (!probe_write_access(signalled, sizeof(*signalled))) {
    goto access_violation;
  }

  sysevents_poll(awaited, signalled, deadline);
  return;

access_violation:
  apptask_access_violation();
}

ssize_t syshandle_read__verified(syshandle_t handle, void *buffer,
                                 size_t buffer_size) {
  if (!probe_write_access(buffer, buffer_size)) {
    goto access_violation;
  }

  return syshandle_read(handle, buffer, buffer_size);

access_violation:
  apptask_access_violation();
  return -1;
}

ssize_t syshandle_write__verified(syshandle_t handle, const void *data,
                                  size_t data_size) {
  if (!probe_read_access(data, data_size)) {
    goto access_violation;
  }

  return syshandle_write(handle, data, data_size);

access_violation:
  apptask_access_violation();
  return -1;
}

// ---------------------------------------------------------------------

#ifdef USE_DBG_CONSOLE

ssize_t dbg_console_read__verified(void *buffer, size_t buffer_size) {
  if (!probe_write_access(buffer, buffer_size)) {
    goto access_violation;
  }

  return dbg_console_read(buffer, buffer_size);

access_violation:
  apptask_access_violation();
  return -1;
}

void dbg_console_write__verified(const void *data, size_t data_size) {
  if (!probe_read_access(data, data_size)) {
    goto access_violation;
  }

  dbg_console_write(data, data_size);
  return;

access_violation:
  apptask_access_violation();
}

#endif  // USE_DBG_CONSOLE

// ---------------------------------------------------------------------

bool boot_image_check__verified(const boot_image_t *image) {
  if (!probe_read_access(image, sizeof(*image))) {
    goto access_violation;
  }

  return boot_image_check(image);

access_violation:
  apptask_access_violation();
  return false;
};

void boot_image_replace__verified(const boot_image_t *image) {
  if (!probe_read_access(image, sizeof(*image))) {
    goto access_violation;
  }

  if (!probe_read_access(image->image_ptr, image->image_size)) {
    goto access_violation;
  }

  boot_image_replace(image);
  return;

access_violation:
  apptask_access_violation();
}

// ---------------------------------------------------------------------

void system_exit__verified(int exit_code) {
  systask_t *task = systask_active();

  systask_exit(task, exit_code);
}

void system_exit_error__verified(const char *title, size_t title_len,
                                 const char *message, size_t message_len,
                                 const char *footer, size_t footer_len) {
  char title_copy[64] = {0};
  char message_copy[64] = {0};
  char footer_copy[64] = {0};

  if (title != NULL) {
    if (!probe_read_access(title, title_len)) {
      goto access_violation;
    }
    title_len = MIN(title_len, sizeof(title_copy) - 1);
    title = strncpy(title_copy, title, title_len);
  } else {
    title_len = 0;
  }

  if (message != NULL) {
    if (!probe_read_access(message, message_len)) {
      goto access_violation;
    }
    message_len = MIN(message_len, sizeof(message_copy) - 1);
    message = strncpy(message_copy, message, message_len);
  } else {
    message_len = 0;
  }

  if (footer != NULL) {
    if (!probe_read_access(footer, footer_len)) {
      goto access_violation;
    }
    footer_len = MIN(footer_len, sizeof(footer_copy) - 1);
    footer = strncpy(footer_copy, footer, footer_len);
  } else {
    footer_len = 0;
  }

  systask_t *task = systask_active();

  systask_exit_error(task, title, title_len, message, message_len, footer,
                     footer_len);

  return;

access_violation:
  apptask_access_violation();
}

void system_exit_fatal__verified(const char *message, size_t message_len,
                                 const char *file, size_t file_len, int line) {
  char message_copy[64] = {0};
  char file_copy[64] = {0};

  if (message != NULL) {
    if (!probe_read_access(message, message_len)) {
      goto access_violation;
    }
    message_len = MIN(message_len, sizeof(message_copy) - 1);
    message = strncpy(message_copy, message, message_len);
  } else {
    message_len = 0;
  }

  if (file != NULL) {
    if (!probe_read_access(file, file_len)) {
      goto access_violation;
    }
    file_len = MIN(file_len, sizeof(file_copy) - 1);
    file = strncpy(file_copy, file, file_len);
  } else {
    file_len = 0;
  }

  systask_t *task = systask_active();

  systask_exit_fatal(task, message, message_len, file, file_len, line);

  return;

access_violation:
  apptask_access_violation();
}

// ---------------------------------------------------------------------

void reboot_and_upgrade__verified(const uint8_t hash[32]) {
  if (!probe_read_access(hash, 32)) {
    goto access_violation;
  }

  reboot_and_upgrade(hash);

access_violation:
  apptask_access_violation();
}

// ---------------------------------------------------------------------

#ifdef FRAMEBUFFER

bool display_get_frame_buffer__verified(display_fb_info_t *fb) {
  if (!probe_write_access(fb, sizeof(*fb))) {
    goto access_violation;
  }

  display_fb_info_t fb_copy = {0};

  bool result = display_get_frame_buffer(&fb_copy);

  *fb = fb_copy;

  return result;

access_violation:
  apptask_access_violation();
  return false;
}

#endif  // FRAMEBUFFER

void display_fill__verified(const gfx_bitblt_t *bb) {
  if (!probe_read_access(bb, sizeof(*bb))) {
    goto access_violation;
  }

  gfx_bitblt_t bb_copy = *bb;

  display_fill(&bb_copy);

  return;

access_violation:
  apptask_access_violation();
}

void display_copy_rgb565__verified(const gfx_bitblt_t *bb) {
  if (!probe_read_access(bb, sizeof(*bb))) {
    goto access_violation;
  }

  gfx_bitblt_t bb_copy = *bb;

  CHECK_BB_SRC(&bb_copy);

  display_copy_rgb565(&bb_copy);
  return;

access_violation:
  apptask_access_violation();
}

// ---------------------------------------------------------------------

void usb_get_state__verified(usb_state_t *state) {
  if (!probe_write_access(state, sizeof(*state))) {
    goto access_violation;
  }

  usb_get_state(state);
  return;

access_violation:
  apptask_access_violation();
}

secbool usb_start__verified(const usb_start_params_t *params) {
  if (!probe_read_access(params, sizeof(*params))) {
    goto access_violation;
  }

  return usb_start(params);

access_violation:
  apptask_access_violation();
  return secfalse;
}

// ---------------------------------------------------------------------

#ifdef USE_SD_CARD

secbool __wur sdcard_read_blocks__verified(uint32_t *dest, uint32_t block_num,
                                           uint32_t num_blocks) {
  if (num_blocks >= (UINT32_MAX / SDCARD_BLOCK_SIZE)) {
    goto access_violation;
  }

  if (!probe_write_access(dest, num_blocks * SDCARD_BLOCK_SIZE)) {
    goto access_violation;
  }

  return sdcard_read_blocks(dest, block_num, num_blocks);

access_violation:
  apptask_access_violation();
  return secfalse;
}

secbool __wur sdcard_write_blocks__verified(const uint32_t *src,
                                            uint32_t block_num,
                                            uint32_t num_blocks) {
  if (num_blocks >= (UINT32_MAX / SDCARD_BLOCK_SIZE)) {
    goto access_violation;
  }

  if (!probe_read_access(src, num_blocks * SDCARD_BLOCK_SIZE)) {
    goto access_violation;
  }

  return sdcard_write_blocks(src, block_num, num_blocks);

access_violation:
  apptask_access_violation();
  return secfalse;
}

#endif  // USE_SD_CARD

// ---------------------------------------------------------------------

void unit_properties_get__verified(unit_properties_t *props) {
  if (!probe_write_access(props, sizeof(*props))) {
    goto access_violation;
  }

  unit_properties_get(props);

  return;

access_violation:
  apptask_access_violation();
}

bool unit_properties_get_sn__verified(uint8_t *device_sn,
                                      size_t max_device_sn_size,
                                      size_t *device_sn_size) {
  if (!probe_write_access(device_sn, max_device_sn_size)) {
    goto access_violation;
  }

  if (!probe_write_access(device_sn_size, sizeof(*device_sn_size))) {
    goto access_violation;
  }

  return unit_properties_get_sn(device_sn, max_device_sn_size, device_sn_size);

access_violation:
  apptask_access_violation();
  return false;
}

// ---------------------------------------------------------------------

#ifdef USE_OPTIGA

optiga_sign_result __wur optiga_sign__verified(
    uint8_t index, const uint8_t *digest, size_t digest_size,
    uint8_t *signature, size_t max_sig_size, size_t *sig_size) {
  if (!probe_read_access(digest, digest_size)) {
    goto access_violation;
  }

  if (!probe_write_access(signature, max_sig_size)) {
    goto access_violation;
  }

  if (!probe_write_access(sig_size, sizeof(*sig_size))) {
    goto access_violation;
  }

  return optiga_sign(index, digest, digest_size, signature, max_sig_size,
                     sig_size);

access_violation:
  apptask_access_violation();
  return (optiga_sign_result){0};
}

bool __wur optiga_cert_size__verified(uint8_t index, size_t *cert_size) {
  if (!probe_write_access(cert_size, sizeof(*cert_size))) {
    goto access_violation;
  }

  return optiga_cert_size(index, cert_size);

access_violation:
  apptask_access_violation();
  return false;
}

bool __wur optiga_read_cert__verified(uint8_t index, uint8_t *cert,
                                      size_t max_cert_size, size_t *cert_size) {
  if (!probe_write_access(cert, max_cert_size)) {
    goto access_violation;
  }

  if (!probe_write_access(cert_size, sizeof(*cert_size))) {
    goto access_violation;
  }

  return optiga_read_cert(index, cert, max_cert_size, cert_size);

access_violation:
  apptask_access_violation();
  return false;
}

bool __wur optiga_read_sec__verified(uint8_t *sec) {
  if (!probe_write_access(sec, sizeof(*sec))) {
    goto access_violation;
  }

  return optiga_read_sec(sec);

access_violation:
  apptask_access_violation();
  return false;
}

#endif  // USE_OPTIGA

// ---------------------------------------------------------------------

#include <sec/secret_keys.h>

secbool secret_key_delegated_identity__verified(
    uint16_t rotation_index, uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
  if (!probe_write_access(dest, ECDSA_PRIVATE_KEY_SIZE)) {
    goto access_violation;
  }

  return secret_key_delegated_identity(rotation_index, dest);

access_violation:
  apptask_access_violation();
  return secfalse;
}

// ---------------------------------------------------------------------

static PIN_UI_WAIT_CALLBACK storage_callback = NULL;

static secbool storage_callback_wrapper(uint32_t wait, uint32_t progress,
                                        enum storage_ui_message_t message) {
  secbool result;

  applet_t *applet = syscall_get_context();
  result = systask_invoke_callback(&applet->task, wait, progress, message,
                                   storage_callback);
  return result;
}

void storage_setup__verified(PIN_UI_WAIT_CALLBACK callback) {
  if (!probe_execute_access(callback)) {
    goto access_violation;
  }
  storage_callback = callback;

  storage_setup(storage_callback_wrapper);
  return;

access_violation:
  apptask_access_violation();
}

secbool storage_unlock__verified(const uint8_t *pin, size_t pin_len,
                                 const uint8_t *ext_salt) {
  if (!probe_read_access(pin, pin_len)) {
    goto access_violation;
  }

  if (!probe_read_access(ext_salt, EXTERNAL_SALT_SIZE)) {
    goto access_violation;
  }

  return storage_unlock(pin, pin_len, ext_salt);

access_violation:
  apptask_access_violation();
  return secfalse;
}

secbool storage_change_pin__verified(const uint8_t *oldpin, size_t oldpin_len,
                                     const uint8_t *newpin, size_t newpin_len,
                                     const uint8_t *old_ext_salt,
                                     const uint8_t *new_ext_salt) {
  if (!probe_read_access(oldpin, oldpin_len)) {
    goto access_violation;
  }

  if (!probe_read_access(newpin, newpin_len)) {
    goto access_violation;
  }

  if (!probe_read_access(old_ext_salt, EXTERNAL_SALT_SIZE)) {
    goto access_violation;
  }

  if (!probe_read_access(new_ext_salt, EXTERNAL_SALT_SIZE)) {
    goto access_violation;
  }

  return storage_change_pin(oldpin, oldpin_len, newpin, newpin_len,
                            old_ext_salt, new_ext_salt);

access_violation:
  apptask_access_violation();
  return secfalse;
}

void storage_ensure_not_wipe_code__verified(const uint8_t *pin,
                                            size_t pin_len) {
  if (!probe_read_access(pin, pin_len)) {
    goto access_violation;
  }

  storage_ensure_not_wipe_code(pin, pin_len);
  return;

access_violation:
  apptask_access_violation();
}

secbool storage_change_wipe_code__verified(const uint8_t *pin, size_t pin_len,
                                           const uint8_t *ext_salt,
                                           const uint8_t *wipe_code,
                                           size_t wipe_code_len) {
  if (!probe_read_access(pin, pin_len)) {
    goto access_violation;
  }

  if (!probe_read_access(ext_salt, EXTERNAL_SALT_SIZE)) {
    goto access_violation;
  }

  if (!probe_read_access(wipe_code, wipe_code_len)) {
    goto access_violation;
  }

  return storage_change_wipe_code(pin, pin_len, ext_salt, wipe_code,
                                  wipe_code_len);

access_violation:
  apptask_access_violation();
  return secfalse;
}

secbool storage_get__verified(const uint16_t key, void *val,
                              const uint16_t max_len, uint16_t *len) {
  if (!probe_write_access(val, max_len)) {
    goto access_violation;
  }

  if (!probe_write_access(len, sizeof(*len))) {
    goto access_violation;
  }

  return storage_get(key, val, max_len, len);

access_violation:
  apptask_access_violation();
  return secfalse;
}

secbool storage_set__verified(const uint16_t key, const void *val,
                              const uint16_t len) {
  if (!probe_read_access(val, len)) {
    goto access_violation;
  }

  return storage_set(key, val, len);

access_violation:
  apptask_access_violation();
  return secfalse;
}

secbool storage_next_counter__verified(const uint16_t key, uint32_t *count) {
  if (!probe_write_access(count, sizeof(*count))) {
    goto access_violation;
  }

  return storage_next_counter(key, count);

access_violation:
  apptask_access_violation();
  return secfalse;
}

// ---------------------------------------------------------------------

void rng_fill_buffer__verified(void *buffer, size_t buffer_size) {
  if (!probe_write_access(buffer, buffer_size)) {
    goto access_violation;
  }

  rng_fill_buffer(buffer, buffer_size);
  return;

access_violation:
  apptask_access_violation();
}

bool rng_fill_buffer_strong__verified(void *buffer, size_t buffer_size) {
  if (!probe_write_access(buffer, buffer_size)) {
    goto access_violation;
  }

  return rng_fill_buffer_strong(buffer, buffer_size);

access_violation:
  apptask_access_violation();
  return false;
}

// ---------------------------------------------------------------------

bool translations_write__verified(const uint8_t *data, uint32_t offset,
                                  uint32_t len) {
  if (!probe_read_access(data, len)) {
    goto access_violation;
  }

  return translations_write(data, offset, len);

access_violation:
  apptask_access_violation();
  return false;
}

const uint8_t *translations_read__verified(uint32_t *len, uint32_t offset) {
  if (!probe_write_access(len, sizeof(*len))) {
    goto access_violation;
  }

  return translations_read(len, offset);

access_violation:
  apptask_access_violation();
  return NULL;
}

// ---------------------------------------------------------------------

int firmware_hash_start__verified(const uint8_t *challenge,
                                  size_t challenge_len) {
  if (!probe_read_access(challenge, challenge_len)) {
    goto access_violation;
  }

  return firmware_hash_start(challenge, challenge_len);

access_violation:
  apptask_access_violation();
  return -1;
}

int firmware_hash_continue__verified(uint8_t *hash, size_t hash_len) {
  if (!probe_write_access(hash, hash_len)) {
    goto access_violation;
  }

  return firmware_hash_continue(hash, hash_len);

access_violation:
  apptask_access_violation();
  return -1;
}

secbool firmware_get_vendor__verified(char *buff, size_t buff_size) {
  if (!probe_write_access(buff, buff_size)) {
    goto access_violation;
  }

  return firmware_get_vendor(buff, buff_size);

access_violation:
  apptask_access_violation();
  return secfalse;
}

// ---------------------------------------------------------------------

#ifdef USE_BLE

bool ble_enter_pairing_mode__verified(const uint8_t *name, size_t name_len) {
  if (!probe_read_access(name, name_len)) {
    goto access_violation;
  }

  return ble_enter_pairing_mode(name, name_len);

access_violation:
  apptask_access_violation();
  return false;
}

bool ble_allow_pairing__verified(const uint8_t *pairing_code) {
  if (!probe_read_access(pairing_code, BLE_PAIRING_CODE_LEN)) {
    goto access_violation;
  }

  return ble_allow_pairing(pairing_code);

access_violation:
  apptask_access_violation();
  return false;
}

void ble_get_state__verified(ble_state_t *state) {
  if (!probe_write_access(state, sizeof(*state))) {
    goto access_violation;
  }

  ble_state_t state_copy = {0};
  ble_get_state(&state_copy);
  *state = state_copy;
  return;

access_violation:
  apptask_access_violation();
}

bool ble_get_event__verified(ble_event_t *event) {
  if (!probe_write_access(event, sizeof(*event))) {
    goto access_violation;
  }

  return ble_get_event(event);

access_violation:
  apptask_access_violation();
  return false;
}

bool ble_write__verified(const uint8_t *data, size_t len) {
  if (!probe_read_access(data, len)) {
    goto access_violation;
  }

  return ble_write(data, len);

access_violation:
  apptask_access_violation();
  return false;
}

uint32_t ble_read__verified(uint8_t *data, size_t len) {
  if (!probe_write_access(data, len)) {
    goto access_violation;
  }

  return ble_read(data, len);

access_violation:
  apptask_access_violation();
  return 0;
}

void ble_set_name__verified(const uint8_t *name, size_t len) {
  if (!probe_read_access(name, len)) {
    goto access_violation;
  }

  ble_set_name(name, len);

  return;

access_violation:
  apptask_access_violation();
}

bool ble_unpair__verified(const bt_le_addr_t *addr) {
  if (!probe_read_access(addr, sizeof(*addr))) {
    goto access_violation;
  }

  return ble_unpair(addr);

access_violation:
  apptask_access_violation();

  return false;
}

uint8_t ble_get_bond_list__verified(bt_le_addr_t *bonds, size_t count) {
  if (!probe_write_access(bonds, sizeof(bt_le_addr_t) * count)) {
    goto access_violation;
  }

  return ble_get_bond_list(bonds, count);

access_violation:
  apptask_access_violation();

  return 0;
}

#endif

// ---------------------------------------------------------------------

#ifdef USE_NRF

bool nrf_update_required__verified(const uint8_t *data, size_t len) {
  if (!probe_read_access(data, len)) {
    goto access_violation;
  }

  return nrf_update_required(data, len);

access_violation:
  apptask_access_violation();
  return false;
}

bool nrf_update__verified(const uint8_t *data, size_t len) {
  if (!probe_read_access(data, len)) {
    goto access_violation;
  }

  return nrf_update(data, len);

access_violation:
  apptask_access_violation();
  return false;
}

#endif

// ---------------------------------------------------------------------

#ifdef USE_POWER_MANAGER

pm_status_t pm_get_state__verified(pm_state_t *status) {
  if (!probe_write_access(status, sizeof(*status))) {
    goto access_violation;
  }

  pm_state_t status_copy = {0};
  pm_status_t retval = pm_get_state(&status_copy);
  *status = status_copy;

  return retval;

access_violation:
  apptask_access_violation();
  return PM_ERROR;
}

bool pm_get_events__verified(pm_event_t *event) {
  if (!probe_write_access(event, sizeof(*event))) {
    goto access_violation;
  }

  pm_event_t event_copy = {0};
  bool retval = pm_get_events(&event_copy);
  *event = event_copy;

  return retval;

access_violation:
  apptask_access_violation();
  return false;
}

pm_status_t pm_suspend__verified(wakeup_flags_t *wakeup_reason) {
  if (!probe_write_access(wakeup_reason, sizeof(*wakeup_reason))) {
    goto access_violation;
  }

  return pm_suspend(wakeup_reason);

access_violation:
  apptask_access_violation();
  return PM_ERROR;
}

#endif

// ---------------------------------------------------------------------

#ifdef USE_HW_JPEG_DECODER

jpegdec_state_t jpegdec_process__verified(jpegdec_input_t *input) {
  if (!probe_write_access(input, sizeof(*input))) {
    goto access_violation;
  }

  return jpegdec_process(input);

access_violation:
  apptask_access_violation();
  return JPEGDEC_STATE_ERROR;
}

bool jpegdec_get_info__verified(jpegdec_image_t *image) {
  if (!probe_write_access(image, sizeof(*image))) {
    goto access_violation;
  }

  return jpegdec_get_info(image);

access_violation:
  apptask_access_violation();
  return false;
}

bool jpegdec_get_slice_rgba8888__verified(void *rgba8888,
                                          jpegdec_slice_t *slice) {
  if (!probe_write_access(rgba8888, JPEGDEC_RGBA8888_BUFFER_SIZE)) {
    goto access_violation;
  }

  if (!probe_write_access(slice, sizeof(*slice))) {
    goto access_violation;
  }

  return jpegdec_get_slice_rgba8888(rgba8888, slice);

access_violation:
  apptask_access_violation();
  return false;
}

bool jpegdec_get_slice_mono8__verified(void *mono8, jpegdec_slice_t *slice) {
  if (!probe_write_access(mono8, JPEGDEC_RGBA8888_BUFFER_SIZE)) {
    goto access_violation;
  }

  if (!probe_write_access(slice, sizeof(*slice))) {
    goto access_violation;
  }

  return jpegdec_get_slice_mono8(mono8, slice);

access_violation:
  apptask_access_violation();
  return false;
}

#endif  // USE_HW_JPEG_DECODER

// ---------------------------------------------------------------------

#ifdef USE_DMA2D

bool dma2d_rgb565_fill__verified(const gfx_bitblt_t *bb) {
  if (!probe_read_access(bb, sizeof(*bb))) {
    goto access_violation;
  }

  gfx_bitblt_t bb_copy = *bb;

  CHECK_BB_DST(&bb_copy);

  return dma2d_rgb565_fill(&bb_copy);

access_violation:
  apptask_access_violation();
  return false;
}

bool dma2d_rgb565_copy_mono4__verified(const gfx_bitblt_t *bb) {
  if (!probe_read_access(bb, sizeof(*bb))) {
    goto access_violation;
  }

  gfx_bitblt_t bb_copy = *bb;

  CHECK_BB_DST(&bb_copy);
  CHECK_BB_SRC(&bb_copy);

  return dma2d_rgb565_copy_mono4(&bb_copy);

access_violation:
  apptask_access_violation();
  return false;
}

bool dma2d_rgb565_copy_rgb565__verified(const gfx_bitblt_t *bb) {
  if (!probe_read_access(bb, sizeof(*bb))) {
    goto access_violation;
  }

  gfx_bitblt_t bb_copy = *bb;

  CHECK_BB_DST(&bb_copy);
  CHECK_BB_SRC(&bb_copy);

  return dma2d_rgb565_copy_rgb565(&bb_copy);

access_violation:
  apptask_access_violation();
  return false;
}

bool dma2d_rgb565_blend_mono4__verified(const gfx_bitblt_t *bb) {
  if (!probe_read_access(bb, sizeof(*bb))) {
    goto access_violation;
  }

  gfx_bitblt_t bb_copy = *bb;

  CHECK_BB_DST(&bb_copy);
  CHECK_BB_SRC(&bb_copy);

  return dma2d_rgb565_blend_mono4(&bb_copy);

access_violation:
  apptask_access_violation();
  return false;
}

bool dma2d_rgb565_blend_mono8__verified(const gfx_bitblt_t *bb) {
  if (!probe_read_access(bb, sizeof(*bb))) {
    goto access_violation;
  }

  gfx_bitblt_t bb_copy = *bb;

  CHECK_BB_DST(&bb_copy);
  CHECK_BB_SRC(&bb_copy);

  return dma2d_rgb565_blend_mono8(&bb_copy);

access_violation:
  apptask_access_violation();
  return false;
}

bool dma2d_rgba8888_fill__verified(const gfx_bitblt_t *bb) {
  if (!probe_read_access(bb, sizeof(*bb))) {
    goto access_violation;
  }

  gfx_bitblt_t bb_copy = *bb;

  CHECK_BB_DST(&bb_copy);

  return dma2d_rgba8888_fill(&bb_copy);

access_violation:
  apptask_access_violation();
  return false;
}

bool dma2d_rgba8888_copy_mono4__verified(const gfx_bitblt_t *bb) {
  if (!probe_read_access(bb, sizeof(*bb))) {
    goto access_violation;
  }

  gfx_bitblt_t bb_copy = *bb;

  CHECK_BB_DST(&bb_copy);
  CHECK_BB_SRC(&bb_copy);

  return dma2d_rgba8888_copy_mono4(&bb_copy);

access_violation:
  apptask_access_violation();
  return false;
}

bool dma2d_rgba8888_copy_rgb565__verified(const gfx_bitblt_t *bb) {
  if (!probe_read_access(bb, sizeof(*bb))) {
    goto access_violation;
  }

  gfx_bitblt_t bb_copy = *bb;

  CHECK_BB_DST(&bb_copy);
  CHECK_BB_SRC(&bb_copy);

  return dma2d_rgba8888_copy_rgb565(&bb_copy);

access_violation:
  apptask_access_violation();
  return false;
}

bool dma2d_rgba8888_copy_rgba8888__verified(const gfx_bitblt_t *bb) {
  if (!probe_read_access(bb, sizeof(*bb))) {
    goto access_violation;
  }

  gfx_bitblt_t bb_copy = *bb;

  CHECK_BB_DST(&bb_copy);
  CHECK_BB_SRC(&bb_copy);

  return dma2d_rgba8888_copy_rgba8888(&bb_copy);

access_violation:
  apptask_access_violation();
  return false;
}

bool dma2d_rgba8888_blend_mono4__verified(const gfx_bitblt_t *bb) {
  if (!probe_read_access(bb, sizeof(*bb))) {
    goto access_violation;
  }

  gfx_bitblt_t bb_copy = *bb;

  CHECK_BB_DST(&bb_copy);
  CHECK_BB_SRC(&bb_copy);

  return dma2d_rgba8888_blend_mono4(&bb_copy);

access_violation:
  apptask_access_violation();
  return false;
}

bool dma2d_rgba8888_blend_mono8__verified(const gfx_bitblt_t *bb) {
  if (!probe_read_access(bb, sizeof(*bb))) {
    goto access_violation;
  }

  gfx_bitblt_t bb_copy = *bb;

  CHECK_BB_DST(&bb_copy);
  CHECK_BB_SRC(&bb_copy);

  return dma2d_rgba8888_blend_mono8(&bb_copy);

access_violation:
  apptask_access_violation();
  return false;
}

#endif

// ---------------------------------------------------------------------

#ifdef USE_BUTTON

#include <io/button.h>

bool button_get_event__verified(button_event_t *event) {
  if (!probe_write_access(event, sizeof(*event))) {
    goto access_violation;
  }

  return button_get_event(event);

access_violation:
  apptask_access_violation();
  return false;
}

#endif

#ifdef USE_TROPIC
#include <libtropic_common.h>
#include <sec/tropic.h>
#include "ecdsa.h"

bool tropic_ping__verified(const uint8_t *msg_out, uint8_t *msg_in,
                           uint16_t msg_len) {
  if (!probe_read_access(msg_out, msg_len)) {
    goto access_violation;
  }

  if (!probe_write_access(msg_in, msg_len)) {
    goto access_violation;
  }

  return tropic_ping(msg_out, msg_in, msg_len);
access_violation:
  apptask_access_violation();
  return false;
}

bool tropic_ecc_key_generate__verified(uint16_t slot_index) {
  return tropic_ecc_key_generate(slot_index);
}

bool tropic_ecc_sign__verified(uint16_t key_slot_index, const uint8_t *dig,
                               uint16_t dig_len, uint8_t *sig) {
  if (!probe_read_access(dig, dig_len)) {
    goto access_violation;
  }

  if (!probe_write_access(sig, ECDSA_RAW_SIGNATURE_SIZE)) {
    goto access_violation;
  }

  return tropic_ecc_sign(key_slot_index, dig, dig_len, sig);
access_violation:
  apptask_access_violation();
  return false;
}

bool tropic_data_read__verified(uint16_t udata_slot, uint8_t *data,
                                uint16_t *size) {
  if (!probe_write_access(data, R_MEM_DATA_SIZE_MAX)) {
    goto access_violation;
  }

  if (!probe_write_access(size, sizeof(*size))) {
    goto access_violation;
  }

  return tropic_data_read(udata_slot, data, size);
access_violation:
  apptask_access_violation();
  return false;
}
#endif

#endif  // KERNEL
