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

#include <stdint.h>
#include <string.h>

/**
 * @brief Converts a float to a uint32_t using safe type-punning.
 *
 * This function uses memcpy to avoid violating strict-aliasing rules.
 * Modern compilers optimize this into a single register move.
 *
 * @param f The float value to convert.
 * @return The bit-equivalent uint32_t value.
 */
static inline uint32_t float_to_u32(float f) {
  uint32_t u;
  memcpy(&u, &f, sizeof(u));
  return u;
}

/**
 * @brief Converts a uint32_t to a float using safe type-punning.
 *
 * This function uses memcpy to avoid violating strict-aliasing rules.
 * Modern compilers optimize this into a single register move.
 *
 * @param u The uint32_t value to convert.
 * @return The bit-equivalent float value.
 */
static inline float u32_to_float(uint32_t u) {
  float f;
  memcpy(&f, &u, sizeof(f));
  return f;
}
