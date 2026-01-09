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

#pragma once

#ifdef SECMON

// ---------------------------------------------------------------------
#include <sys/bootargs.h>

void bootargs_set__verified(boot_command_t command, const void *args,
                            size_t args_size);

void bootargs_get_args__verified(boot_args_t *args);

// ---------------------------------------------------------------------

#include <util/boot_image.h>

bool boot_image_check__verified(const boot_image_t *image);

void boot_image_replace__verified(const boot_image_t *image);

// ---------------------------------------------------------------------
#include <sys/bootutils.h>

void reboot_and_upgrade__verified(const uint8_t hash[32]);

void reboot_with_rsod__verified(const systask_postmortem_t *pminfo);

// ---------------------------------------------------------------------
#include <util/unit_properties.h>

void unit_properties_get__verified(unit_properties_t *props);

bool unit_properties_get_sn__verified(uint8_t *device_sn,
                                      size_t max_device_sn_size,
                                      size_t *device_sn_size);

// ---------------------------------------------------------------------
#ifdef USE_OPTIGA

#include <sec/optiga.h>

optiga_sign_result __wur optiga_sign__verified(
    uint8_t index, const uint8_t *digest, size_t digest_size,
    uint8_t *signature, size_t max_sig_size, size_t *sig_size);

bool __wur optiga_cert_size__verified(uint8_t index, size_t *cert_size);

bool __wur optiga_read_cert__verified(uint8_t index, uint8_t *cert,
                                      size_t max_cert_size, size_t *cert_size);

bool __wur optiga_read_sec__verified(uint8_t *sec);

#endif  // USE_OPTIGA

// ---------------------------------------------------------------------

#include <sec/secret_keys.h>

secbool secret_key_delegated_identity__verified(
    uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]);

// ---------------------------------------------------------------------

#include <sec/storage.h>

void storage_setup__verified(PIN_UI_WAIT_CALLBACK callback);

storage_unlock_result_t storage_unlock__verified(const uint8_t *pin,
                                                 size_t pin_len,
                                                 const uint8_t *ext_salt);

storage_pin_change_result_t storage_change_pin__verified(
    const uint8_t *newpin, size_t newpin_len, const uint8_t *new_ext_salt);

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
#include <sec/rng.h>

void rng_fill_buffer__verified(void *buffer, size_t buffer_size);

bool rng_fill_buffer_strong__verified(void *buffer, size_t buffer_size);

// ---------------------------------------------------------------------
#include <util/fwutils.h>

int firmware_hash_start__verified(const uint8_t *challenge,
                                  size_t challenge_len);

int firmware_hash_continue__verified(uint8_t *hash, size_t hash_len);

secbool firmware_get_vendor__verified(char *buff, size_t buff_size);

// ---------------------------------------------------------------------
#ifdef USE_TROPIC

bool tropic_ping__verified(const uint8_t *msg_out, uint8_t *msg_in,
                           uint16_t msg_len);

bool tropic_ecc_key_generate__verified(uint16_t slot_index);

bool tropic_ecc_sign__verified(uint16_t key_slot_index, const uint8_t *dig,
                               uint16_t dig_len, uint8_t *sig);

bool tropic_data_read__verified(uint16_t udata_slot, uint8_t *data,
                                uint16_t *size);

#endif

// ---------------------------------------------------------------------

#ifdef USE_BACKUP_RAM

#include <sys/backup_ram.h>

bool backup_ram_read__verified(uint16_t key, void *buffer, size_t buffer_size,
                               size_t *data_size);

bool backup_ram_write__verified(uint16_t key, backup_ram_item_type_t type,
                                const void *data, size_t data_size);

#endif  // USE_BACKUP_RAM

#ifdef USE_NRF_AUTH

#include <sec/secret_keys.h>

secbool secret_validate_nrf_pairing__verified(const uint8_t *message,
                                              size_t msg_len,
                                              const uint8_t *mac,
                                              size_t mac_len);
#endif

#endif  // SECMON
