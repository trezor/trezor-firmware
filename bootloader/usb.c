/*
 * This file is part of the TREZOR project, https://trezor.io/
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
#include <libopencm3/stm32/flash.h>

#include <string.h>

#include "buttons.h"
#include "bootloader.h"
#include "oled.h"
#include "rng.h"
#include "usb.h"
#include "layout.h"
#include "util.h"
#include "signatures.h"
#include "sha2.h"
#include "ecdsa.h"
#include "secp256k1.h"
#include "memzero.h"

#include "usb21_standard.h"
#include "webusb.h"
#include "winusb.h"

#define FIRMWARE_MAGIC "TRZR"

#define USB_INTERFACE_INDEX_MAIN 0

#define ENDPOINT_ADDRESS_IN         (0x81)
#define ENDPOINT_ADDRESS_OUT        (0x01)

static bool brand_new_firmware;
static bool old_was_unsigned;

static const struct usb_device_descriptor dev_descr = {
	.bLength = USB_DT_DEVICE_SIZE,
	.bDescriptorType = USB_DT_DEVICE,
	.bcdUSB = 0x0210,
	.bDeviceClass = 0,
	.bDeviceSubClass = 0,
	.bDeviceProtocol = 0,
	.bMaxPacketSize0 = 64,
	.idVendor = 0x1209,
	.idProduct = 0x53c0,
	.bcdDevice = 0x0100,
	.iManufacturer = 1,
	.iProduct = 2,
	.iSerialNumber = 3,
	.bNumConfigurations = 1,
};

static const struct usb_endpoint_descriptor endpoints[2] = {{
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

static const struct usb_interface_descriptor iface[] = {{
	.bLength = USB_DT_INTERFACE_SIZE,
	.bDescriptorType = USB_DT_INTERFACE,
	.bInterfaceNumber = USB_INTERFACE_INDEX_MAIN,
	.bAlternateSetting = 0,
	.bNumEndpoints = 2,
	.bInterfaceClass = USB_CLASS_VENDOR,
	.bInterfaceSubClass = 0,
	.bInterfaceProtocol = 0,
	.iInterface = 0,
	.endpoint = endpoints,
	.extra = NULL,
	.extralen = 0,
}};

static const struct usb_interface ifaces[] = {{
	.num_altsetting = 1,
	.altsetting = iface,
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
	"000000000000000000000000",
};

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
	// response: Success message (id 2), payload len 0
	while ( usbd_ep_write_packet(dev, ENDPOINT_ADDRESS_IN,
		// header
		"?##"
		// msg_id
		"\x00\x02"
		// msg_size
		"\x00\x00\x00\x00"
		// padding
		"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
		, 64) != 64) {}
}

static void send_msg_failure(usbd_device *dev)
{
	// response: Failure message (id 3), payload len 2
	//           - code = 99 (Failure_FirmwareError)
	while ( usbd_ep_write_packet(dev, ENDPOINT_ADDRESS_IN,
		// header
		"?##"
		// msg_id
		"\x00\x03"
		// msg_size
		"\x00\x00\x00\x02"
		// data
		"\x08" "\x63"
		// padding
		"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
		, 64) != 64) {}
}

static void send_msg_features(usbd_device *dev)
{
	// response: Features message (id 17), payload len 30
	//           - vendor = "trezor.io"
	//           - major_version = VERSION_MAJOR
	//           - minor_version = VERSION_MINOR
	//           - patch_version = VERSION_PATCH
	//           - bootloader_mode = True
	//           - firmware_present = True/False
	//           - model = "1"
	if (brand_new_firmware) {
		while ( usbd_ep_write_packet(dev, ENDPOINT_ADDRESS_IN,
			// header
			"?##"
			// msg_id
			"\x00\x11"
			// msg_size
			"\x00\x00\x00\x16"
			// data
			"\x0a" "\x09" "trezor.io"
			"\x10" VERSION_MAJOR_CHAR
			"\x18" VERSION_MINOR_CHAR
			"\x20" VERSION_PATCH_CHAR
			"\x28" "\x01"
			"\x90\x01" "\x00"
			"\xaa" "\x01" "1"
			// padding
			"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
			, 64) != 64) {}
	} else {
		while ( usbd_ep_write_packet(dev, ENDPOINT_ADDRESS_IN,
			// header
			"?##"
			// msg_id
			"\x00\x11"
			// msg_size
			"\x00\x00\x00\x16"
			// data
			"\x0a" "\x09" "trezor.io"
			"\x10" VERSION_MAJOR_CHAR
			"\x18" VERSION_MINOR_CHAR
			"\x20" VERSION_PATCH_CHAR
			"\x28" "\x01"
			"\x90\x01" "\x01"
			"\xaa" "\x01" "1"
			// padding
			"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
			, 64) != 64) {}
	}
}

static void send_msg_buttonrequest_firmwarecheck(usbd_device *dev)
{
	// response: ButtonRequest message (id 26), payload len 2
	//           - code = ButtonRequest_FirmwareCheck (9)
	while ( usbd_ep_write_packet(dev, ENDPOINT_ADDRESS_IN,
		// header
		"?##"
		// msg_id
		"\x00\x1a"
		// msg_size
		"\x00\x00\x00\x02"
		// data
		"\x08" "\x09"
		// padding
		"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
		, 64) != 64) {}
}

static void backup_metadata(uint8_t *backup)
{
	memcpy(backup, FLASH_PTR(FLASH_META_START), FLASH_META_LEN);
}

static void restore_metadata(const uint8_t *backup)
{
	flash_unlock();
	for (int i = 0; i < FLASH_META_LEN / 4; i++) {
		const uint32_t *w = (const uint32_t *)(backup + i * 4);
		flash_program_word(FLASH_META_START + i * 4, *w);
	}
	flash_lock();
}

static void rx_callback(usbd_device *dev, uint8_t ep)
{
	(void)ep;
	static uint8_t buf[64] __attribute__((aligned(4)));
	static uint8_t towrite[4] __attribute__((aligned(4)));
	static int wi;

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
		msg_size = ((uint32_t) buf[5] << 24) + (buf[6] << 16) + (buf[7] << 8) + buf[8];
	}

	if (flash_state == STATE_READY || flash_state == STATE_OPEN) {
		if (msg_id == 0x0000) {		// Initialize message (id 0)
			send_msg_features(dev);
			flash_state = STATE_OPEN;
			return;
		}
		if (msg_id == 0x0037) {		// GetFeatures message (id 55)
			send_msg_features(dev);
			return;
		}
		if (msg_id == 0x0001) {		// Ping message (id 1)
			send_msg_success(dev);
			return;
		}
		if (msg_id == 0x0005) {		// WipeDevice message (id 5)
			layoutDialog(&bmp_icon_question, "Cancel", "Confirm", NULL, "Do you really want to", "wipe the device?", NULL, "All data will be lost.", NULL, NULL);
			do {
				delay(100000);
				buttonUpdate();
			} while (!button.YesUp && !button.NoUp);
			if (button.YesUp) {
				flash_wait_for_last_operation();
				flash_clear_status_flags();
				flash_unlock();
				// erase metadata area
				for (int i = FLASH_META_SECTOR_FIRST; i <= FLASH_META_SECTOR_LAST; i++) {
					layoutProgress("PREPARING ... Please wait", 1000 * (i - FLASH_META_SECTOR_FIRST) / (FLASH_CODE_SECTOR_LAST - FLASH_META_SECTOR_FIRST));
					flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
				}
				// erase code area
				for (int i = FLASH_CODE_SECTOR_FIRST; i <= FLASH_CODE_SECTOR_LAST; i++) {
					layoutProgress("PREPARING ... Please wait", 1000 * (i - FLASH_META_SECTOR_FIRST) / (FLASH_CODE_SECTOR_LAST - FLASH_META_SECTOR_FIRST));
					flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
				}
				flash_wait_for_last_operation();
				flash_lock();
				flash_state = STATE_END;
				layoutDialog(&bmp_icon_ok, NULL, NULL, NULL, "Device", "successfully wiped.", NULL, "You may now", "unplug your TREZOR.", NULL);
				send_msg_success(dev);
			} else {
				flash_state = STATE_END;
				layoutDialog(&bmp_icon_warning, NULL, NULL, NULL, "Device wipe", "aborted.", NULL, "You may now", "unplug your TREZOR.", NULL);
				send_msg_failure(dev);
			}
			return;
		}
	}

	if (flash_state == STATE_OPEN) {
		if (msg_id == 0x0006) {		// FirmwareErase message (id 6)
			if (!brand_new_firmware) {
				layoutDialog(&bmp_icon_question, "Abort", "Continue", NULL, "Install new", "firmware?", NULL, "Never do this without", "your recovery card!", NULL);
				do {
					delay(100000);
					buttonUpdate();
				} while (!button.YesUp && !button.NoUp);
			}
			if (brand_new_firmware || button.YesUp) {
				// check whether current firmware is signed
				if (!brand_new_firmware && SIG_OK == signatures_ok(NULL)) {
					old_was_unsigned = false;
					// backup metadata
					backup_metadata(meta_backup);
				} else {
					old_was_unsigned = true;
				}
				flash_wait_for_last_operation();
				flash_clear_status_flags();
				flash_unlock();
				// erase metadata area
				for (int i = FLASH_META_SECTOR_FIRST; i <= FLASH_META_SECTOR_LAST; i++) {
					layoutProgress("PREPARING ... Please wait", 1000 * (i - FLASH_META_SECTOR_FIRST) / (FLASH_CODE_SECTOR_LAST - FLASH_META_SECTOR_FIRST));
					flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
				}
				// erase code area
				for (int i = FLASH_CODE_SECTOR_FIRST; i <= FLASH_CODE_SECTOR_LAST; i++) {
					layoutProgress("PREPARING ... Please wait", 1000 * (i - FLASH_META_SECTOR_FIRST) / (FLASH_CODE_SECTOR_LAST - FLASH_META_SECTOR_FIRST));
					flash_erase_sector(i, FLASH_CR_PROGRAM_X32);
				}
				layoutProgress("INSTALLING ... Please wait", 0);
				flash_wait_for_last_operation();
				flash_lock();

				// check that metadata was succesfully erased
				// flash status register should show now error and
				// the config block should contain only \xff.
				uint8_t hash[32];
				sha256_Raw(FLASH_PTR(FLASH_META_START), FLASH_META_LEN, hash);
				if ((FLASH_SR & (FLASH_SR_PGAERR | FLASH_SR_PGPERR | FLASH_SR_PGSERR | FLASH_SR_WRPERR)) != 0
					|| memcmp(hash, "\x2d\x86\x4c\x0b\x78\x9a\x43\x21\x4e\xee\x85\x24\xd3\x18\x20\x75\x12\x5e\x5c\xa2\xcd\x52\x7f\x35\x82\xec\x87\xff\xd9\x40\x76\xbc", 32) != 0) {
					send_msg_failure(dev);
					flash_state = STATE_END;
					layoutDialog(&bmp_icon_error, NULL, NULL, NULL, "Error installing ", "firmware.", NULL, "Unplug your TREZOR", "and try again.", NULL);
					return;
				}

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
			uint8_t *p = buf + 10;
			flash_len = readprotobufint(&p);
			if (flash_len > FLASH_TOTAL_SIZE + FLASH_META_DESC_LEN - (FLASH_APP_START - FLASH_ORIGIN)) { // firmware is too big
				send_msg_failure(dev);
				flash_state = STATE_END;
				layoutDialog(&bmp_icon_error, NULL, NULL, NULL, "Firmware is too big.", NULL, "Get official firmware", "from trezor.io/start", NULL, NULL);
				return;
			}
			// check firmware magic
			if (memcmp(p, FIRMWARE_MAGIC, 4) != 0) {
				send_msg_failure(dev);
				flash_state = STATE_END;
				layoutDialog(&bmp_icon_error, NULL, NULL, NULL, "Wrong firmware header.", NULL, "Get official firmware", "from trezor.io/start", NULL, NULL);
				return;
			}
			flash_state = STATE_FLASHING;
			p += 4;         // Don't flash firmware header yet.
			flash_pos = 4;
			wi = 0;
			flash_unlock();
			while (p < buf + 64) {
				towrite[wi] = *p;
				wi++;
				if (wi == 4) {
					const uint32_t *w = (uint32_t *)towrite;
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
		const uint8_t *p = buf + 1;
		if (flash_anim % 32 == 4) {
			layoutProgress("INSTALLING ... Please wait", 1000 * flash_pos / flash_len);
		}
		flash_anim++;
		flash_unlock();
		while (p < buf + 64 && flash_pos < flash_len) {
			towrite[wi] = *p;
			wi++;
			if (wi == 4) {
				const uint32_t *w = (const uint32_t *)towrite;
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
			flash_state = STATE_CHECK;
			if (!brand_new_firmware) {
				send_msg_buttonrequest_firmwarecheck(dev);
				return;
			}
		} else {
			return;
		}
	}

	if (flash_state == STATE_CHECK) {

		if (!brand_new_firmware) {
			if (msg_id != 0x001B) {	// ButtonAck message (id 27)
				return;
			}
			uint8_t hash[32];
			sha256_Raw(FLASH_PTR(FLASH_APP_START), flash_len - FLASH_META_DESC_LEN, hash);
			layoutFirmwareHash(hash);
			do {
				delay(100000);
				buttonUpdate();
			} while (!button.YesUp && !button.NoUp);
		}

		bool hash_check_ok = brand_new_firmware || button.YesUp;

		layoutProgress("INSTALLING ... Please wait", 1000);
		uint8_t flags = *FLASH_PTR(FLASH_META_FLAGS);
		// wipe storage if:
		// 0) there was no firmware
		// 1) old firmware was unsigned
		// 2) firmware restore flag isn't set
		// 3) signatures are not ok
		if (brand_new_firmware || old_was_unsigned || (flags & 0x01) == 0 || SIG_OK != signatures_ok(NULL)) {
			memzero(meta_backup, sizeof(meta_backup));
		}
		// copy new firmware header
		memcpy(meta_backup, (void *)FLASH_META_START, FLASH_META_DESC_LEN);
		// write "TRZR" in header only when hash was confirmed
		if (hash_check_ok) {
			memcpy(meta_backup, FIRMWARE_MAGIC, 4);
		} else {
			memzero(meta_backup, 4);
		}

		// no need to erase, because we are not changing any already flashed byte.
		restore_metadata(meta_backup);
		memzero(meta_backup, sizeof(meta_backup));

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

static void set_config(usbd_device *dev, uint16_t wValue)
{
	(void)wValue;

	usbd_ep_setup(dev, ENDPOINT_ADDRESS_IN,  USB_ENDPOINT_ATTR_INTERRUPT, 64, 0);
	usbd_ep_setup(dev, ENDPOINT_ADDRESS_OUT, USB_ENDPOINT_ATTR_INTERRUPT, 64, rx_callback);
}

static usbd_device *usbd_dev;
static uint8_t usbd_control_buffer[256] __attribute__ ((aligned (2)));

static const struct usb_device_capability_descriptor* capabilities[] = {
	(const struct usb_device_capability_descriptor*)&webusb_platform_capability_descriptor,
};

static const struct usb_bos_descriptor bos_descriptor = {
	.bLength = USB_DT_BOS_SIZE,
	.bDescriptorType = USB_DT_BOS,
	.bNumDeviceCaps = sizeof(capabilities)/sizeof(capabilities[0]),
	.capabilities = capabilities
};

void usbInit(void)
{
	usbd_dev = usbd_init(&otgfs_usb_driver, &dev_descr, &config, usb_strings, sizeof(usb_strings)/sizeof(const char *), usbd_control_buffer, sizeof(usbd_control_buffer));
	usbd_register_set_config_callback(usbd_dev, set_config);
	usb21_setup(usbd_dev, &bos_descriptor);
	static const char* origin_url = "trezor.io/start";
	webusb_setup(usbd_dev, origin_url);
	winusb_setup(usbd_dev, USB_INTERFACE_INDEX_MAIN);
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

void usbLoop(bool firmware_present)
{
	brand_new_firmware = !firmware_present;
	usbInit();
	for (;;) {
		usbd_poll(usbd_dev);
		if (brand_new_firmware && (flash_state == STATE_READY || flash_state == STATE_OPEN)) {
			checkButtons();
		}
	}
}
