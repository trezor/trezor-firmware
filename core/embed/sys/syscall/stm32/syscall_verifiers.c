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

#include <trezor_rtl.h>

#include <sys/systask.h>

#include "syscall_probe.h"
#include "syscall_verifiers.h"

#ifdef SYSCALL_DISPATCH

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

  uint8_t *src_ptr = (uint8_t *)bb_copy.src_row;
  size_t src_len = bb_copy.src_stride * bb_copy.height;

  if (!probe_read_access(src_ptr, src_len)) {
    goto access_violation;
  }

  display_copy_rgb565(&bb_copy);

  return;

access_violation:
  apptask_access_violation();
}

// ---------------------------------------------------------------------

int usb_hid_read__verified(uint8_t iface_num, uint8_t *buf, uint32_t len) {
  if (!probe_write_access(buf, len)) {
    goto access_violation;
  }

  return usb_hid_read(iface_num, buf, len);

access_violation:
  apptask_access_violation();
  return 0;
}

int usb_hid_write__verified(uint8_t iface_num, const uint8_t *buf,
                            uint32_t len) {
  if (!probe_read_access(buf, len)) {
    goto access_violation;
  }

  return usb_hid_write(iface_num, buf, len);

access_violation:
  apptask_access_violation();
  return 0;
}

int usb_hid_read_blocking__verified(uint8_t iface_num, uint8_t *buf,
                                    uint32_t len, int timeout) {
  if (!probe_write_access(buf, len)) {
    goto access_violation;
  }

  return usb_hid_read_blocking(iface_num, buf, len, timeout);

access_violation:
  apptask_access_violation();
  return 0;
}

int usb_hid_write_blocking__verified(uint8_t iface_num, const uint8_t *buf,
                                     uint32_t len, int timeout) {
  if (!probe_read_access(buf, len)) {
    goto access_violation;
  }

  return usb_hid_write_blocking(iface_num, buf, len, timeout);

access_violation:
  apptask_access_violation();
  return 0;
}

// ---------------------------------------------------------------------

int usb_vcp_read__verified(uint8_t iface_num, uint8_t *buf, uint32_t len) {
  if (!probe_write_access(buf, len)) {
    goto access_violation;
  }

  return usb_vcp_read(iface_num, buf, len);

access_violation:
  apptask_access_violation();
  return 0;
}

int usb_vcp_write__verified(uint8_t iface_num, const uint8_t *buf,
                            uint32_t len) {
  if (!probe_read_access(buf, len)) {
    goto access_violation;
  }

  return usb_vcp_write(iface_num, buf, len);

access_violation:
  apptask_access_violation();
  return 0;
}

int usb_vcp_read_blocking__verified(uint8_t iface_num, uint8_t *buf,
                                    uint32_t len, int timeout) {
  if (!probe_write_access(buf, len)) {
    goto access_violation;
  }

  return usb_vcp_read_blocking(iface_num, buf, len, timeout);

access_violation:
  apptask_access_violation();
  return 0;
}

int usb_vcp_write_blocking__verified(uint8_t iface_num, const uint8_t *buf,
                                     uint32_t len, int timeout) {
  if (!probe_read_access(buf, len)) {
    goto access_violation;
  }

  return usb_vcp_write_blocking(iface_num, buf, len, timeout);

access_violation:
  apptask_access_violation();
  return 0;
}

// ---------------------------------------------------------------------

int usb_webusb_read__verified(uint8_t iface_num, uint8_t *buf, uint32_t len) {
  if (!probe_write_access(buf, len)) {
    goto access_violation;
  }

  return usb_webusb_read(iface_num, buf, len);

access_violation:
  apptask_access_violation();
  return 0;
}

int usb_webusb_write__verified(uint8_t iface_num, const uint8_t *buf,
                               uint32_t len) {
  if (!probe_read_access(buf, len)) {
    goto access_violation;
  }

  return usb_webusb_write(iface_num, buf, len);

access_violation:
  apptask_access_violation();
  return 0;
}

int usb_webusb_read_blocking__verified(uint8_t iface_num, uint8_t *buf,
                                       uint32_t len, int timeout) {
  if (!probe_write_access(buf, len)) {
    goto access_violation;
  }

  return usb_webusb_read_blocking(iface_num, buf, len, timeout);

access_violation:
  apptask_access_violation();
  return 0;
}

int usb_webusb_write_blocking__verified(uint8_t iface_num, const uint8_t *buf,
                                        uint32_t len, int timeout) {
  if (!probe_read_access(buf, len)) {
    goto access_violation;
  }

  return usb_webusb_write_blocking(iface_num, buf, len, timeout);

access_violation:
  apptask_access_violation();
  return 0;
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

bool __wur optiga_random_buffer__verified(uint8_t *dest, size_t size) {
  if (!probe_write_access(dest, size)) {
    goto access_violation;
  }

  return optiga_random_buffer(dest, size);

access_violation:
  apptask_access_violation();
  return false;
}

#endif  // USE_OPTIGA

// ---------------------------------------------------------------------

void storage_init__verified(PIN_UI_WAIT_CALLBACK callback, const uint8_t *salt,
                            const uint16_t salt_len) {
  if (!probe_read_access(salt, salt_len)) {
    goto access_violation;
  }

  storage_init(callback, salt, salt_len);
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

void entropy_get__verified(uint8_t *buf) {
  if (!probe_write_access(buf, HW_ENTROPY_LEN)) {
    goto access_violation;
  }

  entropy_get(buf);
  return;

access_violation:
  apptask_access_violation();
}

// ---------------------------------------------------------------------

secbool firmware_calc_hash__verified(const uint8_t *challenge,
                                     size_t challenge_len, uint8_t *hash,
                                     size_t hash_len,
                                     firmware_hash_callback_t callback,
                                     void *callback_context) {
  if (!probe_read_access(challenge, challenge_len)) {
    goto access_violation;
  }

  if (!probe_write_access(hash, hash_len)) {
    goto access_violation;
  }

  return firmware_calc_hash(challenge, challenge_len, hash, hash_len, callback,
                            callback_context);

access_violation:
  apptask_access_violation();
  return secfalse;
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

#endif  // SYSCALL_DISPATCH
