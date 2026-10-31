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
 * @brief A firmware hash.
 */
typedef struct {
  uint8_t bytes[32];
} firmware_hash_t;

/**
 * @brief Starts or restarts the firmware hash calculation.
 *
 * @param challenge Optional challenge data, or NULL.
 * @param challenge_len Length of the challenge data in bytes (1 to 32).
 * @return TS_OK on success, TS_EINVAL if the challenge cannot initialize the
 * hash.
 */
ts_t firmware_hash_start(const uint8_t* challenge, size_t challenge_len);

/**
 * @brief Continues the firmware hash calculation.
 *
 * Call repeatedly while the call succeeds and @p progress is less than 100.
 * When the call succeeds and @p progress is 100, @p hash contains the completed
 * firmware hash.
 *
 * @param[out] hash Buffer that receives the completed firmware hash.
 * @param[out] progress Hash calculation progress, from 0 to 100.
 * @return
 *    TS_OK on success,
 *    TS_ENOINIT if hashing has not started or is already finished,
 *    TS_EINVAL if updating or finalizing the hash fails.
 */
ts_t firmware_hash_continue(firmware_hash_t* hash, int32_t* progress);

/**
 * @brief Reads the firmware vendor string from the firmware header.
 *
 * @param[out] buff Buffer that receives the vendor string.
 * @param buff_size Size of @p buff in bytes; reserve at least 64 bytes.
 * @return TS_OK if the vendor string was read successfully.
 */
ts_t firmware_get_vendor(char* buff, size_t buff_size);

#ifdef SECURE_MODE

/**
 * @brief Invalidates the firmware by erasing the first 1 KiB of the firmware
 * area.
 *
 * Requires MPU write access to the firmware area.
 */
void firmware_invalidate_header(void);

#endif  // SECURE_MODE
