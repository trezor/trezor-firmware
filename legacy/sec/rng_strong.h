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

#include <stdbool.h>

#include "rand.h"

// Minimal implementation of sec/rng_strong.h from core/embed

static inline bool rng_fill_buffer_strong(void* buffer, size_t buffer_size) {
  random_buffer((uint8_t*)buffer, buffer_size);
  return true;
}

static inline void rng_fill_buffer_strong_time(uint32_t* time) {
  (void)time;  // Suppress unused parameter warning
}

static inline bool rng_fill_buffer(void* buffer, size_t buffer_size) {
  random_buffer((uint8_t*)buffer, buffer_size);
  return true;
}
