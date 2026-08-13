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

// This module records which real TRNG implementations were used, allowing
// callers to verify that strong random numbers were generated using all TRNGs.

/**
 * @brief TRNG types.
 */
typedef enum {
  RNG_TYPE_MCU,
  RNG_TYPE_OPTIGA,
  RNG_TYPE_TROPIC,
} rng_type_t;

/**
 * @brief Clears all RNG flags.
 *
 * This function resets the internal state of the RNG flags, indicating that no
 * RNG types have been used or set.
 */
void rng_use_flags_clear(void);

#ifndef TREZOR_EMULATOR
/**
 * @brief Marks the specified RNG type as used.
 *
 * @note This function is intentionally unavailable in emulator builds. Code
 * using a PRNG must not call it; it may only be called by real TRNG
 * implementations in hardware builds.
 */
void rng_use_flag_set(rng_type_t type);
#endif

/**
 * @brief Reads the use flag state of the specified RNG type.
 *
 * @return true if the specified RNG type has been used
 */
bool rng_use_flag_is_set(rng_type_t type);
