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

// Charger extension to the core PMIC interface (<io/pmic.h>).
//
// Only charger-capable PMICs implement this surface (currently the npm1300).
// PMICs without a charger - e.g. the npm2100 boost regulator for primary cells,
// or a bare GPIO power latch - do not implement it, and it is called only from
// charger-enabled power-manager policy code (the policy core's charging
// controller).
//
// Regulator/buck-mode control is deliberately NOT here: it currently has no
// cross-chip consumer, so it lives as an npm1300-private detail
// (npm1300_defs.h) rather than a public interface. Promote it to an agnostic
// <io/pmic_regulator.h> if and when a policy needs to control regulator mode.

// Enables or disables the charging.
//
// The function returns `false` if the operation cannot be performed.
bool pmic_set_charging(bool enable);

// Sets the charging current limit [mA].
//
// The value must lie within the range the charger hardware accepts, which is
// a property of the chip and lives in its driver. The battery pack's own
// maximum is a board property (BATTERY_CHARGING_CURRENT_MAX_MA in the board
// header); the driver checks at compile time that it fits the chip's range.
//
// The function returns `false` if the operation cannot be performed, including
// when the value is out of range.
bool pmic_set_charging_limit(int i_charge);

// Smallest charging current limit the charger hardware accepts [mA].
//
// The policy uses it to reject a requested maximum the charger could never
// honour, instead of asking for it every tick and being refused.
int pmic_charging_limit_min(void);

// Gets the charging current limit [mA].
int pmic_get_charging_limit(void);

// Clears all battery charger errors.
bool pmic_clear_charger_errors(void);
