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

#ifndef TREZORHAL_SYSCALL_VERIFIERS_H
#define TREZORHAL_SYSCALL_VERIFIERS_H

#ifdef SYSCALL_DISPATCH

// ---------------------------------------------------------------------
#include "systask.h"

void system_exit__verified(int exit_code);

void system_exit_error__verified(const char *title, size_t title_len,
                                 const char *message, size_t message_len,
                                 const char *footer, size_t footer_len);

void system_exit_fatal__verified(const char *message, size_t message_len,
                                 const char *file, size_t file_len, int line);

// ---------------------------------------------------------------------
#include "bootutils.h"

void reboot_and_upgrade__verified(const uint8_t hash[32]);

// ---------------------------------------------------------------------
#include "display.h"

#ifdef XFRAMEBUFFER
bool display_get_frame_buffer__verified(display_fb_info_t *fb);
#endif

void display_fill__verified(const gfx_bitblt_t *bb);

void display_copy_rgb565__verified(const gfx_bitblt_t *bb);

// ---------------------------------------------------------------------
#include "usb_hid.h"

int usb_hid_read__verified(uint8_t iface_num, uint8_t *buf, uint32_t len);

int usb_hid_write__verified(uint8_t iface_num, const uint8_t *buf,
                            uint32_t len);

int usb_hid_read_blocking__verified(uint8_t iface_num, uint8_t *buf,
                                    uint32_t len, int timeout);
int usb_hid_write_blocking__verified(uint8_t iface_num, const uint8_t *buf,
                                     uint32_t len, int timeout);

// ---------------------------------------------------------------------
#include "usb_vcp.h"

int usb_vcp_read__verified(uint8_t iface_num, uint8_t *buf, uint32_t len);

int usb_vcp_write__verified(uint8_t iface_num, const uint8_t *buf,
                            uint32_t len);

int usb_vcp_read_blocking__verified(uint8_t iface_num, uint8_t *buf,
                                    uint32_t len, int timeout);
int usb_vcp_write_blocking__verified(uint8_t iface_num, const uint8_t *buf,
                                     uint32_t len, int timeout);

// ---------------------------------------------------------------------
#include "usb_webusb.h"

int usb_webusb_read__verified(uint8_t iface_num, uint8_t *buf, uint32_t len);

int usb_webusb_write__verified(uint8_t iface_num, const uint8_t *buf,
                               uint32_t len);

int usb_webusb_read_blocking__verified(uint8_t iface_num, uint8_t *buf,
                                       uint32_t len, int timeout);
int usb_webusb_write_blocking__verified(uint8_t iface_num, const uint8_t *buf,
                                        uint32_t len, int timeout);

// ---------------------------------------------------------------------
#include "sdcard.h"

secbool __wur sdcard_read_blocks__verified(uint32_t *dest, uint32_t block_num,
                                           uint32_t num_blocks);

secbool __wur sdcard_write_blocks__verified(const uint32_t *src,
                                            uint32_t block_num,
                                            uint32_t num_blocks);

// ---------------------------------------------------------------------
#include "unit_properties.h"

void unit_properties_get__verified(unit_properties_t *props);

// ---------------------------------------------------------------------
#include "optiga.h"

optiga_sign_result __wur optiga_sign__verified(
    uint8_t index, const uint8_t *digest, size_t digest_size,
    uint8_t *signature, size_t max_sig_size, size_t *sig_size);

bool __wur optiga_cert_size__verified(uint8_t index, size_t *cert_size);

bool __wur optiga_read_cert__verified(uint8_t index, uint8_t *cert,
                                      size_t max_cert_size, size_t *cert_size);

bool __wur optiga_read_sec__verified(uint8_t *sec);

bool __wur optiga_random_buffer__verified(uint8_t *dest, size_t size);

// ---------------------------------------------------------------------
#include "storage.h"

void storage_init__verified(PIN_UI_WAIT_CALLBACK callback, const uint8_t *salt,
                            const uint16_t salt_len);

secbool storage_unlock__verified(const uint8_t *pin, size_t pin_len,
                                 const uint8_t *ext_salt);

secbool storage_change_pin__verified(const uint8_t *oldpin, size_t oldpin_len,
                                     const uint8_t *newpin, size_t newpin_len,
                                     const uint8_t *old_ext_salt,
                                     const uint8_t *new_ext_salt);

void storage_ensure_not_wipe_code__verified(const uint8_t *pin, size_t pin_len);

secbool storage_change_wipe_code__verified(const uint8_t *pin, size_t pin_len,
                                           const uint8_t *ext_salt,
                                           const uint8_t *wipe_code,
                                           size_t wipe_code_len);

secbool storage_get__verified(const uint16_t key, void *val,
                              const uint16_t max_len, uint16_t *len);

secbool storage_set__verified(const uint16_t key, const void *val,
                              const uint16_t len);

secbool storage_next_counter__verified(const uint16_t key, uint32_t *count);

// ---------------------------------------------------------------------
#include "translations.h"

bool translations_write__verified(const uint8_t *data, uint32_t offset,
                                  uint32_t len);

const uint8_t *translations_read__verified(uint32_t *len, uint32_t offset);

// ---------------------------------------------------------------------
#include "entropy.h"

void entropy_get__verified(uint8_t *buf);

// ---------------------------------------------------------------------
#include "fwutils.h"

secbool firmware_calc_hash__verified(const uint8_t *challenge,
                                     size_t challenge_len, uint8_t *hash,
                                     size_t hash_len,
                                     firmware_hash_callback_t callback,
                                     void *callback_context);

secbool firmware_get_vendor__verified(char *buff, size_t buff_size);

#endif  // SYSCALL_DISPATCH

#endif  // TREZORHAL_SYSCALL_VERIFIERS_H
