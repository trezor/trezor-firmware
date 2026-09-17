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

// Firmware manifest for prodtest's Merkle-tree variant: a single module,
// flagged as the boot module. See firmware/src/stm32/manifest_header.c.

#include <trezor_types.h>

#include <sec/firmware_manifest.h>

#include "version.h"

// FW_VARIANT (prodtest/build.rs) must be the hardened PRODTEST codeword.
_Static_assert(FW_VARIANT == FW_VARIANT_SEC_PRODTEST,
               "FW_VARIANT must be FW_VARIANT_SEC_PRODTEST (see "
               "prodtest/build.rs)");

// The single module's code region, as offset from the firmware start and size
// (prodtest_pq.ld). Linker-defined absolute symbols: only their address is
// meaningful.
extern const uint8_t _manifest_module_addr[];
extern const uint8_t _manifest_module_size[];

__attribute__((section(".manifest"),
               used)) static const firmware_manifest_t g_firmware_manifest = {
    .magic = FW_MANIFEST_MAGIC,
    .firmware_variant = FW_VARIANT,
    .firmware_version = {VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH,
                         VERSION_BUILD},
    .module_count = 1,
    .entries =
        {
            {
                .module_type = FW_MODULE_PRODTEST,
                .flags = FW_MANIFEST_ENTRY_FLAG_BOOT,
                .addr = FW_MANIFEST_LINKER_VALUE(_manifest_module_addr),
                .chunk_size = FW_CHUNK_SIZE,
                .size = FW_MANIFEST_LINKER_VALUE(_manifest_module_size),
            },
        },
};

// The manifest and the largest proof must fit the region the linker reserves
// (the *_pq.ld scripts pad `.manifest` to FW_MANIFEST_REGION).
_Static_assert(FW_MANIFEST_REGION_USED(1) <= FW_MANIFEST_REGION,
               "the manifest and its proof must fit FW_MANIFEST_REGION");
