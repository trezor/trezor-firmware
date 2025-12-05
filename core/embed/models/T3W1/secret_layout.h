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

#define SECRET_NUM_KEY_SLOTS 3

#define SECRET_MASTER_KEY_SLOT_SIZE 0x20

// first page: static
#define SECRET_HEADER_OFFSET 0x00
#define SECRET_HEADER_LEN 0x10

#define SECRET_KEY_SLOT_0_OFFSET 0x10
#define SECRET_KEY_SLOT_0_LEN SECRET_MASTER_KEY_SLOT_SIZE

#define SECRET_MONOTONIC_COUNTER_0_OFFSET 0x30
#define SECRET_MONOTONIC_COUNTER_0_LEN 0x400

#define SECRET_MONOTONIC_COUNTER_1_OFFSET 0x430
#define SECRET_MONOTONIC_COUNTER_1_LEN 0x400

#define SECRET_KEY_SLOT_1_OFFSET 0x830
#define SECRET_KEY_SLOT_1_LEN SECRET_MASTER_KEY_SLOT_SIZE
#define SECRET_KEY_SLOT_1_PUBLIC 1

#define SECRET_KEY_SLOT_2_OFFSET 0x850
#define SECRET_KEY_SLOT_2_LEN 0x20
#define SECRET_KEY_SLOT_2_PUBLIC 1

#define SECRET_MCU_DEVICE_CERT_OFFSET 0x870
#define SECRET_MCU_DEVICE_CERT_SIZE 0x1000

#define SECRET_MONOTONIC_COUNTER_2_OFFSET 0x1870
#define SECRET_MONOTONIC_COUNTER_2_LEN 0x400

#define SECRET_LOCK_SLOT_OFFSET 0x1FF0
#define SECRET_LOCK_SLOT_LEN 0x10

// second page: refreshed on wallet wipe
#define SECRET_BHK_OFFSET 0x2000
#define SECRET_BHK_LEN 0x20

// slot assignments
#define SECRET_PRIVILEGED_MASTER_KEY_SLOT 0
#define SECRET_UNPRIVILEGED_MASTER_KEY_SLOT 1
#define SECRET_TROPIC_TROPIC_PUBKEY_SLOT 2
