/*
 * This file is part of the TREZOR project.
 *
 * Copyright (C) 2014 Pavol Rusnak <stick@satoshilabs.com>
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

#include <libopencm3/usb/usbd.h>
#include <libopencm3/usb/hid.h>
#include <libopencm3/stm32/flash.h>

#include <string.h>

#include "buttons.h"
#include "bootloader.h"
#include "oled.h"
#include "rng.h"
#include "usb.h"
#include "serialno.h"
#include "layout.h"
#include "util.h"
#include "signatures.h"
#include "sha2.h"

static const struct usb_device_descriptor dev_descr = {
	.bLength = USB_DT_DEVICE_SIZE,
	.bDescriptorType = USB_DT_DEVICE,
	.bcdUSB = 0x0200,
	.bDeviceClass = 0,
	.bDeviceSubClass = 0,
	.bDeviceProtocol = 0,
	.bMaxPacketSize0 = 64,
	.idVendor = 0x534c,
	.idProduct = 0x0001,
	.bcdDevice = 0x0100,
	.iManufacturer = 1,
	.iProduct = 2,
	.iSerialNumber = 3,
	.bNumConfigurations = 1,
};

/* got via usbhid-dump from CP2110 */
static const uint8_t hid_report_descriptor[] = {
	0x06, 0x00, 0xFF, 0x09, 0x01, 0xA1, 0x01, 0x09, 0x01, 0x75, 0x08, 0x95, 0x40, 0x26, 0xFF, 0x00,
	0x15, 0x00, 0x85, 0x01, 0x95, 0x01, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x02,
	0x95, 0x02, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x03, 0x95, 0x03, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x04, 0x95, 0x04, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x05, 0x95, 0x05, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x06,
	0x95, 0x06, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x07, 0x95, 0x07, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x08, 0x95, 0x08, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x09, 0x95, 0x09, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x0A,
	0x95, 0x0A, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x0B, 0x95, 0x0B, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x0C, 0x95, 0x0C, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x0D, 0x95, 0x0D, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x0E,
	0x95, 0x0E, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x0F, 0x95, 0x0F, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x10, 0x95, 0x10, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x11, 0x95, 0x11, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x12,
	0x95, 0x12, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x13, 0x95, 0x13, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x14, 0x95, 0x14, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x15, 0x95, 0x15, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x16,
	0x95, 0x16, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x17, 0x95, 0x17, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x18, 0x95, 0x18, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x19, 0x95, 0x19, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x1A,
	0x95, 0x1A, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x1B, 0x95, 0x1B, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x1C, 0x95, 0x1C, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x1D, 0x95, 0x1D, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x1E,
	0x95, 0x1E, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x1F, 0x95, 0x1F, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x20, 0x95, 0x20, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x21, 0x95, 0x21, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x22,
	0x95, 0x22, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x23, 0x95, 0x23, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x24, 0x95, 0x24, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x25, 0x95, 0x25, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x26,
	0x95, 0x26, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x27, 0x95, 0x27, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x28, 0x95, 0x28, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x29, 0x95, 0x29, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x2A,
	0x95, 0x2A, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x2B, 0x95, 0x2B, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x2C, 0x95, 0x2C, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x2D, 0x95, 0x2D, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x2E,
	0x95, 0x2E, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x2F, 0x95, 0x2F, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x30, 0x95, 0x30, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x31, 0x95, 0x31, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x32,
	0x95, 0x32, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x33, 0x95, 0x33, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x34, 0x95, 0x34, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x35, 0x95, 0x35, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x36,
	0x95, 0x36, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x37, 0x95, 0x37, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x38, 0x95, 0x38, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x39, 0x95, 0x39, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x3A,
	0x95, 0x3A, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x3B, 0x95, 0x3B, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x3C, 0x95, 0x3C, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01,
	0x91, 0x02, 0x85, 0x3D, 0x95, 0x3D, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x3E,
	0x95, 0x3E, 0x09, 0x01, 0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x3F, 0x95, 0x3F, 0x09, 0x01,
	0x81, 0x02, 0x09, 0x01, 0x91, 0x02, 0x85, 0x40, 0x95, 0x01, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x41,
	0x95, 0x01, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x42, 0x95, 0x06, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x43,
	0x95, 0x01, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x44, 0x95, 0x02, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x45,
	0x95, 0x04, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x46, 0x95, 0x02, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x47,
	0x95, 0x02, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x50, 0x95, 0x08, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x51,
	0x95, 0x01, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x52, 0x95, 0x01, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x60,
	0x95, 0x0A, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x61, 0x95, 0x3F, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x62,
	0x95, 0x3F, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x63, 0x95, 0x3F, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x64,
	0x95, 0x3F, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x65, 0x95, 0x3E, 0x09, 0x01, 0xB1, 0x02, 0x85, 0x66,
	0x95, 0x13, 0x09, 0x01, 0xB1, 0x02, 0xC0,
};

