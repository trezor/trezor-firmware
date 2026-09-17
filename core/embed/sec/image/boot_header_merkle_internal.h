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
 * @brief boot_header_merkle.c internals, exposed only so the cross-validation
 *        harness (tests/fw_merkle) can compare intermediate values against the
 *        Python signer and the nRF. Not under inc/sec/ -- not part of the API.
 */

#pragma once

/**
 * @brief Merkle LEAF hash H(0x00 || data); counterpart of the 0x01-tagged
 *        internal node.
 *
 * @param data  bytes to commit
 * @param len   length of @p data
 * @param out   [out] the resulting leaf
 */
void merkle_leaf_hash(const uint8_t* data, size_t len,
                      merkle_proof_node_t* out);

/**
 * @brief Smart-hashing chain over one firmware module's code.
 *
 * @param base        base address the module is mapped at
 * @param addr        module offset from @p base
 * @param size        module length in bytes
 * @param chunk_size  per-module chunk size the chain folds over
 * @param out         [out] 32-byte chain value
 */
void firmware_module_code_hash(uintptr_t base, uint32_t addr, uint32_t size,
                               uint32_t chunk_size, uint8_t* out);
