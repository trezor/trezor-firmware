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

#ifndef TREZORHAL_POWERCTL_H
#define TREZORHAL_POWERCTL_H

// Enters low-power mode (actually STOP2 mode on STM32U25)
//
// Can be called only in privileged mode. Use `svc_suspend`
// to call it indirectly from user mode.
void powerctl_suspend(void);

#endif  // TREZORHAL_POWERCTL_H