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

#include <sys/systask.h>

// Currently, the emulator runs in single-task mode, so all
// task-related functions are stubs that allow compiling and
// running the emulator without multitasking support.

systask_t* systask_active(void) { return NULL; }

systask_t* systask_kernel(void) { return NULL; }

systask_id_t systask_id(const systask_t* task) { return 0; }

void systask_yield_to(systask_t* task) {}
