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

/**
 * @file
 * @brief boot_header_merkle.c internals, exposed only for cross-validation.
 *
 * INTERNAL to sec/image/stm32 -- deliberately not under inc/sec/, so it is not
 * part of the module's API, and no production caller outside
 * boot_header_merkle.c uses any of it.
 *
 * These are the intermediate VALUES the cross-validation harnesses compare
 * against the Python signer's and the nRF's. Going through the public entry
 * points instead would only yield pass/fail, and a hash that differs from
 * theirs by one byte is exactly the failure that is otherwise silent -- images
 * simply stop verifying.
 *
 * Everything the fold needs beyond these stays static:
 * boot_header_internal_node() has no caller outside its own file now that the
 * nRF path folds through boot_header_verify_slot().
 */

#pragma once

/**
 * @brief Smart-hashing chain over one firmware module's code.
 *
 * Declared here so the cross-validation harness can compare it against the
 * Python signer's chain directly -- that comparison is the whole point of the
 * harness, and going through firmware_verify_manifest() would only tell us
 * pass/fail.
 *
 * @param base        base address the module is mapped at
 * @param addr        module offset from @p base
 * @param size        module length in bytes
 * @param chunk_size  per-module chunk size the chain folds over
 * @param out         [out] 32-byte chain value
 */
void firmware_module_code_hash(uintptr_t base, uint32_t addr, uint32_t size,
                               uint32_t chunk_size, uint8_t* out);
