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

#include <io/haptic.h>

static bool g_haptic_enabled = false;

ts_t __wur haptic_init(void) { return TS_OK; }

void haptic_deinit(void) {}

ts_t haptic_set_enabled(bool enabled) {
  g_haptic_enabled = enabled;
  return TS_OK;
}

bool haptic_get_enabled(void) { return g_haptic_enabled; }

ts_t haptic_play(haptic_effect_t effect) { return TS_OK; }

ts_t haptic_play_custom(int8_t amplitude_pct, uint16_t duration_ms) {
  return TS_OK;
}
