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

#define IFACE_USB_MAX (15)  // 0-15 reserved for USB

#define MODE_READ 0x0000
#define MODE_WRITE 0x0100

typedef enum {
  EVENT_NONE = 0,
  EVENT_USB_CAN_READ = 0x01,
} poll_event_type_t;

typedef struct {
  poll_event_type_t type;
} poll_event_t;

uint8_t poll_events(const uint16_t* ifaces, size_t ifaces_num,
                    poll_event_t* event, uint32_t timeout_ms);
