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

#ifdef SECURE_MODE

#include <sys/rng_use_flags.h>

static uint32_t g_rng_flags = 0;

void rng_use_flags_clear(void) { g_rng_flags = 0; }

void rng_use_flag_set(rng_type_t type) { g_rng_flags |= (1 << type); }

bool rng_use_flag_is_set(rng_type_t type) {
  return (g_rng_flags & (1 << type)) != 0;
}

#endif  // SECURE_MODE
