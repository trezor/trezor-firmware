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

#ifndef __TREZORHAL_USB_H__
#define __TREZORHAL_USB_H__

#include <trezor_types.h>

#include <io/usb_hid.h>
#include <io/usb_vcp.h>
#include <io/usb_webusb.h>

// clang-format off
//
// USB stack high-level state machine
// ------------------------------------
//
//              +---------------+
//        ----> | Uninitialized |   - Stack is completely uninitialized
//        |     +---------------+
//        |            |
//        |         usb_init()
//   usb_deinit()      |
//        |            v
//        |     +---------------+   - Stack is partially initialized
//        |-----|  Initialized  |   - Ready for class registration
//        |     +---------------+
//        |            |
//        |       N x usb_xxx_add() - Multiple class drivers can be registered
//        |            |
//        |            v
//        |     +---------------+   - Stack is completely initialized
//        |-----|    Stopped    |   - USB hardware left uninitialized
//        |     +---------------+   - Can go low power at this mode
//        |        |        ^
//        |    usb_start()  |
//        |        |     usb_stop()
//        |        v        |
//        |     +---------------+   - USB hardware initialized
//        ------|    Running    |   - Stack is running if the USB host is connected
//              +---------------+
//
// clang-format on

typedef struct {
  uint8_t device_class;
  uint8_t device_subclass;
  uint8_t device_protocol;
  uint16_t vendor_id;
  uint16_t product_id;
  uint16_t release_num;
  const char *manufacturer;
  const char *product;
  const char *serial_number;
  const char *interface;
  secbool usb21_enabled;
  secbool usb21_landing;
} usb_dev_info_t;

// Initializes USB stack
//
// When the USB driver is initialized, class drivers can be registered.
// After all class drivers are registered, `usb_start()` can  be called.
//
// Returns `sectrue` if the initialization is successful.
secbool usb_init(const usb_dev_info_t *dev_info);

// Deinitialize USB stack
//
// This function completely deinitializes the USB driver and all class drivers.
// After this function is called, `usb_init()` can be called again.
void usb_deinit(void);

// Starts USB driver and its class drivers
//
// Initializes the USB stack (and hardware) and starts all registered class
// drivers.
//
// This function can called after all class drivers are registered or after
// `usb_stop()` is called.
//
// Returns `sectrue` if the USB stack is started successfully.
secbool usb_start(void);

// Stops USB driver and its class drivers
//
// Unitializes the USB stack (and hardware) but leaves all configuration intact,
// so it can be started again with `usb_start()`.
//
// When the USB stack is stopped, it does not respond to any USB events and
// the CPU can go to stop/standby mode.
void usb_stop(void);

// Returns `sectrue` if the device is connected to the host (or is expected to
// be)
//
// TODO: Review and clarify the logic of this function in the future
secbool usb_configured(void);

#endif
