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

#include <sys/rng_use_flags.h>

#ifndef TREZOR_EMULATOR
#error "Mock RNG must not be compiled into a non-emulator build"
#endif

_Static_assert(sizeof(void*) == 8,
               "Mock RNG compiled for a 32-bit target -- device build?");

#if !defined(__linux__) && !defined(__APPLE__) && !defined(_WIN32)
#error "Insecure PRNG is not supported on this target"
#endif

#if __STDC_HOSTED__ == 0
#error "Insecure PRNG must not be compiled for a freestanding target"
#endif

#ifdef USE_INSECURE_PRNG

// This implementation intentionally differs from real hardware. The flag
// cannot be set in emulator builds, ensuring that only real TRNG
// implementations can report their use.

void rng_use_flags_clear(void) {}

bool rng_use_flag_is_set(rng_type_t type) { return true; }

#endif  // USE_INSECURE_PRNG
