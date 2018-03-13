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

#ifndef USB21_STANDARD_H_INCLUDED
#define USB21_STANDARD_H_INCLUDED

#include <libopencm3/usb/usbd.h>

/* USB 3.1 Descriptor Types - Table 9-6 */
#define USB_DT_BOS				15
#define USB_DT_DEVICE_CAPABILITY		16
#define USB_DT_SUPERSPEED_USB_ENDPOINT_COMPANION 48
#define USB_DT_SUPERSPEEDPLUS_ISOCHRONOUS_ENDPOINT_COMPANION 49

struct usb_device_capability_descriptor {
	uint8_t bLength;
	uint8_t bDescriptorType;
	uint8_t bDevCapabilityType;
} __attribute__((packed));

struct usb_bos_descriptor {
	uint8_t bLength;
	uint8_t bDescriptorType;
	uint16_t wTotalLength;
	uint8_t bNumDeviceCaps;
	/* Descriptor ends here.  The following are used internally: */
	const struct usb_device_capability_descriptor **capabilities;
} __attribute__((packed));

#define USB_DT_BOS_SIZE 5

/* USB Device Capability Types - USB 3.1 Table 9-14 */
#define USB_DC_WIRELESS_USB			1
#define USB_DC_USB_2_0_EXTENSION		2
#define USB_DC_SUPERSPEED_USB			3
#define USB_DC_CONTAINER_ID			4
#define USB_DC_PLATFORM				5
#define USB_DC_POWER_DELIVERY_CAPABILITY	6
#define USB_DC_BATTERY_INFO_CAPABILITY		7
#define USB_DC_PD_CONSUMER_PORT_CAPABILITY	8
#define USB_DC_PD_PROVIDER_PORT_CAPABILITY	9
#define USB_DC_SUPERSPEED_PLUS			10
#define USB_DC_PRECISION_TIME_MEASUREMENT	11
#define USB_DC_WIRELESS_USB_EXT			12

extern void usb21_setup(usbd_device* usbd_dev, const struct usb_bos_descriptor* binary_object_store);

#endif
