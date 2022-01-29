/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (C) 2017 Saleem Rashid <trezor@saleemrashid.com>
 *
 * This library is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with this library.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <stdint.h>

#include "usb.h"

#include "debug.h"
#include "messages.h"
#include "timer.h"

static volatile char tiny = 0;

void usbInit(void) { emulatorSocketInit(); }

#if DEBUG_LINK
#define _ISDBG (((iface == 1) ? 'd' : 'n'))
#else
#define _ISDBG ('n')
#endif

void usbSleep(uint32_t millis) {
  emulatorPoll();

  static uint8_t buffer[USB_PACKET_SIZE];

  int iface = 0;
  if (emulatorSocketRead(&iface, buffer, sizeof(buffer), millis) > 0) {
    if (!tiny) {
      do {
        msg_read_common(_ISDBG, buffer, sizeof(buffer));
      } while (emulatorSocketRead(&iface, buffer, sizeof(buffer), 0) > 0);
    } else {
      msg_read_tiny(buffer, sizeof(buffer));
    }
  }

  const uint8_t *data;
  while ((data = msg_out_data()) != NULL) {
    emulatorSocketWrite(0, data, USB_PACKET_SIZE);
  }

#if DEBUG_LINK
  while ((data = msg_debug_out_data()) != NULL) {
    emulatorSocketWrite(1, data, USB_PACKET_SIZE);
  }
#endif
}

void usbPoll(void) { usbSleep(0); }

char usbTiny(char set) {
  char old = tiny;
  tiny = set;
  return old;
}

void usbFlush(uint32_t millis) { usbSleep(millis); }