static const struct {
	struct usb_hid_descriptor hid_descriptor;
	struct {
		uint8_t bReportDescriptorType;
		uint16_t wDescriptorLength;
	} __attribute__((packed)) hid_report;
} __attribute__((packed)) hid_function = {
	.hid_descriptor = {
		.bLength = sizeof(hid_function),
		.bDescriptorType = USB_DT_HID,
		.bcdHID = 0x0111,
		.bCountryCode = 0,
		.bNumDescriptors = 1,
	},
	.hid_report = {
		.bReportDescriptorType = USB_DT_REPORT,
		.wDescriptorLength = sizeof(hid_report_descriptor),
	}
};

static const struct usb_endpoint_descriptor hid_endpoints[2] = {{
	.bLength = USB_DT_ENDPOINT_SIZE,
	.bDescriptorType = USB_DT_ENDPOINT,
	.bEndpointAddress = 0x81,
	.bmAttributes = USB_ENDPOINT_ATTR_INTERRUPT,
	.wMaxPacketSize = 64,
	.bInterval = 1,
}, {
	.bLength = USB_DT_ENDPOINT_SIZE,
	.bDescriptorType = USB_DT_ENDPOINT,
	.bEndpointAddress = 0x02,
	.bmAttributes = USB_ENDPOINT_ATTR_INTERRUPT,
	.wMaxPacketSize = 64,
	.bInterval = 1,
}};

static const struct usb_interface_descriptor hid_iface[] = {{
	.bLength = USB_DT_INTERFACE_SIZE,
	.bDescriptorType = USB_DT_INTERFACE,
	.bInterfaceNumber = 0,
	.bAlternateSetting = 0,
	.bNumEndpoints = 2,
	.bInterfaceClass = USB_CLASS_HID,
	.bInterfaceSubClass = 0,
	.bInterfaceProtocol = 0,
	.iInterface = 0,
	.endpoint = hid_endpoints,
	.extra = &hid_function,
	.extralen = sizeof(hid_function),
}};

static const struct usb_interface ifaces[] = {{
	.num_altsetting = 1,
	.altsetting = hid_iface,
}};

static const struct usb_config_descriptor config = {
	.bLength = USB_DT_CONFIGURATION_SIZE,
	.bDescriptorType = USB_DT_CONFIGURATION,
	.wTotalLength = 0,
	.bNumInterfaces = 1,
	.bConfigurationValue = 1,
	.iConfiguration = 0,
	.bmAttributes = 0x80,
	.bMaxPower = 0x32,
	.interface = ifaces,
};

static const char *usb_strings[] = {
	"SatoshiLabs",
	"TREZOR",
	"", // empty serial
};

static int hid_control_request(usbd_device *dev, struct usb_setup_data *req, uint8_t **buf, uint16_t *len,
			void (**complete)(usbd_device *, struct usb_setup_data *))
{
	(void)complete;
	(void)dev;

	if ((req->bmRequestType != 0x81) ||
	    (req->bRequest != USB_REQ_GET_DESCRIPTOR) ||
	    (req->wValue != 0x2200)) return 0;

	*buf = (uint8_t *)hid_report_descriptor;
	*len = sizeof(hid_report_descriptor);

	return 1;
}

