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

#include <sec/telemetry.h>
#include <trezor_types.h>

bool telemetry_get(telemetry_data_t* out) {
  out->min_temp_c = 20.0f;
  out->max_temp_c = 35.0f;
  out->battery_errors.all = 0;
  out->battery_cycles = 30.00f;
  return true;
}

void telemetry_reset(void) {
  // No-op for emulator
}

#endif
