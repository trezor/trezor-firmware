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

#ifndef LIB_RSOD_H
#define LIB_RSOD_H

#include <sys/systask.h>

// Shows RSOD (Red Screen of Death) using terminal.
void rsod_terminal(const systask_postmortem_t* pminfo);

// Shows RSOD (Red Screen of Death) using Rust GUI.
void rsod_gui(const systask_postmortem_t* pminfo);

#ifdef KERNEL_MODE

// Universal panic handler that can be passed to `system_init()` function
// to show RSOD screen describing the system error.
// (may be called from interrupt context)
void rsod_panic_handler(const systask_postmortem_t* pminfo);

#endif  // KERNEL_MODE

#endif  // LIB_RSOD_H
