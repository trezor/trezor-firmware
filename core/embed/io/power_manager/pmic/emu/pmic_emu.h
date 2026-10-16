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

#include <io/pmic.h>

// Emulated PMIC: implements <io/pmic.h> and pmic_charger.h on the host.
//
// The "chip" is a report the test can edit. Measurements complete
// synchronously, and the charger extension records what it is told, so the
// emulator runs the real policy core over physical inputs (voltages, VBUS,
// charger phase) instead of a mock of the reported state.

// The report the next measurement returns. Edit it to change what the policy
// sees; the power manager's emulator glue samples it from here.
pmic_report_t* pmic_emu_inputs(void);

// What the policy last told the charger.
bool pmic_emu_charging_on(void);
int pmic_emu_charging_limit_ma(void);
