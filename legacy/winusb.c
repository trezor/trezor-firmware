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

#include "winusb.h"
#include <libopencm3/usb/usbd.h>
#include "random_delays.h"
#include "util.h"

static int usb_descriptor_type(uint16_t wValue) { return wValue >> 8; }

static int usb_descriptor_index(uint16_t wValue) { return wValue & 0xFF; }

static struct winusb_compatible_id_descriptor winusb_wcid = {
    .header =
        {
            .dwLength =
                sizeof(struct winusb_compatible_id_descriptor_header) +
                1 * sizeof(struct winusb_compatible_id_function_section),
            .bcdVersion = WINUSB_BCD_VERSION,
            .wIndex = WINUSB_REQ_GET_COMPATIBLE_ID_FEATURE_DESCRIPTOR,
            .bNumSections = 1,
            .reserved = {0, 0, 0, 0, 0, 0, 0},
        },
    .functions = {
        {// note - bInterfaceNumber is rewritten in winusb_setup with the
         // correct interface number
         .bInterfaceNumber = 0,
         .reserved0 = {1},
         .compatibleId = "WINUSB",
         .subCompatibleId = "",
         .reserved1 = {0, 0, 0, 0, 0, 0}},
    }};

static const struct usb_string_descriptor winusb_string_descriptor = {
    .bLength = 0x12,
    .bDescriptorType = USB_DT_STRING,
    .wData = WINUSB_EXTRA_STRING};

static const struct winusb_extended_properties_descriptor guid = {
    .header =
        {
            .dwLength =
                sizeof(struct winusb_extended_properties_descriptor_header) +
                1 * sizeof(
                        struct winusb_extended_properties_feature_descriptor),
            .bcdVersion = WINUSB_BCD_VERSION,
            .wIndex = WINUSB_REQ_GET_EXTENDED_PROPERTIES_OS_FEATURE_DESCRIPTOR,
            .wNumFeatures = 1,
        },
    .features = {
        {
            .dwLength =
                sizeof(struct winusb_extended_properties_feature_descriptor),
            .dwPropertyDataType = WINUSB_EXTENDED_PROPERTIES_MULTISZ_DATA_TYPE,
            .wNameLength = WINUSB_EXTENDED_PROPERTIES_GUID_NAME_SIZE_C,
            .name = WINUSB_EXTENDED_PROPERTIES_GUID_NAME,
            .dwPropertyDataLength = WINUSB_EXTENDED_PROPERTIES_GUID_DATA_SIZE_C,
            .propertyData = WINUSB_EXTENDED_PROPERTIES_GUID_DATA,
        },
    }};

static enum usbd_request_return_codes winusb_descriptor_request(
    usbd_device *usbd_dev, struct usb_setup_data *req, uint8_t **buf,
    uint16_t *len, usbd_control_complete_callback *complete) {
  (void)complete;
  (void)usbd_dev;

  wait_random();

  if ((req->bmRequestType & USB_REQ_TYPE_TYPE) != USB_REQ_TYPE_STANDARD) {
    return USBD_REQ_NEXT_CALLBACK;
  }

  if (req->bRequest == USB_REQ_GET_DESCRIPTOR &&
      usb_descriptor_type(req->wValue) == USB_DT_STRING) {
    if (usb_descriptor_index(req->wValue) == WINUSB_EXTRA_STRING_INDEX) {
      *buf = (uint8_t *)(&winusb_string_descriptor);
      *len = MIN_8bits(*len, winusb_string_descriptor.bLength);
      return USBD_REQ_HANDLED;
    }
  }
  return USBD_REQ_NEXT_CALLBACK;
}

static enum usbd_request_return_codes winusb_control_vendor_request(
    usbd_device *usbd_dev, struct usb_setup_data *req, uint8_t **buf,
    uint16_t *len, usbd_control_complete_callback *complete) {
  (void)complete;
  (void)usbd_dev;

  wait_random();

  if (req->bRequest != WINUSB_MS_VENDOR_CODE) {
    return USBD_REQ_NEXT_CALLBACK;
  }

  int status = USBD_REQ_NOTSUPP;
  if (((req->bmRequestType & USB_REQ_TYPE_RECIPIENT) == USB_REQ_TYPE_DEVICE) &&
      (req->wIndex == WINUSB_REQ_GET_COMPATIBLE_ID_FEATURE_DESCRIPTOR)) {
    *buf = (uint8_t *)(&winusb_wcid);
    *len = MIN_8bits(*len, winusb_wcid.header.dwLength);
    status = USBD_REQ_HANDLED;

  } else if (((req->bmRequestType & USB_REQ_TYPE_RECIPIENT) ==
              USB_REQ_TYPE_INTERFACE) &&
             (req->wIndex ==
              WINUSB_REQ_GET_EXTENDED_PROPERTIES_OS_FEATURE_DESCRIPTOR) &&
             (usb_descriptor_index(req->wValue) ==
              winusb_wcid.functions[0].bInterfaceNumber)) {
    *buf = (uint8_t *)(&guid);
    *len = MIN_8bits(*len, guid.header.dwLength);
    status = USBD_REQ_HANDLED;

  } else {
    status = USBD_REQ_NOTSUPP;
  }

  return status;
}

static void winusb_set_config(usbd_device *usbd_dev, uint16_t wValue) {
  (void)wValue;
  usbd_register_control_callback(usbd_dev, USB_REQ_TYPE_VENDOR,
                                 USB_REQ_TYPE_TYPE,
                                 winusb_control_vendor_request);
}

void winusb_setup(usbd_device *usbd_dev, uint8_t interface) {
  winusb_wcid.functions[0].bInterfaceNumber = interface;

  usbd_register_set_config_callback(usbd_dev, winusb_set_config);

  /* Windows probes the compatible ID before setting the configuration,
     so also register the callback now */

  usbd_register_control_callback(usbd_dev, USB_REQ_TYPE_VENDOR,
                                 USB_REQ_TYPE_TYPE,
                                 winusb_control_vendor_request);

  usbd_register_control_callback(usbd_dev, USB_REQ_TYPE_DEVICE,
                                 USB_REQ_TYPE_RECIPIENT,
                                 winusb_descriptor_request);
}
