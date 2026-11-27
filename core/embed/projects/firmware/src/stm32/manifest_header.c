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

// Firmware manifest ("firmware directory") at the start of the image; the
// variant leaf of the firmware tree. Design:
// docs/core/embed-arch/firmware-merkle-tree.md. The layout is
// firmware_manifest_t's (sec/firmware_manifest.h) and must match
// tools/trezor_core_tools/firmware_module.py byte-for-byte. code_hash and the
// proof are filled post-build.

#include <trezor_types.h>

#include <sec/firmware_manifest.h>

#include "../../version.h"

// FW_VARIANT (firmware/build.rs) must be a hardened FW_VARIANT_SEC_* codeword.
_Static_assert(FW_VARIANT == FW_VARIANT_SEC_UNIVERSAL ||
                   FW_VARIANT == FW_VARIANT_SEC_BITCOIN_ONLY ||
                   FW_VARIANT == FW_VARIANT_SEC_CUSTOM,
               "FW_VARIANT must be a hardened FW_VARIANT_SEC_* codeword (see "
               "firmware/build.rs)");

// Module code regions, as offset from the firmware start and size
// (firmware_pq.ld). Linker-defined absolute symbols: only their address is
// meaningful.
extern const uint8_t _manifest_secmon_addr[];
extern const uint8_t _manifest_secmon_size[];
extern const uint8_t _manifest_kernel_addr[];
extern const uint8_t _manifest_kernel_size[];

__attribute__((section(".manifest"),
               used)) static const firmware_manifest_t g_firmware_manifest = {
    .magic = FW_MANIFEST_MAGIC,
    .firmware_variant = FW_VARIANT,
    .firmware_version = {VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH,
                         VERSION_BUILD},
    .module_count = 2,
    .entries =
        {
            // The secure boot/entry module.
            {
                .module_type = FW_MODULE_SECMON,
                .flags = FW_MANIFEST_ENTRY_FLAG_BOOT,
                .addr = FW_MANIFEST_LINKER_VALUE(_manifest_secmon_addr),
                .chunk_size = FW_CHUNK_SIZE,
                .size = FW_MANIFEST_LINKER_VALUE(_manifest_secmon_size),
            },
            // kernel+coreapp
            {
                .module_type = FW_MODULE_APP,
                .flags = 0,
                .addr = FW_MANIFEST_LINKER_VALUE(_manifest_kernel_addr),
                .chunk_size = FW_CHUNK_SIZE,
                .size = FW_MANIFEST_LINKER_VALUE(_manifest_kernel_size),
            },
        },
};

// The manifest and the largest proof must fit the region the linker reserves
// (the *_pq.ld scripts pad `.manifest` to FW_MANIFEST_REGION).
_Static_assert(FW_MANIFEST_REGION_USED(2) <= FW_MANIFEST_REGION,
               "the manifest and its proof must fit FW_MANIFEST_REGION");
