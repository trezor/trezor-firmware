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

#include <stdint.h>
#include "secbool.h"

#include "usb_hid.h"
#include "usb_vcp.h"
#include "usb_webusb.h"

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

void usb_init(const usb_dev_info_t *dev_info);
void usb_deinit(void);
void usb_start(void);
void usb_stop(void);
secbool usb_configured(void);

#endif
