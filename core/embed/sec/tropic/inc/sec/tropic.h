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

#ifdef USE_STORAGE
#include <sec/storage.h>
#endif
#include <trezor_types.h>

#include "ed25519-donna/ed25519.h"

// FIDO attestation key and certificate.
#define TROPIC_FIDO_CERT_FIRST_SLOT 0
#define TROPIC_FIDO_CERT_SLOT_COUNT 3
#define TROPIC_FIDO_KEY_SLOT 1  // ECC_SLOT_1

// Device attestation key and certificate.
#define TROPIC_DEVICE_CERT_FIRST_SLOT 3
#define TROPIC_DEVICE_CERT_SLOT_COUNT 3
#define TROPIC_DEVICE_KEY_SLOT 0  // ECC_SLOT_0

#ifdef USE_STORAGE
// KEK masks used in PIN verification
#define TROPIC_KEK_MASKS_PRIVILEGED_SLOT 128
#define TROPIC_KEK_MASKS_UNPRIVILEGED_SLOT 256

// Mac-and-destroy slots used in PIN verification
#define TROPIC_FIRST_MAC_AND_DESTROY_SLOT_PRIVILEGED 0
#define TROPIC_FIRST_MAC_AND_DESTROY_SLOT_UNPRIVILEGED 64
#endif

// Pairing key used by prodtest to inject the privileged and unprivileged
// pairing keys.
#define TROPIC_FACTORY_PAIRING_KEY_SLOT 0  // PAIRING_KEY_SLOT_INDEX_0

// Pairing key used by the HSM to inject the attestation FIDO key and generate
// the device key, and by unofficial firwmare.
#define TROPIC_UNPRIVILEGED_PAIRING_KEY_SLOT 1  // PAIRING_KEY_SLOT_INDEX_1

// Pairing key used by official firmware.
#define TROPIC_PRIVILEGED_PAIRING_KEY_SLOT 2  // PAIRING_KEY_SLOT_INDEX_2

#define TROPIC_MAC_AND_DESTROY_SIZE 32

#ifdef KERNEL_MODE

bool tropic_init(void);

void tropic_deinit(void);

#ifdef TREZOR_PRODTEST
#include "libtropic.h"
lt_handle_t* tropic_get_handle(void);
#endif

#endif

typedef secbool (*tropic_ui_progress_t)(void);

void tropic_get_factory_privkey(curve25519_key privkey);

bool tropic_ping(const uint8_t* msg_out, uint8_t* msg_in, uint16_t msg_len);

bool tropic_ecc_key_generate(uint16_t slot_index);

bool tropic_ecc_sign(uint16_t key_slot_index, const uint8_t* dig,
                     uint16_t dig_len, uint8_t* sig);

bool tropic_data_read(uint16_t udata_slot, uint8_t* data, uint16_t* size);

bool tropic_data_multi_size(uint16_t first_slot, size_t* data_length);

bool tropic_data_multi_read(uint16_t first_slot, uint16_t slot_count,
                            uint8_t* data, size_t max_data_length,
                            size_t* data_length);

bool tropic_random_buffer(void* buffer, size_t length);

#ifdef USE_STORAGE
bool tropic_pin_stretch(tropic_ui_progress_t ui_progress, uint16_t pin_index,
                        uint8_t stretched_pin[TROPIC_MAC_AND_DESTROY_SIZE]);

bool tropic_pin_reset_slots(
    tropic_ui_progress_t ui_progress, uint16_t pin_index,
    const uint8_t reset_key[TROPIC_MAC_AND_DESTROY_SIZE]);

bool tropic_pin_set(
    tropic_ui_progress_t ui_progress,
    uint8_t stretched_pins[PIN_MAX_TRIES][TROPIC_MAC_AND_DESTROY_SIZE],
    uint8_t reset_key[TROPIC_MAC_AND_DESTROY_SIZE]);

bool tropic_pin_set_kek_masks(
    tropic_ui_progress_t ui_progress,
    const uint8_t kek[TROPIC_MAC_AND_DESTROY_SIZE],
    const uint8_t stretched_pins[PIN_MAX_TRIES][TROPIC_MAC_AND_DESTROY_SIZE]);

bool tropic_pin_unmask_kek(
    tropic_ui_progress_t ui_progress, uint16_t pin_index,
    const uint8_t stretched_pin[TROPIC_MAC_AND_DESTROY_SIZE],
    uint8_t kek[TROPIC_MAC_AND_DESTROY_SIZE]);

uint32_t tropic_estimate_time_ms(storage_pin_op_t op, uint16_t pin_index);
#endif
