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

#include <trezor_types.h>

#include <ecdsa.h>

secbool secret_key_delegated_identity(uint16_t rotation_index,
                                      uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]);

#ifdef SECURE_MODE

#ifdef SECRET_MASTER_KEY_SLOT_SIZE

#define SECRET_KEY_MASKING

#include <../vendor/mldsa-native/mldsa/params.h>

secbool secret_key_mcu_device_auth(uint8_t dest[MLDSA_SEEDBYTES]);

#endif  // SECRET_MASTER_KEY_SLOT_SIZE

#ifdef USE_OPTIGA

#define OPTIGA_PAIRING_SECRET_SIZE 32
secbool secret_key_optiga_pairing(uint8_t dest[OPTIGA_PAIRING_SECRET_SIZE]);
secbool secret_key_optiga_masking(uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]);

#endif  // USE_OPTIGA

#ifdef USE_TROPIC

#include <ed25519-donna/ed25519.h>

secbool secret_key_tropic_public(curve25519_key dest);

secbool secret_key_tropic_pairing_unprivileged(curve25519_key dest);
secbool secret_key_tropic_pairing_privileged(curve25519_key dest);
secbool secret_key_tropic_masking(uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]);

#endif  // USE_TROPIC

#ifdef USE_NRF_AUTH

#define NRF_PAIRING_SECRET_SIZE 32
secbool secret_key_nrf_pairing(uint8_t dest[NRF_PAIRING_SECRET_SIZE]);

#endif

#define SECRET_KEY_STORAGE_SALT_SIZE 32

secbool secret_key_storage_salt(uint16_t fw_type,
                                uint8_t dest[SECRET_KEY_STORAGE_SALT_SIZE]);

#define SECRET_KEY_MASTER_KEY_SIZE 32

typedef struct {
  size_t size;
  uint8_t bytes[SECRET_KEY_MASTER_KEY_SIZE];
} secret_key_master_key_t;

/**
 * Retrieves the generated buffer with the master key.
 *
 * If master key has not yet been generated for the device,
 * it is generated now.
 *
 * This key is used to derive additional credential keys (e.g. Evolu).
 *
 * @param master_key structure filled with the generated data.
 */
secbool secret_key_master_key_get(secret_key_master_key_t* master_key);

#endif  // SECURE_MODE

#ifdef KERNEL_MODE
#ifdef USE_NRF_AUTH
secbool secret_validate_nrf_pairing(const uint8_t* message, size_t msg_len,
                                    const uint8_t* mac, size_t mac_len);

#endif
#endif
