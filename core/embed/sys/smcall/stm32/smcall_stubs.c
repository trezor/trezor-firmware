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

#if defined(KERNEL) && defined(USE_SECMON_LAYOUT)

#include "smcall_invoke.h"
#include "smcall_numbers.h"

// =============================================================================
// bootargs.h
// =============================================================================

#include <sys/bootargs.h>

void bootargs_set(boot_command_t command, const void *args, size_t args_size) {
  smcall_invoke3(command, (uint32_t)args, args_size, SMCALL_BOOTARGS_SET);
}

void bootargs_get_args(boot_args_t *args) {
  smcall_invoke1((uint32_t)args, SMCALL_BOOTARGS_GET_ARGS);
}
// =============================================================================
// boot_image.h
// =============================================================================

#include <util/boot_image.h>

bool boot_image_check(const boot_image_t *image) {
  return (bool)smcall_invoke1((uint32_t)image, SMCALL_BOOT_IMAGE_CHECK);
}

void boot_image_replace(const boot_image_t *image) {
  smcall_invoke1((uint32_t)image, SMCALL_BOOT_IMAGE_REPLACE);
}

// =============================================================================
// board_capabilities.h
// =============================================================================

#include <util/board_capabilities.h>

uint32_t get_board_name(void) { return smcall_invoke0(SMCALL_GET_BOARD_NAME); }

void get_boardloader_version(boardloader_version_t *version) {
  smcall_invoke1((uint32_t)version, SMCALL_GET_BOARDLOADER_VERSION);
}

// =============================================================================
// bootutils.h
// =============================================================================

#include <sys/bootutils.h>

void reboot_to_bootloader(void) {
  smcall_invoke0(SMCALL_REBOOT_TO_BOOTLOADER);
  while (1)
    ;
}

void reboot_and_upgrade(const uint8_t hash[32]) {
  smcall_invoke1((uint32_t)hash, SMCALL_REBOOT_AND_UPGRADE);
  while (1)
    ;
}

void reboot_device(void) {
  smcall_invoke0(SMCALL_REBOOT_DEVICE);
  while (1)
    ;
}

void reboot_or_halt_after_rsod(void) {
  smcall_invoke0(SMCALL_REBOOT_DEVICE);
  while (1)
    ;
}

void reboot_to_off(void) {
  smcall_invoke0(SMCALL_REBOOT_TO_OFF);
  while (1)
    ;
}

void reboot_with_rsod(const systask_postmortem_t *pminfo) {
  smcall_invoke1((uint32_t)pminfo, SMCALL_REBOOT_WITH_RSOD);
  while (1)
    ;
}

// =============================================================================
// power_manager_secure.h
// =============================================================================

#ifdef USE_SUSPEND

#include <sys/suspend_io.h>

void suspend_cpu(void) { smcall_invoke0(SMCALL_SUSPEND_CPU); }

void suspend_secure_drivers(void) {
  smcall_invoke0(SMCALL_SUSPEND_SECURE_DRIVERS);
}

void resume_secure_drivers(void) {
  smcall_invoke0(SMCALL_RESUME_SECURE_DRIVERS);
}

#endif  // USE_SUSPEND

// =============================================================================
// unit_properties.h
// =============================================================================

#include <util/unit_properties.h>

void unit_properties_get(unit_properties_t *props) {
  smcall_invoke1((uint32_t)props, SMCALL_UNIT_PROPERTIES_GET);
}

bool unit_properties_get_sn(uint8_t *device_sn, size_t max_device_sn_size,
                            size_t *device_sn_size) {
  return (bool)smcall_invoke3((uint32_t)device_sn, max_device_sn_size,
                              (uint32_t)device_sn_size,
                              SMCALL_UNIT_PROPERTIES_GET_SN);
}

// =============================================================================
// secret.h
// =============================================================================

#ifdef LOCKABLE_BOOTLOADER

#include <sec/secret.h>

secbool secret_bootloader_locked(void) {
  return (secbool)smcall_invoke0(SMCALL_SECRET_BOOTLOADER_LOCKED);
}

#endif  // LOCKABLE_BOOTLOADER

// =============================================================================
// random_delays.h
// =============================================================================

void random_delays_refresh_rdi(void) {
  smcall_invoke0(SMCALL_RANDOM_DELAYS_REFRESH_RDI);
}

void wait_random(void) { smcall_invoke0(SMCALL_WAIT_RANDOM); }

// =============================================================================
// optiga.h
// =============================================================================

#ifdef USE_OPTIGA

#include <sec/optiga.h>

