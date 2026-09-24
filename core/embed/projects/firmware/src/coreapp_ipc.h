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

#include <sys/systask.h>

/**
 * Task the coreapp exchanges IPC messages with.
 *
 * Task IDs are zero-based indices (see `systask_id_t`): 0 is the kernel, 1 the
 * coreapp itself, 2 the loaded user app. Only meaningful with `USE_APP_LOADING`
 * enabled, which is also what raises `SYSTASK_MAX_TASKS` to 3.
 *
 * TODO: replace with a task id obtained from the applet/app-arena layer once
 * one is exposed, rather than assuming the single extapp slot.
 */
#define IPC_REMOTE_EXTAPP ((systask_id_t)2)
// Size of the IPC receive buffer registered by the coreapp
#define IPC_COREAPP_BUFFER_SIZE (32 * 1024)
