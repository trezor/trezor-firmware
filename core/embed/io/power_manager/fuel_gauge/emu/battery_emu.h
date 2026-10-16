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

// Emulator fuel gauge: a gauge whose answers are set by the test instead of
// estimated. Implements fuel_gauge/battery.h for the host build.

// Sets the state of charge the gauge reports (0.0 to 1.0).
void bat_emu_set_soc(float soc);

// Sets the brownout verdict bat_eval_critical() returns.
void bat_emu_set_critical(bool critical);
