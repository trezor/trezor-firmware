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

#ifdef SECURE_MODE

#ifdef SECRET_MASTER_KEY_SLOT_SIZE

#define SECRET_KEY_MASKING

#include <../vendor/mldsa-native/mldsa/params.h>

secbool secret_key_mcu_device_auth(uint8_t dest[MLDSA_SEEDBYTES]);

#endif  // SECRET_MASTER_KEY_SLOT_SIZE

#ifdef USE_OPTIGA

#include <ecdsa.h>

#define OPTIGA_PAIRING_SECRET_SIZE 32
secbool secret_key_optiga_pairing(uint8_t dest[OPTIGA_PAIRING_SECRET_SIZE]);
secbool secret_key_optiga_masking(uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]);

#endif  // USE_OPTIGA

#ifdef USE_TROPIC

#include <ecdsa.h>
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

#endif  // SECURE_MODE

#ifndef ECDSA_PRIVATE_KEY_SIZE
#include <ecdsa.h>
#endif
secbool secret_keys_delegated_identity(uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]);

#ifdef KERNEL_MODE
#ifdef USE_NRF_AUTH
secbool secret_validate_nrf_pairing(const uint8_t *message, size_t msg_len,
                                    const uint8_t *mac, size_t mac_len);

#endif
#endif
