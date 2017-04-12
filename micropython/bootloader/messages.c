#include "usb.h"
#include "version.h"

#include "messages.h"

void send_msg_success(int iface)
{
	// send response: Success message (id 2), payload len 0
	usb_hid_write_blocking(iface, (const uint8_t *)
		"?##"				// header
		"\x00\x02"			// msg_id
		"\x00\x00\x00\x00"	// payload_len
		"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
		, 64, 1);
}

void send_msg_failure(int iface)
{
	// send response: Failure message (id 3), payload len 2
		// code = 99 (Failure_FirmwareError)
	usb_hid_write_blocking(iface, (const uint8_t *)
		"?##"				// header
		"\x00\x03"			// msg_id
		"\x00\x00\x00\x02"	// payload_len
		"\x08\x63"			// data
		"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
		, 64, 1);
}

void send_msg_features(int iface, bool firmware_present)
{
	// send response: Features message (id 17), payload len 22
		// vendor = "trezor.io"
		// major_version = VERSION_MAJOR
		// minor_version = VERSION_MINOR
		// patch_version = VERSION_PATCH
		// bootloader_mode = True
		// firmware_present = True/False
	if (firmware_present) {
		usb_hid_write_blocking(iface, (const uint8_t *)
			"?##"				// header
			"\x00\x11"			// msg_id
			"\x00\x00\x00\x16"	// payload_len
			"\x0a\x09" "trezor.io\x10" VERSION_MAJOR_CHAR "\x18" VERSION_MINOR_CHAR " " VERSION_PATCH_CHAR "(\x01"		// data
			"\x90\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
			, 64, 1);
	} else {
		usb_hid_write_blocking(iface, (const uint8_t *)
			"?##"				// header
			"\x00\x11"			// msg_id
			"\x00\x00\x00\x16"	// payload_len
			"\x0a\x09" "trezor.io\x10" VERSION_MAJOR_CHAR "\x18" VERSION_MINOR_CHAR " " VERSION_PATCH_CHAR "(\x01"		// data
			"\x90\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
			, 64, 1);
	}
}