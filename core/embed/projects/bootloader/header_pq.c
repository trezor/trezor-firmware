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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include <sec/boot_header.h>

#include <version.h>

extern const uint8_t _bootloader_code_size;

typedef union {
  boot_header_auth_t hdr;
  uint8_t raw[BOOT_HEADER_MAXSIZE];
} boot_header_padded_t;

__attribute__((section(".header")))
const boot_header_padded_t g_bootloader_header = {
    .hdr = {
        .magic = BOOT_HEADER_MAGIC_TRZQ,
        .hw_model = HW_MODEL,
        .hw_revision = HW_REVISION,
        .version =
            {
                .major = VERSION_MAJOR,
                .minor = VERSION_MINOR,
                .patch = VERSION_PATCH,
                .build = VERSION_BUILD,
            },
        .fix_version =
            {
                .major = FIX_VERSION_MAJOR,
                .minor = FIX_VERSION_MINOR,
                .patch = FIX_VERSION_PATCH,
                .build = FIX_VERSION_BUILD,
            },
        .min_prev_version =
            {
                .major = 0,
                .minor = 0,
                .patch = 0,
                .build = 0,
            },
        .monotonic_version = BOOTLOADER_MONOTONIC_VERSION,
        // The sigmask field is properly initialized later by headertool_pq
        // (= 0 => no keys used for signature verification; prevents booting)
        .sigmask = 0,
        .header_size = BOOT_HEADER_MAXSIZE,
        // The authenticated part size is calculated for a zero-length Merkle
        // proof, since the Merkle proof is not known at compile time.
        // headertool_pq must update this value later when adding the Merkle
        // proof to the header.
        .auth_size = BOOT_HEADER_MAXSIZE - sizeof(boot_header_merkle_proof_t) -
                     sizeof(boot_header_unauth_t),
        .code_size = (uint32_t)&_bootloader_code_size,
        .storage_address = STORAGE_1_START,
    }};
