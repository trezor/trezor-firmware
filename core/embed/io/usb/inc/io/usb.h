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

#define USB_PACKET_LEN 64

typedef enum {
  USB_EVENT_NONE = 0,
  USB_EVENT_CONFIGURED = 1,
  USB_EVENT_DECONFIGURED = 2,
} usb_event_t;

typedef union {
  bool configured;
} usb_state_t;

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

#define USB_MAX_STR_SIZE 62

typedef struct {
  uint8_t device_class;
  uint8_t device_subclass;
  uint8_t device_protocol;
  uint16_t vendor_id;
  uint16_t product_id;
  uint16_t release_num;
  char manufacturer[USB_MAX_STR_SIZE + 1];
  char product[USB_MAX_STR_SIZE + 1];
  char serial_number[USB_MAX_STR_SIZE + 1];
  char interface[USB_MAX_STR_SIZE + 1];
  secbool usb21_enabled;
  secbool usb21_landing;
} usb_dev_info_t;

typedef struct {
  char serial_number[USB_MAX_STR_SIZE + 1];
  secbool usb21_landing;
} usb_start_params_t;

/**
 * Initializes the USB stack driver.
 *
 * When the USB driver is initialized, class drivers can be registered using
 * `usb_xxx_add()` functions. After all class drivers are registered,
 * `usb_start` can be called.
 *
 * @param dev_info Pointer to USB device information structure.
 * @return `sectrue` if the initialization is successful.
 */
secbool usb_init(const usb_dev_info_t *dev_info);

/**
 * Deinitializes the USB stack.
 *
 * This function completely deinitializes the USB driver and all class drivers.
 * After this function is called, `usb_init` can be called again.
 */
void usb_deinit(void);

/**
 * Starts the USB stack and registered class drivers.
 *
 * @param params Parameter that can be used to change some
 * settings specified during USB stack initialization. May be `NULL`.
 *
 * @return `sectrue` if the USB stack is started successfully.
 */
secbool usb_start(const usb_start_params_t *params);

/**
 * Stops the USB stack but leaves all configuration intact,
 * so it can be re-started again with @ref usb_start.
 *
 * When the USB stack is stopped, it does not respond to any USB events and
 * the CPU can go to stop/standby mode.
 */
void usb_stop(void);

/**
 * @brief Reads a USB event.
 *
 * @return USB_EVENT_NONE if no event is available.
 */
usb_event_t usb_get_event(void);

/**
 * @brief Reads the USB state into the provided structure.
 *
 * @param state Pointer to a @ref usb_state_t structure to receive the
 * current state.
 */
void usb_get_state(usb_state_t *state);
