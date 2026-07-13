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

#include <rtl/crypto_helpers.h>

/** Application ring identifiers */
typedef enum {
  APP_RING_0 = 0,  // Most trusted ring
  APP_RING_1 = 1,
  APP_RING_2 = 2,  // Least trusted ring
  APP_RING_COUNT,
} app_ring_t;

/**
 * @brief Initializes the root-of-trust storage.
 *
 * @return TS_OK on success, or an error code on failure.
 */
ts_t app_root_init(void);

/**
 * @brief Updates the root-of-trust storage with a new root packet.
 *
 * Before storing, the function checks the integrity and validity of the
 * root packet, including its signature.
 *
 * @param root_packet Pointer to the root packet to store.
 * @param root_packet_size Size of the root packet in bytes.
 *
 * @return TS_OK on success, or an error code on failure.
 */
ts_t app_root_update(const void* root_packet, size_t root_packet_size);

/**
 * @brief Deletes all stored root packets
 *
 * @return TS_OK on success, or an error code on failure.
 */
ts_t app_root_reset(void);

/**
 * @brief Checks if a root-of-trust is loaded for the given ring.
 *
 * @param ring The ring index to check for the presence of a root-of-trust.
 *
 * @return true if a root-of-trust is loaded for the given ring, false
 * otherwise.
 */
bool app_root_is_loaded(app_ring_t ring);

/**
 * @brief Retrieves the timestamp from the root packet for the given ring.
 *
 * @param ring The ring index to retrieve the timestamp from.
 * @param timestamp Pointer to a uint32_t variable to store the timestamp.
 *
 * @return TS_OK on success, or an error code on failure.
 *         TS_ENOENT if the root packet for the given ring does not exist.
 */
ts_t app_root_get_timestamp(app_ring_t ring, uint32_t* timestamp);

/**
 * @brief Retrieves the Merkle root from the root packet for the given ring.
 *
 * @param ring The ring index to retrieve the Merkle root from.
 * @param merkle_root Pointer to a sha256_digest_t variable to store the Merkle
 * root.
 *
 * @return TS_OK on success, or an error code on failure.
 *         TS_ENOENT if the root packet for the given ring does not exist.
 */
ts_t app_root_get_merkle_root(app_ring_t ring, sha256_digest_t* merkle_root);
