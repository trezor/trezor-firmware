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

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include "poll.h"

#include <io/usb.h>
#include <sys/systick.h>

#ifdef USE_BLE
#include <io/ble.h>
#endif

#ifdef USE_BUTTON
#include <io/button.h>
#endif

#ifdef USE_TOUCH
#include <io/touch.h>
#endif

#ifdef TREZOR_EMULATOR
#include "SDL.h"
#endif

int16_t poll_events(const uint16_t* ifaces, size_t ifaces_num,
                    poll_event_t* event, uint32_t timeout_ms) {
  uint32_t deadline = ticks_timeout(timeout_ms);

  while (!ticks_expired(deadline)) {
#ifdef TREZOR_EMULATOR
    // Ensures that SDL events are processed. This prevents the emulator from
    // freezing when the user interacts with the window.
    SDL_PumpEvents();
#endif

    for (size_t i = 0; i < ifaces_num; i++) {
      uint8_t iface_num = ifaces[i] & 0xFF;
      if (iface_num < IFACE_USB_MAX) {
        if ((ifaces[i] & MODE_READ) == MODE_READ) {
          // check if USB can read
          if (sectrue == usb_webusb_can_read(iface_num)) {
            event->event.usb_data_event = EVENT_USB_CAN_READ;
            return iface_num;
          }
        }
      }
#ifdef USE_BLE
      if (iface_num == IFACE_BLE) {
        if ((ifaces[i] & MODE_READ) == MODE_READ) {
          // check if BLE can read
          if (ble_can_read()) {
            event->event.ble_data_event = EVENT_BLE_CAN_READ;
            return iface_num;
          }
        }
      }
      if (iface_num == IFACE_BLE_EVENT) {
        ble_event_t ble_event = {0};
        if (ble_get_event(&ble_event)) {
          memcpy(&event->event.ble_event, &ble_event, sizeof(ble_event_t));
          return iface_num;
        }
      }
#endif
#ifdef USE_BUTTON
      if (iface_num == IFACE_BUTTON) {
        uint32_t btn_event = button_get_event();
        uint32_t etype = (btn_event >> 24) & 0x3U;  // button down/up
        uint32_t btn_number = btn_event & 0xFFFF;
        if (etype != 0) {
          event->event.button_event.type = etype;
          event->event.button_event.button = btn_number;
          return iface_num;
        }
      }
#endif
    }

#ifndef TREZOR_EMULATOR
    __WFI();
#endif
  }

  return -1;
}
