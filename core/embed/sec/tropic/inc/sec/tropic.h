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

#include <sec/storage.h>
#include <trezor_types.h>

#ifdef KERNEL_MODE

bool tropic_init(void);

void tropic_deinit(void);

#ifdef TREZOR_PRODTEST
#include "libtropic.h"
lt_handle_t* tropic_get_handle(void);
#endif

#endif

#include "libtropic_common.h"

typedef secbool (*tropic_ui_progress_t)(void);

bool tropic_ping(const uint8_t* msg_out, uint8_t* msg_in, uint16_t msg_len);

bool tropic_ecc_key_generate(uint16_t slot_index);

bool tropic_ecc_sign(uint16_t key_slot_index, const uint8_t* dig,
                     uint16_t dig_len, uint8_t* sig);

bool tropic_stretch_pin(tropic_ui_progress_t ui_progress, uint8_t index,
                        uint8_t stretched_pin[MAC_AND_DESTROY_DATA_SIZE]);

bool tropic_reset_slots(tropic_ui_progress_t ui_progress, uint8_t index,
                        const uint8_t reset_key[MAC_AND_DESTROY_DATA_SIZE]);

bool tropic_pin_set(
    tropic_ui_progress_t ui_progresss,
    uint8_t stretched_pins[PIN_MAX_TRIES][MAC_AND_DESTROY_DATA_SIZE],
    uint8_t reset_key[MAC_AND_DESTROY_DATA_SIZE]);