optiga_sign_result optiga_sign(uint8_t index, const uint8_t *digest,
                               size_t digest_size, uint8_t *signature,
                               size_t max_sig_size, size_t *sig_size) {
  return (optiga_sign_result)smcall_invoke6(
      index, (uint32_t)digest, digest_size, (uint32_t)signature, max_sig_size,
      (uint32_t)sig_size, SMCALL_OPTIGA_SIGN);
}

bool optiga_cert_size(uint8_t index, size_t *cert_size) {
  return (bool)smcall_invoke2(index, (uint32_t)cert_size,
                              SMCALL_OPTIGA_CERT_SIZE);
}

bool optiga_read_cert(uint8_t index, uint8_t *cert, size_t max_cert_size,
                      size_t *cert_size) {
  return (bool)smcall_invoke4(index, (uint32_t)cert, max_cert_size,
                              (uint32_t)cert_size, SMCALL_OPTIGA_READ_CERT);
}

bool optiga_read_sec(uint8_t *sec) {
  return (bool)smcall_invoke1((uint32_t)sec, SMCALL_OPTIGA_READ_SEC);
}

void optiga_close_channel(void) { smcall_invoke0(SMCALL_OPTIGA_CLOSE_CHANNEL); }

void optiga_power_down(void) { smcall_invoke0(SMCALL_OPTIGA_POWER_DOWN); }

void optiga_init_and_configure(void) {
  smcall_invoke0(SMCALL_OPTIGA_INIT_AND_CONFIGURE);
}

#if PYOPT == 0
void optiga_set_sec_max(void) { smcall_invoke0(SMCALL_OPTIGA_SET_SEC_MAX); }

#endif

#endif  // USE_OPTIGA

// =============================================================================
// secret_keys.h
// =============================================================================

#include <sec/secret_keys.h>

secbool secret_key_delegated_identity(uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]) {
  return (secbool)smcall_invoke1((uint32_t)dest,
                                 SMCALL_SECRET_KEYS_GET_DELEGATED_IDENTITY_KEY);
}

// =============================================================================
// storage.h
// =============================================================================

#include <sec/storage.h>

void storage_setup(PIN_UI_WAIT_CALLBACK callback) {
  smcall_invoke1((uint32_t)callback, SMCALL_STORAGE_SETUP);
}

void storage_wipe(void) { smcall_invoke0(SMCALL_STORAGE_WIPE); }
secbool storage_is_unlocked(void) {
  return (secbool)smcall_invoke0(SMCALL_STORAGE_IS_UNLOCKED);
}

void storage_lock(void) { smcall_invoke0(SMCALL_STORAGE_LOCK); }

secbool storage_unlock(const uint8_t *pin, size_t pin_len,
                       const uint8_t *ext_salt) {
  return (secbool)smcall_invoke3((uint32_t)pin, pin_len, (uint32_t)ext_salt,
                                 SMCALL_STORAGE_UNLOCK);
}

secbool storage_has_pin(void) {
  return (secbool)smcall_invoke0(SMCALL_STORAGE_HAS_PIN);
}
secbool storage_pin_fails_increase(void) {
  return (secbool)smcall_invoke0(SMCALL_STORAGE_PIN_FAILS_INCREASE);
}

uint32_t storage_get_pin_rem(void) {
  return smcall_invoke0(SMCALL_STORAGE_GET_PIN_REM);
}

secbool storage_change_pin(const uint8_t *newpin, size_t newpin_len,
                           const uint8_t *new_ext_salt) {
  return (secbool)smcall_invoke3((uint32_t)newpin, newpin_len,
                                 (uint32_t)new_ext_salt,
                                 SMCALL_STORAGE_CHANGE_PIN);
}

void storage_ensure_not_wipe_code(const uint8_t *pin, size_t pin_len) {
  smcall_invoke2((uint32_t)pin, pin_len, SMCALL_STORAGE_ENSURE_NOT_WIPE_CODE);
}

secbool storage_has_wipe_code(void) {
  return (secbool)smcall_invoke0(SMCALL_STORAGE_HAS_WIPE_CODE);
}

secbool storage_change_wipe_code(const uint8_t *pin, size_t pin_len,
                                 const uint8_t *ext_salt,
                                 const uint8_t *wipe_code,
                                 size_t wipe_code_len) {
  return (secbool)smcall_invoke5((uint32_t)pin, pin_len, (uint32_t)ext_salt,
                                 (uint32_t)wipe_code, wipe_code_len,
                                 SMCALL_STORAGE_CHANGE_WIPE_CODE);
}

secbool storage_has(const uint16_t key) {
  return (secbool)smcall_invoke1(key, SMCALL_STORAGE_HAS);
}

secbool storage_get(const uint16_t key, void *val, const uint16_t max_len,
                    uint16_t *len) {
  return (secbool)smcall_invoke4(key, (uint32_t)val, max_len, (uint32_t)len,
                                 SMCALL_STORAGE_GET);
}

