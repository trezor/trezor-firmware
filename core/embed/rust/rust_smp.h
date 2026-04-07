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

/**
 * @brief Parsed nRF application version in format
 * "major.minor.revision[.build_num]".
 *
 * Matches MCUboot image header layout (8 bytes total).
 * If the optional build number is absent it defaults to 0.
 */
typedef struct __packed {
  uint8_t major;      /**< Major version (0..255). */
  uint8_t minor;      /**< Minor version (0..255). */
  uint16_t revision;  /**< Revision (0..65535). */
  uint32_t build_num; /**< Optional build number (0..4294967295). */
} nrf_app_version_t;

/**
 * @brief Send an SMP Echo request with a small text payload.
 *
 * @param text Pointer to ASCII data (not null-terminated).
 * @param text_len Number of bytes to send.
 * @return true on successful send and valid response, false otherwise.
 *
 * @note Length is bounded by underlying SMP MTU; oversized input fails.
 */
bool smp_echo(const char* text, uint8_t text_len);

/**
 * @brief Issue an SMP Reset request to the remote nRF device.
 *
 * Sends a reset command and does not wait for the device to come back.
 * @return void
 */
void smp_reset(void);

/**
 * @brief Retrieve and parse the active nRF application version via SMP.
 *
 * Performs an Image State read, extracts the version string, and fills
 * the provided structure with numeric fields.
 *
 * @param out Pointer to nrf_app_version_t to be filled (must be valid).
 * @return true on success, false on failure (communication or parse error).
 *
 * @warning Fails if SMP channel not acquired or version format invalid.
 */
bool smp_image_version_get(nrf_app_version_t* out);

/**
 * @brief Feed a received transport byte into the SMP RX state machine.
 *
 * Call for each byte arriving from the nRF link (i.e. UART).
 * Assembles frames and dispatches completed SMP responses internally.
 *
 * @param byte Received raw byte.
 * @return void
 */
void smp_process_rx_byte(uint8_t byte);

/**
 * @brief Upload an MCUboot image to the nRF device over SMP.
 *
 * Streams the binary image followed by hash metadata (if required) using
 * SMP upload semantics.
 *
 * @param data Pointer to image buffer.
 * @param len Size of image buffer in bytes.
 * @param image_hash Pointer to hash bytes (may be NULL if not used).
 * @param image_hash_len Length of hash (e.g. 32 for SHA-256).
 * @return true if upload completed successfully, false on error.
 *
 * @note Caller must ensure image fits partition and hash matches expected size.
 */
bool smp_upload_app_image(const uint8_t* data, size_t len,
                          const uint8_t* image_hash, size_t image_hash_len);
