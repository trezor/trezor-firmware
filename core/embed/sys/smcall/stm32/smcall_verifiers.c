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

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sys/systask.h>

#include "smcall_probe.h"
#include "smcall_verifiers.h"

#ifdef SECMON

// ---------------------------------------------------------------------

void bootargs_set__verified(boot_command_t command, const void *args,
                            size_t args_size) {
  if (!probe_read_access(args, args_size)) {
    goto access_violation;
  }

  bootargs_set(command, args, args_size);
  return;

access_violation:
  apptask_access_violation();
}

void bootargs_get_args__verified(boot_args_t *args) {
  if (!probe_write_access(args, sizeof(*args))) {
    goto access_violation;
  }

  bootargs_get_args(args);
  return;

access_violation:
  apptask_access_violation();
}

// ---------------------------------------------------------------------

bool boot_image_check__verified(const boot_image_t *image) {
  if (!probe_read_access(image, sizeof(*image))) {
    goto access_violation;
  }

  return boot_image_check(image);

access_violation:
  apptask_access_violation();
  return false;
}

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

void reboot_and_upgrade__verified(const uint8_t hash[32]) {
  if (!probe_read_access(hash, 32)) {
    goto access_violation;
  }

  reboot_and_upgrade(hash);

access_violation:
  apptask_access_violation();
}

void reboot_with_rsod__verified(const systask_postmortem_t *pminfo) {
  if (!probe_read_access(pminfo, sizeof(*pminfo))) {
    goto access_violation;
  }

  reboot_with_rsod(pminfo);

access_violation:
  apptask_access_violation();
}

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
    uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
  if (!probe_write_access(dest, ECDSA_PRIVATE_KEY_SIZE)) {
    goto access_violation;
  }

  return secret_key_delegated_identity(dest);

access_violation:
  apptask_access_violation();
  return secfalse;
}

// ---------------------------------------------------------------------

typedef __attribute__((cmse_nonsecure_call))
PIN_UI_WAIT_CALLBACK ns_storage_callback_t;

static ns_storage_callback_t storage_callback = NULL;

static secbool storage_callback_wrapper(uint32_t wait, uint32_t progress,
                                        enum storage_ui_message_t message) {
  if (storage_callback != NULL) {
    return storage_callback(wait, progress, message);
  } else {
    return secfalse;
  }
}

void storage_setup__verified(PIN_UI_WAIT_CALLBACK callback) {
  if (!probe_execute_access(callback)) {
    goto access_violation;
  }

  storage_callback = (ns_storage_callback_t)cmse_nsfptr_create(callback);
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

#include <sec/rng.h>

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
  if (!probe_write_access(data, TROPIC_SLOT_MAX_SIZE_V1)) {
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

#ifdef USE_BACKUP_RAM

bool backup_ram_read__verified(uint16_t key, void *buffer, size_t buffer_size,
                               size_t *data_size) {
  if (!probe_write_access(buffer, buffer_size)) {
    goto access_violation;
  }

  if (!probe_write_access(data_size, sizeof(*data_size))) {
    goto access_violation;
  }

  if (!backup_ram_kernel_accessible(key)) {
    goto access_violation;
  }

  return backup_ram_read(key, buffer, buffer_size, data_size);
access_violation:
  apptask_access_violation();
  return false;
}

bool backup_ram_write__verified(uint16_t key, backup_ram_item_type_t type,
                                const void *data, size_t data_size) {
  if (!probe_read_access(data, data_size)) {
    goto access_violation;
  }

  if (!backup_ram_kernel_accessible(key)) {
    goto access_violation;
  }

  return backup_ram_write(key, type, data, data_size);
access_violation:
  apptask_access_violation();
  return false;
}

#endif  // USE_BACKUP_RAM

#ifdef USE_NRF_AUTH
secbool secret_validate_nrf_pairing__verified(const uint8_t *message,
                                              size_t msg_len,
                                              const uint8_t *mac,
                                              size_t mac_len) {
  if (!probe_read_access(message, msg_len)) {
    goto access_violation;
  }
  if (!probe_read_access(mac, mac_len)) {
    goto access_violation;
  }

  return secret_validate_nrf_pairing(message, msg_len, mac, mac_len);

access_violation:
  apptask_access_violation();
  return false;
}

#endif

#endif  // SECMON
