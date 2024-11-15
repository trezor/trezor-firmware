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

#ifndef TREZORHAL_USBD_INTERNAL_H
#define TREZORHAL_USBD_INTERNAL_H

#include <trezor_types.h>

#include "usbd_core.h"

#define USB_EP_DIR_MASK 0x80
#define USB_EP_DIR_OUT 0x00
#define USB_EP_DIR_IN 0x80

#define USB_WEBUSB_VENDOR_CODE 0x01   // arbitrary
#define USB_WEBUSB_LANDING_PAGE 0x01  // arbitrary

typedef struct __attribute__((packed)) {
  uint8_t bLength;
  uint8_t bDescriptorType;
  uint16_t bcdUSB;
  uint8_t bDeviceClass;
  uint8_t bDeviceSubClass;
  uint8_t bDeviceProtocol;
  uint8_t bMaxPacketSize0;
  uint16_t idVendor;
  uint16_t idProduct;
  uint16_t bcdDevice;
  uint8_t iManufacturer;
  uint8_t iProduct;
  uint8_t iSerialNumber;
  uint8_t bNumConfigurations;
} usb_device_descriptor_t;

typedef struct __attribute__((packed)) {
  uint8_t bLength;
  uint8_t bDescriptorType;
  uint16_t wData;
} usb_langid_descriptor_t;

typedef enum {
  USB_LANGID_ENGLISH_US = 0x409,
} usb_language_id_t;

typedef struct __attribute__((packed)) {
  uint8_t bLength;
  uint8_t bDescriptorType;
  uint16_t wTotalLength;
  uint8_t bNumInterfaces;
  uint8_t bConfigurationValue;
  uint8_t iConfiguration;
  uint8_t bmAttributes;
  uint8_t bMaxPower;
} usb_config_descriptor_t;

typedef struct __attribute__((packed)) {
  uint8_t bLength;
  uint8_t bDescriptorType;
  uint8_t bInterfaceNumber;
  uint8_t bAlternateSetting;
  uint8_t bNumEndpoints;
  uint8_t bInterfaceClass;
  uint8_t bInterfaceSubClass;
  uint8_t bInterfaceProtocol;
  uint8_t iInterface;
} usb_interface_descriptor_t;

typedef struct __attribute__((packed)) {
  uint8_t bLength;
  uint8_t bDescriptorType;
  uint8_t bFirstInterface;
  uint8_t bInterfaceCount;
  uint8_t bFunctionClass;
  uint8_t bFunctionSubClass;
  uint8_t bFunctionProtocol;
  uint8_t iFunction;
} usb_interface_assoc_descriptor_t;

typedef struct __attribute__((packed)) {
  uint8_t bLength;
  uint8_t bDescriptorType;
  uint8_t bEndpointAddress;
  uint8_t bmAttributes;
  uint16_t wMaxPacketSize;
  uint8_t bInterval;
} usb_endpoint_descriptor_t;

// Number of reserved bytes for the state of each class.
#define USBD_CLASS_STATE_MAX_SIZE 128

// Returns the pointer to class state structure reserved for the
// specified interface number.
//
// The function checks if the interface number is valid and the type
// matches and returns NULL if not. If the `class` is NULL, the function
// returns the valid pointer only if the slot is empty.
//
// The returned array has `USBD_CLASS_STATE_MAX_SIZE` bytes
// and is aligned to 8-byte boundary.
void *usb_get_iface_state(uint8_t iface_num, const USBD_ClassTypeDef *class);

// Assigns the concrete class to the slot `iface_num`.
void usb_set_iface_class(uint8_t iface_num, const USBD_ClassTypeDef *class);

// Allocates the buffer for the class driver descriptors
// (interface, endpoint, ...) inside the USB device structure.
//
// The callee must fill the whole buffer with the descriptors.
//
// The function checks if the remaining space is enough and
// returns NULL if not.
void *usb_alloc_class_descriptors(size_t desc_len);

#endif  // TREZORHAL_USBD_INTERNAL_H
