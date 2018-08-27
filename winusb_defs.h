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

#ifndef WINUSB_DEFS_H_INCLUDED
#define WINUSB_DEFS_H_INCLUDED

#include <stdint.h>

/* Microsoft OS 1.0 descriptors */

/* Extended Compat ID OS Feature Descriptor Specification */
#define WINUSB_REQ_GET_COMPATIBLE_ID_FEATURE_DESCRIPTOR 0x04
#define WINUSB_REQ_GET_EXTENDED_PROPERTIES_OS_FEATURE_DESCRIPTOR 0x05
#define WINUSB_BCD_VERSION 0x0100

// Apparently using DeviceInterfaceGUID does not always work on Windows 7.
// DeviceInterfaceGUIDs does seem to work.
#define WINUSB_EXTENDED_PROPERTIES_GUID_NAME        u"DeviceInterfaceGUIDs"
#define WINUSB_EXTENDED_PROPERTIES_GUID_NAME_SIZE_C sizeof(WINUSB_EXTENDED_PROPERTIES_GUID_NAME)
#define WINUSB_EXTENDED_PROPERTIES_GUID_NAME_SIZE_U (sizeof(WINUSB_EXTENDED_PROPERTIES_GUID_NAME) / 2)

// extra null is intentional - it's an array of GUIDs with 1 item
#define WINUSB_EXTENDED_PROPERTIES_GUID_DATA        u"{0263b512-88cb-4136-9613-5c8e109d8ef5}\x00"
#define WINUSB_EXTENDED_PROPERTIES_GUID_DATA_SIZE_C sizeof(WINUSB_EXTENDED_PROPERTIES_GUID_DATA)
#define WINUSB_EXTENDED_PROPERTIES_GUID_DATA_SIZE_U (sizeof(WINUSB_EXTENDED_PROPERTIES_GUID_DATA) / 2)
#define WINUSB_EXTENDED_PROPERTIES_MULTISZ_DATA_TYPE  7

#define WINUSB_EXTRA_STRING_INDEX 0xee

/* Table 2. Function Section */
struct winusb_compatible_id_function_section {
	uint8_t  bInterfaceNumber;
	uint8_t  reserved0[1];
	char compatibleId[8];
	char subCompatibleId[8];
	uint8_t  reserved1[6];
} __attribute__((packed));

/* Table 1. Header Section */
struct winusb_compatible_id_descriptor_header {
	uint32_t dwLength;
	uint16_t bcdVersion;
	uint16_t wIndex;
	uint8_t  bNumSections;
	uint8_t  reserved[7];
} __attribute__((packed));

struct winusb_compatible_id_descriptor {
	struct winusb_compatible_id_descriptor_header header;
	struct winusb_compatible_id_function_section functions[];
} __attribute__((packed));

struct winusb_extended_properties_feature_descriptor {
	uint32_t dwLength;
	uint32_t dwPropertyDataType;
	uint16_t wNameLength;
	uint16_t name[WINUSB_EXTENDED_PROPERTIES_GUID_NAME_SIZE_U];
	uint32_t dwPropertyDataLength;
	uint16_t propertyData[WINUSB_EXTENDED_PROPERTIES_GUID_DATA_SIZE_U];
} __attribute__((packed));

struct winusb_extended_properties_descriptor_header {
	uint32_t dwLength;
	uint16_t bcdVersion;
	uint16_t wIndex;
	uint16_t wNumFeatures;
} __attribute__((packed));

struct winusb_extended_properties_descriptor {
	struct winusb_extended_properties_descriptor_header header;
	struct winusb_extended_properties_feature_descriptor features[];
} __attribute__((packed));

#endif
