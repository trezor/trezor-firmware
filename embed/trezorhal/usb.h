/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#define USB_EP_DIR_MASK     0x80
#define USB_EP_DIR_OUT      0x00
#define USB_EP_DIR_IN       0x80

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

typedef enum {
    USB_LANGID_ENGLISH_US = 0x409,
} usb_language_id_t;

typedef struct {
    const char *manufacturer;
    const char *product;
    const char *serial_number;
    const char *interface;
} usb_dev_string_table_t;

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

typedef enum {
    USB_IFACE_TYPE_DISABLED = 0,
    USB_IFACE_TYPE_VCP      = 1,
    USB_IFACE_TYPE_HID      = 2,
    USB_IFACE_TYPE_WEBUSB   = 3,
} usb_iface_type_t;

#include "usb_hid-defs.h"
#include "usb_vcp-defs.h"
#include "usb_webusb-defs.h"

typedef struct {
    union {
        usb_hid_state_t hid;
        usb_vcp_state_t vcp;
        usb_webusb_state_t webusb;
    };
    usb_iface_type_t type;
} usb_iface_t;

void usb_init(const usb_dev_info_t *dev_info);
void usb_deinit(void);
void usb_start(void);
void usb_stop(void);

#endif
