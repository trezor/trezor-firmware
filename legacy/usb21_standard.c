/*
 * Copyright (c) 2016, Devan Lai
 *
 * Permission to use, copy, modify, and/or distribute this software
 * for any purpose with or without fee is hereby granted, provided
 * that the above copyright notice and this permission notice
 * appear in all copies.
 *
 * THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
 * WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE
 * AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR
 * CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
 * LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
 * NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
 * CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
 */

#include "usb21_standard.h"
#include <stdint.h>
#include <string.h>
#include "random_delays.h"
#include "util.h"

static uint16_t build_bos_descriptor(const struct usb_bos_descriptor *bos,
                                     uint8_t *buf, uint16_t len) {
  uint8_t *tmpbuf = buf;
  uint16_t count = 0, total = 0, totallen = 0;
  uint16_t i = 0;

  memcpy(buf, bos, count = MIN(len, bos->bLength));
  buf += count;
  len -= count;
  total += count;
  totallen += bos->bLength;

  /* For each device capability */
  for (i = 0; i < bos->bNumDeviceCaps; i++) {
    /* Copy device capability descriptor. */
    const struct usb_device_capability_descriptor *cap = bos->capabilities[i];

    memcpy(buf, cap, count = MIN(len, cap->bLength));
    buf += count;
    len -= count;
    total += count;
    totallen += cap->bLength;
  }

  /* Fill in wTotalLength. */
  *(uint16_t *)(tmpbuf + 2) = totallen;

  return total;
}

static const struct usb_bos_descriptor *usb21_bos;

static enum usbd_request_return_codes usb21_standard_get_descriptor(
    usbd_device *usbd_dev, struct usb_setup_data *req, uint8_t **buf,
    uint16_t *len, usbd_control_complete_callback *complete) {
  (void)complete;
  (void)usbd_dev;

  wait_random();

  if (req->bRequest == USB_REQ_GET_DESCRIPTOR) {
    int descr_type = req->wValue >> 8;
    if (descr_type == USB_DT_BOS) {
      if (!usb21_bos) {
        return USBD_REQ_NOTSUPP;
      }
      *len = MIN_8bits(*len, build_bos_descriptor(usb21_bos, *buf, *len));
      return USBD_REQ_HANDLED;
    }
  }

  return USBD_REQ_NEXT_CALLBACK;
}

static void usb21_set_config(usbd_device *usbd_dev, uint16_t wValue) {
  (void)wValue;

  usbd_register_control_callback(
      usbd_dev, USB_REQ_TYPE_IN | USB_REQ_TYPE_STANDARD | USB_REQ_TYPE_DEVICE,
      USB_REQ_TYPE_DIRECTION | USB_REQ_TYPE_TYPE | USB_REQ_TYPE_RECIPIENT,
      &usb21_standard_get_descriptor);
}

void usb21_setup(usbd_device *usbd_dev,
                 const struct usb_bos_descriptor *binary_object_store) {
  usb21_bos = binary_object_store;

  /* Register the control request handler _before_ the config is set */
  usb21_set_config(usbd_dev, 0x0000);
  usbd_register_set_config_callback(usbd_dev, usb21_set_config);
}
