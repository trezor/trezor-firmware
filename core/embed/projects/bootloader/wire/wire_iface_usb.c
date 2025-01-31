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

#define USB_TIMEOUT 500
#define USB_PACKET_SIZE 64
#define USB_IFACE_NUM 0

_Static_assert(USB_PACKET_SIZE <= MAX_PACKET_SIZE, "USB_PACKET_SIZE too large");

static bool usb_write(uint8_t* data, size_t size) {
  if (size != USB_PACKET_SIZE) {
    return false;
  }

  int r = usb_webusb_write_blocking(USB_IFACE_NUM, data, size, USB_TIMEOUT);

  return r == size;
}

static int usb_read(uint8_t* buffer, size_t buffer_size) {
  if (buffer_size != USB_PACKET_SIZE) {
    return -1;
  }

  int r = usb_webusb_read_blocking(USB_IFACE_NUM, buffer, USB_PACKET_SIZE,
                                   USB_TIMEOUT);

  return r;
}

static void usb_error(void) {
  error_shutdown_ex("USB ERROR",
                    "Error reading from USB. Try different USB cable.", NULL);
}

static void usb_init_all(secbool usb21_landing) {
  usb_dev_info_t dev_info = {
      .device_class = 0x00,
      .device_subclass = 0x00,
      .device_protocol = 0x00,
      .vendor_id = 0x1209,
      .product_id = 0x53C0,
      .release_num = 0x0200,
      .manufacturer = MODEL_USB_MANUFACTURER,
      .product = MODEL_USB_PRODUCT,
      .serial_number = "000000000000000000000000",
      .interface = "TREZOR Interface",
      .usb21_enabled = sectrue,
      .usb21_landing = usb21_landing,
  };

  static uint8_t rx_buffer[USB_PACKET_SIZE];

  static const usb_webusb_info_t webusb_info = {
      .iface_num = USB_IFACE_NUM,
#ifdef TREZOR_EMULATOR
      .emu_port = 21324,
#else
      .ep_in = 0x01,
      .ep_out = 0x01,
#endif
      .subclass = 0,
      .protocol = 0,
      .max_packet_len = sizeof(rx_buffer),
      .rx_buffer = rx_buffer,
      .polling_interval = 1,
  };

  ensure(usb_init(&dev_info), NULL);

  ensure(usb_webusb_add(&webusb_info), NULL);

  ensure(usb_start(), NULL);
}

void usb_iface_init(wire_iface_t* iface, secbool usb21_landing) {
  usb_init_all(usb21_landing);

  memset(iface, 0, sizeof(wire_iface_t));

  iface->poll_iface_id = USB_IFACE_NUM;
  iface->tx_packet_size = USB_PACKET_SIZE;
  iface->rx_packet_size = USB_PACKET_SIZE;
  iface->write = &usb_write;
  iface->read = &usb_read;
  iface->error = &usb_error;
}

void usb_iface_deinit(wire_iface_t* iface) {
  memset(iface, 0, sizeof(wire_iface_t));
  usb_deinit();
}
