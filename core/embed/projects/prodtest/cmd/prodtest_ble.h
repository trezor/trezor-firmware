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

#include <rtl/cli.h>

bool prodtest_ble_erase_bonds(cli_t* cli);

#ifdef USE_BLE_CONSOLE
/**
 * Brings up the BLE console at boot.
 *
 * Initializes the console interface, erases all bonds (a unit arriving at any
 * station starts with none, so a full bond table can never lock the host out),
 * forces a static address, and advertises in pairing mode under a per-unit
 * name derived from the CPU id. Pairing requests are then accepted
 * automatically by the periodic BLE timer.
 *
 * @return false if any step failed; the CLI keeps running on whatever other
 * console is compiled in.
 */
bool prodtest_ble_console_start(void);

/**
 * Keeps the BLE console reachable; call from the main loop on every iteration.
 *
 * Whenever the unit is idle (no connection, not advertising for pairing) it
 * re-enters pairing mode under the boot-time name, because the host forgets
 * its bond every session and the driver alone would fall back to whitelist
 * advertising after a disconnect. Rate-limited; cheap to call often.
 */
void prodtest_ble_console_tick(void);
#endif
