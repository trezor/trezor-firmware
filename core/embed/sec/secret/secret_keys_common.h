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

#include <trezor_model.h>
#include <trezor_rtl.h>

// Key derivation indices
#define KEY_INDEX_MCU_DEVICE_AUTH 0
#define KEY_INDEX_OPTIGA_PAIRING 1
#define KEY_INDEX_OPTIGA_MASKING 2
#define KEY_INDEX_TROPIC_PAIRING_UNPRIVILEGED 3
#define KEY_INDEX_TROPIC_PAIRING_PRIVILEGED 4
#define KEY_INDEX_TROPIC_MASKING 5
#define KEY_INDEX_NRF_PAIRING 6
#define KEY_INDEX_STORAGE_SALT 7
#define KEY_INDEX_DELEGATED_IDENTITY 8

#ifndef SECRET_PRIVILEGED_MASTER_KEY_SLOT
#define UNUSED_KEY_SLOT 0
// This is a dummy value used instead of SECRET_PRIVILEGED_MASTER_KEY_SLOT
#endif  // SECRET_PRIVILEGED_MASTER_KEY_SLOT

secbool secret_key_derive_sym(uint8_t slot, uint16_t index, uint16_t subindex,
                              uint16_t rotation_index,
                              uint8_t dest[SHA256_DIGEST_LENGTH]);

secbool secret_key_derive_nist256p1(uint8_t slot, uint16_t index,
                                    uint16_t rotation_index,
                                    uint8_t dest[ECDSA_PRIVATE_KEY_SIZE]);

#endif  // SECURE_MODE
