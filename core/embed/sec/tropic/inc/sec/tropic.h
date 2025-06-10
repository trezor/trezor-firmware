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

#ifdef KERNEL_MODE

#define TROPIC_CHIP_ID_SIZE 128
#define TROPIC_RISCV_FW_SIZE 4
#define TROPIC_SPECT_FW_SIZE 4

#include "libtropic.h"

typedef struct {
  bool initialized;
  bool sec_chan_established;
  lt_handle_t handle;
} tropic_driver_t;

extern tropic_driver_t g_tropic_driver;

bool tropic_init(void);

void tropic_deinit(void);

bool tropic_get_spect_fw_version(uint8_t* version_buffer, uint16_t max_len);

bool tropic_get_riscv_fw_version(uint8_t* version_buffer, uint16_t max_len);

bool tropic_get_chip_id(uint8_t* chip_id, uint16_t max_len);

#endif

bool tropic_ping(const uint8_t* msg_out, uint8_t* msg_in, uint16_t msg_len);

bool tropic_get_cert(uint8_t* buf, uint16_t buf_size);

bool tropic_ecc_key_generate(uint16_t slot_index);

bool tropic_ecc_sign(uint16_t key_slot_index, const uint8_t* dig,
                     uint16_t dig_len, uint8_t* sig, uint16_t sig_len);
