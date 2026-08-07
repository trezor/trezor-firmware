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

#include <sys/rng.h>

/**
 * @brief Fills a buffer with random bytes using the hardware RNG and
 * combines it with other entropy sources (e.g., Optiga, Tropic) if
 * available.
 *
 * This function is suitable for generating critical secrets since it
 * combines multiple sources of entropy, but it is slower than
 * `rng_fill_buffer()` since it may use external chips on I2C/SPI.
 *
 * The function requires that Optiga and/or Tropic to be initialized
 * if they are enabled by USE_OPTIGA/USE_TROPIC.
 *
 * @param buffer Buffer to fill with random bytes.
 * @param buffer_size Size of the buffer in bytes.
 *
 * @return True on success, false on failure.
 */
bool __wur rng_fill_buffer_strong(void* buffer, size_t buffer_size);

/**
 * @brief Estimates the duration of a 32-byte `rng_fill_buffer_strong()`
 * call and adds the result to `*time_ms`.
 *
 * Used to precompute the duration of operations that call
 * `rng_fill_buffer_strong()`, e.g. to render progress bars. Accumulates the
 * expected time of each enabled secure element's TRNG request. The MCU's
 * TRNG duration is negligible and not counted.
 *
 * @param time_ms Running total in milliseconds to add the estimate to.
 */
void rng_fill_buffer_strong_time(uint32_t* time_ms);
