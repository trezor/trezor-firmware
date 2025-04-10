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

// Event sources that can be signaled by the system or device drivers
typedef enum {
  SYSHANDLE_USB_IFACE_0,
  SYSHANDLE_USB_IFACE_7 = SYSHANDLE_USB_IFACE_0 + 7,
  SYSHANDLE_BLE_IFACE_0,
  // SYSHANDLE_BLE_IFACE_N = SYSHANDLE_BLE_IFACE_0 + N - 1,
  SYSHANDLE_POWERCTL,
  SYSHANDLE_BUTTON,
  SYSHANDLE_TOUCH,
  SYSHANDLE_USB,
  SYSHANDLE_BLE,
  SYSHANDLE_COUNT,
} syshandle_t;

// Bitmask of event sources
typedef uint32_t syshandle_mask_t;

typedef struct {
  // Bitmask of handles ready for reading
  syshandle_mask_t read_ready;
  // Bitmask of handles ready for writing
  syshandle_mask_t write_ready;
} sysevents_t;  // sys_events_t

// Polls for the specified events. The function blocks until at least
// one event is signaled or deadline expires.
//
// Multiple events may be signaled simultaneously.
//
// Returns the events that were signaled. If the timeout expires, both
// fields in the result are set to 0.
void sysevents_poll(const sysevents_t* awaited, sysevents_t* signalled,
                    uint32_t deadline);