enum {
	STATE_READY,
	STATE_OPEN,
	STATE_FLASHSTART,
	STATE_FLASHING,
	STATE_CHECK,
	STATE_END,
};

static uint32_t flash_pos = 0, flash_len = 0;
static char flash_state = STATE_READY;
static uint8_t flash_anim = 0;
static uint16_t msg_id = 0xFFFF;
static uint32_t msg_size = 0;

static uint8_t meta_backup[FLASH_META_LEN];

static void send_msg_success(usbd_device *dev)
{
	// send response: Success message (id 2), payload len 0
	while ( usbd_ep_write_packet(dev, 0x81,
		"?##"				// header
		"\x00\x02"			// msg_id
		"\x00\x00\x00\x00"	// payload_len
		"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
		, 64) != 64) {}
}

static void send_msg_failure(usbd_device *dev)
{
	// send response: Failure message (id 3), payload len 2
		// code = 99 (Failure_FirmwareError)
	while ( usbd_ep_write_packet(dev, 0x81,
		"?##"				// header
		"\x00\x03"			// msg_id
		"\x00\x00\x00\x02"	// payload_len
		"\x08\x63"			// data
		"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
		, 64) != 64) {}
}

static void send_msg_features(usbd_device *dev)
{
	// send response: Features message (id 17), payload len 27
		// vendor = "bitcointrezor.com"
		// major_version = VERSION_MAJOR
		// minor_version = VERSION_MINOR
		// patch_version = VERSION_PATCH
		// bootloader_mode = True
	while ( usbd_ep_write_packet(dev, 0x81,
		"?##"				// header
		"\x00\x11"			// msg_id
		"\x00\x00\x00\x1b"	// payload_len
		"\x0a\x11" "bitcointrezor.com\x10" VERSION_MAJOR_CHAR "\x18" VERSION_MINOR_CHAR " " VERSION_PATCH_CHAR "(\x01"		// data
		"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
		, 64) != 64) {}
}

static void send_msg_buttonrequest_firmwarecheck(usbd_device *dev)
{
	// send response: ButtonRequest message (id 26), payload len 2
		// code = ButtonRequest_FirmwareCheck (9)
	while ( usbd_ep_write_packet(dev, 0x81,
		"?##"				// header
		"\x00\x1a"			// msg_id
		"\x00\x00\x00\x02"	// payload_len
		"\x08\x09"			// data
		"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
		, 64) != 64) {}
}

