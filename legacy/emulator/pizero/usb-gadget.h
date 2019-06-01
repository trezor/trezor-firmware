/*
 * Copyright (C) 2009 Daiki Ueno <ueno@unixuser.org>
 * Modified Copyright (C) 2018, 2019 Yannick Heneault <yheneaul@gmail.com>
 * This file is part of libusb-gadget.
 *
 * libusb-gadget is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Lesser General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * libusb-gadget is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public License
 * along with Foobar.  If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef __USG_H
#define __USG_H

#include <endian.h>
#include <stdint.h>

/* borrowed from libusb/libusb.h */
#define usb_gadget_bswap16(x) (((x & 0xFF) << 8) | (x >> 8))
#define usb_gadget_bswap32(x) ((usb_gadget_bswap16(x & 0xFFFF) << 16) | usb_gadget_bswap16(x >> 16))
/* borrowed from libusb/libusb.h */
#if __BYTE_ORDER == __LITTLE_ENDIAN
#define usb_gadget_cpu_to_le16(x) (x)
#define usb_gadget_le16_to_cpu(x) (x)
#define usb_gadget_cpu_to_le32(x) (x)
#define usb_gadget_le32_to_cpu(x) (x)
#elif __BYTE_ORDER == __BIG_ENDIAN
#define usb_gadget_cpu_to_le16(x) usb_gadget_bswap16(x)
#define usb_gadget_le16_to_cpu(x) usb_gadget_bswap16(x)
#define usb_gadget_cpu_to_le32(x) usb_gadget_bswap32(x)
#define usb_gadget_le32_to_cpu(x) usb_gadget_bswap32(x)
#else
#error "Unrecognized endianness"
#endif

struct usb_gadget_string
{
  uint8_t id;
  const char *s;
};

struct usb_gadget_strings
{
  uint16_t language;	/* 0x0409 for en-us */
  struct usb_gadget_string *strings;
};

struct usb_gadget_endpoint
{
  char *name;
};

enum usb_gadget_event_type {
  USG_EVENT_ENDPOINT_ENABLE,
  USG_EVENT_ENDPOINT_DISABLE,
  USG_EVENT_CONNECT,
  USG_EVENT_DISCONNECT,
  USG_EVENT_SUSPEND,
  USG_EVENT_CONTROL_REQUEST,
  USG_EVENT_SET_CONFIG
};

struct usb_gadget_event
{
  enum usb_gadget_event_type type;
  union
  {
    int number;
    struct usb_ctrlrequest *req;
  } u;
};

struct usb_gadget_dev_handle;
typedef struct usb_gadget_dev_handle usb_gadget_dev_handle;

struct usb_gadget_device
{
  struct usb_device_descriptor *device;
  struct usb_descriptor_header **config, **hs_config;
  struct usb_gadget_strings *strings;
};

struct usb_gadget_endpoint *usb_gadget_endpoint (usb_gadget_dev_handle *, int);
int usb_gadget_endpoint_close (struct usb_gadget_endpoint *);
ssize_t usb_gadget_endpoint_write (struct usb_gadget_endpoint *, const void *, size_t);
ssize_t usb_gadget_endpoint_read (struct usb_gadget_endpoint *, void *, size_t);

usb_gadget_dev_handle *usb_gadget_open (struct usb_gadget_device *);
int usb_gadget_close (usb_gadget_dev_handle *);

typedef int (*usb_gadget_event_cb) (usb_gadget_dev_handle *, struct usb_gadget_event *, void *);
void usb_gadget_set_event_cb (usb_gadget_dev_handle *, usb_gadget_event_cb, void *);
void usb_gadget_set_debug_level (usb_gadget_dev_handle *, int);
int usb_gadget_handle_control_event (usb_gadget_dev_handle *);
int usb_gadget_control_fd (usb_gadget_dev_handle *);

#endif
