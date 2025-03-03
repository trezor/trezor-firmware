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

#include <io/usb.h>

#ifdef USE_BLE
#include <io/ble.h>
#endif
#ifdef USE_BUTTON
#include <io/button.h>
#endif

#define IFACE_USB_MAX (15)  // 0-15 reserved for USB
#define IFACE_BLE (16)
#define IFACE_BLE_EVENT (252)
#define IFACE_BUTTON (254)
#define IFACE_TOUCH (255)

#define MODE_READ 0x0000
#define MODE_WRITE 0x0100

typedef enum {
  EVENT_USB_CAN_READ,
} usb_data_event_type_t;

#ifdef USE_BLE
typedef enum {
  EVENT_BLE_CAN_READ,
} ble_data_event_type_t;
#endif

#ifdef USE_BUTTON
typedef struct {
  uint32_t type;
  button_t button;
} button_event_t;
#endif

typedef struct {
  union {
    usb_data_event_type_t usb_data_event;
    usb_event_t usb_event;
#ifdef USE_BLE
    ble_data_event_type_t ble_data_event;
    ble_event_t ble_event;
#endif
#ifdef USE_BUTTON
    button_event_t button_event;
#endif

  } event;
} poll_event_t;

int16_t poll_events(const uint16_t* ifaces, size_t ifaces_num,
                    poll_event_t* event, uint32_t timeout_ms);
