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

#ifdef KERNEL

#include <sys/systask.h>

// Applet privileges
typedef struct {
  bool assets_area_access;
} applet_privileges_t;

typedef struct {
  // Applet memory layout describing the memory areas
  // the applet is allowed to use
  applet_layout_t layout;
  // Applet privileges
  applet_privileges_t privileges;
  // Applet task
  systask_t task;
#ifdef TREZOR_EMULATOR
  // Handle returned by `dlopen()`
  void* handle;
#endif
} applet_t;

// Initializes the applet structure
void applet_init(applet_t* applet, const applet_layout_t* layout,
                 const applet_privileges_t* privileges);

// Runs the applet and waits until it finishes.
void applet_run(applet_t* applet);

// Release all resources help by the applet
void applet_stop(applet_t* applet);

// Returns `true` if the applet task is alive.
bool applet_is_alive(applet_t* applet);

// Returns the currently active applet.
//
// Returns `NULL` if no applet is currently active.
applet_t* applet_active(void);

#endif  // KERNEL
