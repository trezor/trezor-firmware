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

#include <stddef.h>
#include <stdint.h>

#ifdef SYSCALL_DISPATCH

#include "systask.h"

// Applet entry point
typedef void (*applet_startup_t)(const char* args, uint32_t random);

// Applet header found at the beginning of the applet binary
typedef struct {
  // Stack area
  uint32_t stack_start;
  uint32_t stack_size;
  // Applet entry point
  applet_startup_t startup;
} applet_header_t;

// Applet memory layout
typedef struct {
  // Data area 1
  uint32_t data1_start;
  uint32_t data1_size;
  // Data area 2
  uint32_t data2_start;
  uint32_t data2_size;

} applet_layout_t;

typedef struct {
  // Points to the applet header found at the beginning of the applet binary
  applet_header_t* header;
  // Applet memory layout describing the memory areas
  // the applet is allowed to use
  applet_layout_t layout;
  // Applet task
  systask_t task;

  // + privileges

} applet_t;

// Initializes the applet structure
void applet_init(applet_t* applet, applet_header_t* header,
                 applet_layout_t* layout);

// Resets the applet and prepares it for execution from its entry point.
//
// Applet does not start immediately, it needs to be scheduled by
// `systask_yield_to(&applet->task)` after calling this function.
void applet_reset(applet_t* applet, uint32_t cmd, const void* arg,
                  size_t arg_size);

#endif  // SYSCALL_DISPATCH

#endif  // TREZORHAL_APPLET_H