secbool storage_set(const uint16_t key, const void *val, const uint16_t len) {
  return (secbool)smcall_invoke3(key, (uint32_t)val, len, SMCALL_STORAGE_SET);
}

secbool storage_delete(const uint16_t key) {
  return (secbool)smcall_invoke1(key, SMCALL_STORAGE_DELETE);
}

secbool storage_set_counter(const uint16_t key, const uint32_t count) {
  return (secbool)smcall_invoke2(key, count, SMCALL_STORAGE_SET_COUNTER);
}

secbool storage_next_counter(const uint16_t key, uint32_t *count) {
  return (secbool)smcall_invoke2(key, (uint32_t)count,
                                 SMCALL_STORAGE_NEXT_COUNTER);
}

// =============================================================================
// rng.h
// =============================================================================

#include <sec/rng.h>

void rng_fill_buffer(void *buffer, size_t buffer_size) {
  smcall_invoke2((uint32_t)buffer, buffer_size, SMCALL_RNG_FILL_BUFFER);
}

bool rng_fill_buffer_strong(void *buffer, size_t buffer_size) {
  return (bool)smcall_invoke2((uint32_t)buffer, buffer_size,
                              SMCALL_RNG_FILL_BUFFER_STRONG);
}

// =============================================================================
// fwutils.h
// =============================================================================

#include <util/fwutils.h>

secbool firmware_get_vendor(char *buff, size_t buff_size) {
  return smcall_invoke2((uint32_t)buff, buff_size, SMCALL_FIRMWARE_GET_VENDOR);
}

int firmware_hash_start(const uint8_t *challenge, size_t challenge_len) {
  return (int)smcall_invoke2((uint32_t)challenge, challenge_len,
                             SMCALL_FIRMWARE_HASH_START);
}

int firmware_hash_continue(uint8_t *hash, size_t hash_len) {
  return (int)smcall_invoke2((uint32_t)hash, hash_len,
                             SMCALL_FIRMWARE_HASH_CONTINUE);
}

#ifdef USE_TROPIC

bool tropic_ping(const uint8_t *msg_in, uint8_t *msg_out, uint16_t msg_len) {
  return (bool)smcall_invoke3((uint32_t)msg_in, (uint32_t)msg_out, msg_len,
                              SMCALL_TROPIC_PING);
}

bool tropic_ecc_key_generate(uint16_t slot_index) {
  return (bool)smcall_invoke1((uint32_t)slot_index,
                              SMCALL_TROPIC_ECC_KEY_GENERATE);
}

bool tropic_ecc_sign(uint16_t key_slot_index, const uint8_t *dig,
                     uint16_t dig_len, uint8_t *sig) {
  return (bool)smcall_invoke4((uint32_t)key_slot_index, (uint32_t)dig, dig_len,
                              (uint32_t)sig, SMCALL_TROPIC_ECC_SIGN);
}

bool tropic_data_read(uint16_t udata_slot, uint8_t *data, uint16_t *size) {
  return (bool)smcall_invoke3((uint32_t)udata_slot, (uint32_t)data,
                              (uint32_t)size, SMCALL_TROPIC_DATA_READ);
}

#endif

// =============================================================================
// backup_ram.h
// =============================================================================

#ifdef USE_BACKUP_RAM

#include <sys/backup_ram.h>

uint16_t backup_ram_search(uint16_t min_key) {
  return (bool)smcall_invoke1(min_key, SMCALL_BACKUP_RAM_SEARCH);
}

bool backup_ram_read(uint16_t key, void *buffer, size_t buffer_size,
                     size_t *data_size) {
  return (bool)smcall_invoke4(key, (uint32_t)buffer, buffer_size,
                              (uint32_t)data_size, SMCALL_BACKUP_RAM_READ);
}

bool backup_ram_write(uint16_t key, backup_ram_item_type_t type,
                      const void *data, size_t data_size) {
  return (bool)smcall_invoke4(key, type, (uint32_t)data, data_size,
                              SMCALL_BACKUP_RAM_WRITE);
}

#endif  // USE_BACKUP_RAM

#ifdef USE_NRF

#include <sec/secret.h>

secbool secret_validate_nrf_pairing(const uint8_t *message, size_t msg_len,
                                    const uint8_t *mac, size_t mac_len) {
  return (secbool)smcall_invoke4((uint32_t)message, msg_len, (uint32_t)mac,
                                 mac_len, SMCALL_SECRET_VALIDATE_NRF_PAIRING);
}

#endif

#endif  // defined(KERNEL) && defined(USE_SECMON_LAYOUT)
