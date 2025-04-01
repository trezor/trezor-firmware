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

#ifndef TREZORHAL_APPLET_H
#define TREZORHAL_APPLET_H

#include <trezor_types.h>

#ifdef SYSCALL_DISPATCH

#include <sys/systask.h>

// Applet entry point
typedef void (*applet_startup_t)(const char* args, uint32_t random);

typedef struct {
  uint32_t start;
  uint32_t size;
} applet_memory_t;

// Applet header found at the beginning of the applet binary
typedef struct {
  // Stack area
  applet_memory_t stack;
  // Applet entry point
  applet_startup_t startup;
} applet_header_t;

// Applet memory layout
typedef struct {
  // Read/write data area #1
  applet_memory_t data1;
  // Read/write data area #2
  applet_memory_t data2;
  // Read-only code area #1
  applet_memory_t code1;
  // Read-only code area #2
  applet_memory_t code2;

} applet_layout_t;

// Applet privileges
typedef struct {
  bool assets_area_access;
} applet_privileges_t;

typedef struct {
  // Points to the applet header found at the beginning of the applet binary
  applet_header_t* header;
  // Applet memory layout describing the memory areas
  // the applet is allowed to use
  applet_layout_t layout;
  // Applet privileges
  applet_privileges_t privileges;

  // Applet task
  systask_t task;

} applet_t;

// Initializes the applet structure
void applet_init(applet_t* applet, applet_header_t* header,
                 applet_layout_t* layout, applet_privileges_t* privileges);

// Resets the applet and prepares it for execution from its entry point.
//
// Applet does not start immediately, it needs to be run by
// `applet_run()` after calling this function.
//
// Returns `true` if the applet was successfully reset.
bool applet_reset(applet_t* applet, uint32_t cmd, const void* arg,
                  size_t arg_size);

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

#endif  // SYSCALL_DISPATCH

#endif  // TREZORHAL_APPLET_H
