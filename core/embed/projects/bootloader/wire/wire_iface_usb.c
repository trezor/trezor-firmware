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

#include <trezor_model.h>
#include <trezor_rtl.h>

#include "wire_iface_usb.h"

#include <io/usb.h>
#include <sys/sysevent.h>

#define USB_TIMEOUT 500
#define USB_PACKET_SIZE 64

_Static_assert(USB_PACKET_SIZE <= MAX_PACKET_SIZE, "USB_PACKET_SIZE too large");

static wire_iface_t g_usb_iface = {0};

static bool usb_write(uint8_t* data, size_t size) {
  if (size != USB_PACKET_SIZE) {
    return false;
  }

  ssize_t r =
      syshandle_write_blocking(SYSHANDLE_USB_WIRE, data, size, USB_TIMEOUT);

  return r == size;
}

static int usb_read(uint8_t* buffer, size_t buffer_size) {
  if (buffer_size != USB_PACKET_SIZE) {
    return -1;
  }

  ssize_t r = syshandle_read_blocking(SYSHANDLE_USB_WIRE, buffer, buffer_size,
                                      USB_TIMEOUT);

  return r;
}

static void usb_error(void) {
  error_shutdown_ex("USB ERROR",
                    "Error reading from USB. Try different USB cable.", NULL);
}

wire_iface_t* usb_iface_init(secbool usb21_landing) {
  wire_iface_t* iface = &g_usb_iface;

  if (iface->initialized) {
    return iface;
  }

  usb_start_params_t params = {
      .serial_number = "000000000000000000000000",
      .usb21_landing = usb21_landing,
  };

  usb_start(&params);

  memset(iface, 0, sizeof(wire_iface_t));

  iface->poll_iface_id = SYSHANDLE_USB_WIRE;
  iface->tx_packet_size = USB_PACKET_SIZE;
  iface->rx_packet_size = USB_PACKET_SIZE;
  iface->write = &usb_write;
  iface->read = &usb_read;
  iface->error = &usb_error;
  iface->initialized = true;
  iface->wireless = false;

  return iface;
}

void usb_iface_deinit(void) {
  wire_iface_t* iface = &g_usb_iface;

  if (!iface->initialized) {
    return;
  }

  memset(iface, 0, sizeof(wire_iface_t));
  usb_stop();
}