static void hid_rx_callback(usbd_device *dev, uint8_t ep)
{
	(void)ep;
	static uint8_t buf[64] __attribute__((aligned(4)));
	uint8_t *p;
	static uint8_t towrite[4] __attribute__((aligned(4)));
	static int wi;
	int i;
	uint32_t *w;
	static SHA256_CTX ctx;

	if ( usbd_ep_read_packet(dev, 0x02, buf, 64) != 64) return;

	if (flash_state == STATE_END) {
		return;
	}

	if (flash_state == STATE_READY || flash_state == STATE_OPEN || flash_state == STATE_FLASHSTART || flash_state == STATE_CHECK) {
		if (buf[0] != '?' || buf[1] != '#' || buf[2] != '#') {	// invalid start - discard
			return;
		}
		// struct.unpack(">HL") => msg, size
		msg_id = (buf[3] << 8) + buf[4];
		msg_size = (buf[5] << 24)+ (buf[6] << 16) + (buf[7] << 8) + buf[8];
	}

	if (flash_state == STATE_READY || flash_state == STATE_OPEN) {
		if (msg_id == 0x0000) {		// Initialize message (id 0)
			send_msg_features(dev);
			flash_state = STATE_OPEN;
			return;
		}
		if (msg_id == 0x0001) {		// Ping message (id 1)
			send_msg_success(dev);
			return;
		}
	}

	if (flash_state == STATE_OPEN) {
		if (msg_id == 0x0006) {		// FirmwareErase message (id 6)
			layoutDialog(DIALOG_ICON_QUESTION, "Abort", "Continue", NULL, "Install new", "firmware?", NULL, "Never do this without", "your recovery card!", NULL);
			do {
				delay(100000);
				buttonUpdate();
			} while (!button.YesUp && !button.NoUp);
			if (button.YesUp) {
				layoutProgress("INSTALLING ... Please wait", 0);
				// backup metadata
				memcpy(meta_backup, (void *)FLASH_META_START, FLASH_META_LEN);
				flash_unlock();
				// erase metadata area
				for (i = FLASH_META_SECTOR_FIRST; i <= FLASH_META_SECTOR_LAST; i++) {
					flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
				}
				// erase code area
				for (i = FLASH_CODE_SECTOR_FIRST; i <= FLASH_CODE_SECTOR_LAST; i++) {
					flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
				}
				flash_lock();
				send_msg_success(dev);
				flash_state = STATE_FLASHSTART;
				return;
			}
			send_msg_failure(dev);
			flash_state = STATE_END;
			layoutDialog(DIALOG_ICON_WARNING, NULL, NULL, NULL, "Firmware installation", "aborted.", NULL, "You may now", "unplug your TREZOR.", NULL);
			return;
		}
		return;
	}

	if (flash_state == STATE_FLASHSTART) {
		if (msg_id == 0x0007) {		// FirmwareUpload message (id 7)
			if (buf[9] != 0x0a) { // invalid contents
				send_msg_failure(dev);
				flash_state = STATE_END;
				layoutDialog(DIALOG_ICON_ERROR, NULL, NULL, NULL, "Error installing ", "firmware.", NULL, "Unplug your TREZOR", "and try again.", NULL);
				return;
			}
			// read payload length
			p = buf + 10;
			flash_len = readprotobufint(&p);
			if (flash_len > FLASH_TOTAL_SIZE + FLASH_META_DESC_LEN - (FLASH_APP_START - FLASH_ORIGIN)) { // firmware is too big
				send_msg_failure(dev);
				flash_state = STATE_END;
				layoutDialog(DIALOG_ICON_ERROR, NULL, NULL, NULL, "Firmware is too big.", NULL, "Get official firmware", "from mytrezor.com", NULL, NULL);
				return;
			}
			sha256_Init(&ctx);
			flash_state = STATE_FLASHING;
			flash_pos = 0;
			wi = 0;
			flash_unlock();
			while (p < buf + 64) {
				towrite[wi] = *p;
				wi++;
				if (wi == 4) {
					w = (uint32_t *)towrite;
					flash_program_word(FLASH_META_START + flash_pos, *w);
					flash_pos += 4;
					wi = 0;
				}
				p++;
			}
			flash_lock();
			return;
		}
		return;
	}

	if (flash_state == STATE_FLASHING) {
		if (buf[0] != '?') {	// invalid contents
			send_msg_failure(dev);
			flash_state = STATE_END;
			layoutDialog(DIALOG_ICON_ERROR, NULL, NULL, NULL, "Error installing ", "firmware.", NULL, "Unplug your TREZOR", "and try again.", NULL);
			return;
		}
		p = buf + 1;
		if (flash_anim % 8 == 4) {
			layoutProgress("INSTALLING ... Please wait", 1000 * flash_pos / flash_len);
		}
		flash_anim++;
		flash_unlock();
		while (p < buf + 64 && flash_pos < flash_len) {
			towrite[wi] = *p;
			wi++;
			if (wi == 4) {
				w = (uint32_t *)towrite;
				if (flash_pos < FLASH_META_DESC_LEN) {
					flash_program_word(FLASH_META_START + flash_pos, *w);			// the first 256 bytes of firmware is metadata descriptor
				} else {
					flash_program_word(FLASH_APP_START + (flash_pos - FLASH_META_DESC_LEN), *w);	// the rest is code
					sha256_Update(&ctx, towrite, 4);
				}
				flash_pos += 4;
				wi = 0;
			}
			p++;
		}
		flash_lock();
		// flashing done
		if (flash_pos == flash_len) {
			flash_state = STATE_CHECK;
			send_msg_buttonrequest_firmwarecheck(dev);
		}
		return;
	}

	if (flash_state == STATE_CHECK) {
		if (msg_id != 0x001B) {	// ButtonAck message (id 27)
			return;
		}
		char digest[64];
		sha256_End(&ctx, digest);
		char str[4][17];
		strlcpy(str[0], digest, 17);
		strlcpy(str[1], digest + 16, 17);
		strlcpy(str[2], digest + 32, 17);
		strlcpy(str[3], digest + 48, 17);
		layoutDialog(DIALOG_ICON_QUESTION, "Abort", "Continue", "Compare fingerprints", str[0], str[1], str[2], str[3], NULL, NULL);

		do {
			delay(100000);
			buttonUpdate();
		} while (!button.YesUp && !button.NoUp);

		bool hash_check_ok = button.YesUp;

		layoutProgress("INSTALLING ... Please wait", 1000);
		uint8_t flags = *((uint8_t *)FLASH_META_FLAGS);
		// check if to restore old storage area but only if signatures are ok
		if ((flags & 0x01) && signatures_ok()) {
			// copy new stuff
			memcpy(meta_backup, (void *)FLASH_META_START, FLASH_META_DESC_LEN);
			// replace "TRZR" in header with 0000 when hash not confirmed
			if (!hash_check_ok) {
				meta_backup[0] = 0;
				meta_backup[1] = 0;
				meta_backup[2] = 0;
				meta_backup[3] = 0;
			}
			flash_unlock();
			// erase storage
			for (i = FLASH_META_SECTOR_FIRST; i <= FLASH_META_SECTOR_LAST; i++) {
				flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
			}
			// copy it back
			for (i = 0; i < FLASH_META_LEN / 4; i++) {
				w = (uint32_t *)(meta_backup + i * 4);
				flash_program_word(FLASH_META_START + i * 4, *w);
			}
			flash_lock();
		} else {
			// replace "TRZR" in header with 0000 when hash not confirmed
			if (!hash_check_ok) {
				// no need to erase, because we are just erasing bits
				flash_unlock();
				flash_program_word(FLASH_META_START, 0x00000000);
				flash_lock();
			}
		}
		flash_state = STATE_END;
		if (hash_check_ok) {
			layoutDialog(DIALOG_ICON_OK, NULL, NULL, NULL, "New firmware", "successfully installed.", NULL, "You may now", "unplug your TREZOR.", NULL);
			send_msg_success(dev);
		} else {
			layoutDialog(DIALOG_ICON_WARNING, NULL, NULL, NULL, "Firmware installation", "aborted.", NULL, "You need to repeat", "the procedure with", "the correct firmware.");
			send_msg_failure(dev);
		}
		return;
	}

}

static void hid_set_config(usbd_device *dev, uint16_t wValue)
{
	(void)wValue;

	usbd_ep_setup(dev, 0x81, USB_ENDPOINT_ATTR_INTERRUPT, 64, 0);
	usbd_ep_setup(dev, 0x02, USB_ENDPOINT_ATTR_INTERRUPT, 64, hid_rx_callback);

	usbd_register_control_callback(
		dev,
		USB_REQ_TYPE_STANDARD | USB_REQ_TYPE_INTERFACE,
		USB_REQ_TYPE_TYPE | USB_REQ_TYPE_RECIPIENT,
		hid_control_request
	);
}

static usbd_device *usbd_dev;
static uint8_t usbd_control_buffer[128];

void usbInit(void)
{
	usbd_dev = usbd_init(&otgfs_usb_driver, &dev_descr, &config, usb_strings, 3, usbd_control_buffer, sizeof(usbd_control_buffer));
	usbd_register_set_config_callback(usbd_dev, hid_set_config);
}

void usbLoop(void)
{
	for (;;) {
		usbd_poll(usbd_dev);
	}
}
