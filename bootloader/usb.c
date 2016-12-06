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

#define ENDPOINT_ADDRESS_IN         (0x81)
#define ENDPOINT_ADDRESS_OUT        (0x01)

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

static const uint8_t hid_report_descriptor[] = {
	0x06, 0x00, 0xff,  // USAGE_PAGE (Vendor Defined)
	0x09, 0x01,        // USAGE (1)
	0xa1, 0x01,        // COLLECTION (Application)
	0x09, 0x20,        // USAGE (Input Report Data)
	0x15, 0x00,        // LOGICAL_MINIMUM (0)
	0x26, 0xff, 0x00,  // LOGICAL_MAXIMUM (255)
	0x75, 0x08,        // REPORT_SIZE (8)
	0x95, 0x40,        // REPORT_COUNT (64)
	0x81, 0x02,        // INPUT (Data,Var,Abs)
	0x09, 0x21,        // USAGE (Output Report Data)
	0x15, 0x00,        // LOGICAL_MINIMUM (0)
	0x26, 0xff, 0x00,  // LOGICAL_MAXIMUM (255)
	0x75, 0x08,        // REPORT_SIZE (8)
	0x95, 0x40,        // REPORT_COUNT (64)
	0x91, 0x02,        // OUTPUT (Data,Var,Abs)
	0xc0               // END_COLLECTION
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
	.bEndpointAddress = ENDPOINT_ADDRESS_IN,
	.bmAttributes = USB_ENDPOINT_ATTR_INTERRUPT,
	.wMaxPacketSize = 64,
	.bInterval = 1,
}, {
	.bLength = USB_DT_ENDPOINT_SIZE,
	.bDescriptorType = USB_DT_ENDPOINT,
	.bEndpointAddress = ENDPOINT_ADDRESS_OUT,
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

static int hid_control_request(usbd_device *dev, struct usb_setup_data *req, uint8_t **buf, uint16_t *len, usbd_control_complete_callback *complete)
{
	(void)complete;
	(void)dev;

	if ((req->bmRequestType != 0x81) ||
	    (req->bRequest != USB_REQ_GET_DESCRIPTOR) ||
	    (req->wValue != 0x2200))
		return 0;

	/* Handle the HID report descriptor. */
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
	while ( usbd_ep_write_packet(dev, ENDPOINT_ADDRESS_IN,
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
	while ( usbd_ep_write_packet(dev, ENDPOINT_ADDRESS_IN,
		"?##"				// header
		"\x00\x03"			// msg_id
		"\x00\x00\x00\x02"	// payload_len
		"\x08\x63"			// data
		"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
		, 64) != 64) {}
}

extern int firmware_present;

static void send_msg_features(usbd_device *dev)
{
	// send response: Features message (id 17), payload len 30
		// vendor = "bitcointrezor.com"
		// major_version = VERSION_MAJOR
		// minor_version = VERSION_MINOR
		// patch_version = VERSION_PATCH
		// bootloader_mode = True
		// firmware_present = True/False
	if (firmware_present) {
		while ( usbd_ep_write_packet(dev, ENDPOINT_ADDRESS_IN,
			"?##"				// header
			"\x00\x11"			// msg_id
			"\x00\x00\x00\x1e"	// payload_len
			"\x0a\x11" "bitcointrezor.com\x10" VERSION_MAJOR_CHAR "\x18" VERSION_MINOR_CHAR " " VERSION_PATCH_CHAR "(\x01"		// data
			"\x90\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
			, 64) != 64) {}
	} else {
		while ( usbd_ep_write_packet(dev, ENDPOINT_ADDRESS_IN,
			"?##"				// header
			"\x00\x11"			// msg_id
			"\x00\x00\x00\x1e"	// payload_len
			"\x0a\x11" "bitcointrezor.com\x10" VERSION_MAJOR_CHAR "\x18" VERSION_MINOR_CHAR " " VERSION_PATCH_CHAR "(\x01"		// data
			"\x90\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
			, 64) != 64) {}
	}
}

static void send_msg_buttonrequest_firmwarecheck(usbd_device *dev)
{
	// send response: ButtonRequest message (id 26), payload len 2
		// code = ButtonRequest_FirmwareCheck (9)
	while ( usbd_ep_write_packet(dev, ENDPOINT_ADDRESS_IN,
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

	if ( usbd_ep_read_packet(dev, ENDPOINT_ADDRESS_OUT, buf, 64) != 64) return;

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
			layoutDialog(&bmp_icon_question, "Abort", "Continue", NULL, "Install new", "firmware?", NULL, "Never do this without", "your recovery card!", NULL);
			do {
				delay(100000);
				buttonUpdate();
			} while (!button.YesUp && !button.NoUp);
			if (button.YesUp) {
				// backup metadata
				memcpy(meta_backup, (void *)FLASH_META_START, FLASH_META_LEN);
				flash_unlock();
				// erase metadata area
				for (i = FLASH_META_SECTOR_FIRST; i <= FLASH_META_SECTOR_LAST; i++) {
					layoutProgress("ERASING ... Please wait", 1000*(i - FLASH_META_SECTOR_FIRST) / (FLASH_CODE_SECTOR_LAST - FLASH_META_SECTOR_FIRST));
					flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
				}
				// erase code area
				for (i = FLASH_CODE_SECTOR_FIRST; i <= FLASH_CODE_SECTOR_LAST; i++) {
					layoutProgress("ERASING ... Please wait", 1000*(i - FLASH_META_SECTOR_FIRST) / (FLASH_CODE_SECTOR_LAST - FLASH_META_SECTOR_FIRST));
					flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
				}
				layoutProgress("INSTALLING ... Please wait", 0);
				flash_lock();
				send_msg_success(dev);
				flash_state = STATE_FLASHSTART;
				return;
			}
			send_msg_failure(dev);
			flash_state = STATE_END;
			layoutDialog(&bmp_icon_warning, NULL, NULL, NULL, "Firmware installation", "aborted.", NULL, "You may now", "unplug your TREZOR.", NULL);
			return;
		}
		return;
	}

	if (flash_state == STATE_FLASHSTART) {
		if (msg_id == 0x0007) {		// FirmwareUpload message (id 7)
			if (buf[9] != 0x0a) { // invalid contents
				send_msg_failure(dev);
				flash_state = STATE_END;
				layoutDialog(&bmp_icon_error, NULL, NULL, NULL, "Error installing ", "firmware.", NULL, "Unplug your TREZOR", "and try again.", NULL);
				return;
			}
			// read payload length
			p = buf + 10;
			flash_len = readprotobufint(&p);
			if (flash_len > FLASH_TOTAL_SIZE + FLASH_META_DESC_LEN - (FLASH_APP_START - FLASH_ORIGIN)) { // firmware is too big
				send_msg_failure(dev);
				flash_state = STATE_END;
				layoutDialog(&bmp_icon_error, NULL, NULL, NULL, "Firmware is too big.", NULL, "Get official firmware", "from mytrezor.com", NULL, NULL);
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
			layoutDialog(&bmp_icon_error, NULL, NULL, NULL, "Error installing ", "firmware.", NULL, "Unplug your TREZOR", "and try again.", NULL);
			return;
		}
		p = buf + 1;
		if (flash_anim % 32 == 4) {
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
				}
				flash_pos += 4;
				wi = 0;
			}
			p++;
		}
		flash_lock();
		// flashing done
		if (flash_pos == flash_len) {
			sha256_Update(&ctx, (unsigned char*) FLASH_APP_START,
						  flash_len - FLASH_META_DESC_LEN);
			flash_state = STATE_CHECK;
			send_msg_buttonrequest_firmwarecheck(dev);
		}
		return;
	}

	if (flash_state == STATE_CHECK) {
		if (msg_id != 0x001B) {	// ButtonAck message (id 27)
			return;
		}
		uint8_t hash[32];
		sha256_Final(&ctx, hash);
		layoutFirmwareHash(hash);
		do {
			delay(100000);
			buttonUpdate();
		} while (!button.YesUp && !button.NoUp);

		bool hash_check_ok = button.YesUp;

		layoutProgress("INSTALLING ... Please wait", 1000);
		uint8_t flags = *((uint8_t *)FLASH_META_FLAGS);
		// check if to restore old storage area but only if signatures are ok
		if ((flags & 0x01) && signatures_ok(NULL)) {
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
			layoutDialog(&bmp_icon_ok, NULL, NULL, NULL, "New firmware", "successfully installed.", NULL, "You may now", "unplug your TREZOR.", NULL);
			send_msg_success(dev);
		} else {
			layoutDialog(&bmp_icon_warning, NULL, NULL, NULL, "Firmware installation", "aborted.", NULL, "You need to repeat", "the procedure with", "the correct firmware.");
			send_msg_failure(dev);
		}
		return;
	}

}

static void hid_set_config(usbd_device *dev, uint16_t wValue)
{
	(void)wValue;

	usbd_ep_setup(dev, ENDPOINT_ADDRESS_IN, USB_ENDPOINT_ATTR_INTERRUPT, 64, 0);
	usbd_ep_setup(dev, ENDPOINT_ADDRESS_OUT, USB_ENDPOINT_ATTR_INTERRUPT, 64, hid_rx_callback);

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

void checkButtons(void)
{
	static bool btn_left = false, btn_right = false, btn_final = false;
	if (btn_final) {
		return;
	}
	uint16_t state = gpio_port_read(BTN_PORT);
	if ((state & (BTN_PIN_YES | BTN_PIN_NO)) != (BTN_PIN_YES | BTN_PIN_NO)) {
		if ((state & BTN_PIN_NO) != BTN_PIN_NO) {
			btn_left = true;
		}
		if ((state & BTN_PIN_YES) != BTN_PIN_YES) {
			btn_right = true;
		}
	}
	if (btn_left) {
		oledBox(0, 0, 3, 3, true);
	}
	if (btn_right) {
		oledBox(OLED_WIDTH - 4, 0, OLED_WIDTH - 1, 3, true);
	}
	if (btn_left || btn_right) {
		oledRefresh();
	}
	if (btn_left && btn_right) {
		btn_final = true;
	}
}

void usbLoop(void)
{
	for (;;) {
		usbd_poll(usbd_dev);
		if (!firmware_present && (flash_state == STATE_READY || flash_state == STATE_OPEN)) {
			checkButtons();
		}
	}
}
