#ifndef MODELS_MODEL_T3B1_H_
#define MODELS_MODEL_T3B1_H_

#include "sizedefs.h"

#define MODEL_NAME "Safe 3"
#define MODEL_FULL_NAME "Trezor Safe 3"
#define MODEL_INTERNAL_NAME "T3B1"
#define MODEL_INTERNAL_NAME_TOKEN T3B1
#define MODEL_INTERNAL_NAME_QSTR MP_QSTR_T3B1
#define MODEL_USB_MANUFACTURER "Trezor Company"
#define MODEL_USB_PRODUCT MODEL_FULL_NAME

#define MODEL_BOARDLOADER_KEYS \
  (const uint8_t *)"\xbb\xc2\x1a\xdb\xc1\xb4\x4d\x6b\xfe\x10\xc5\x22\x3d\xe3\x3c\x28\x42\x9e\x52\x68\x07\x07\xd3\x24\x90\x07\xed\x42\xdc\xc5\xbe\x13", \
  (const uint8_t *)"\x22\xe4\x2a\x30\x1f\x3b\x6f\xf4\xf2\xe6\x92\x6b\xce\x43\x59\xe8\x3f\xc8\x3f\x0f\x4a\x84\xa7\x33\x89\x59\xc1\xfd\x0e\x29\xdc\x13", \
  (const uint8_t *)"\x7f\x47\x8f\x5f\xb7\x8d\x8c\x05\x4b\x72\x0d\x81\x04\xbf\x2f\x64\x87\xe4\x52\x40\x24\x58\x97\x9b\x55\x25\xc2\x90\xdc\x34\x4d\x32",

#define MODEL_BOOTLOADER_KEYS \
  (const uint8_t *)"\x41\xd9\x88\x48\x01\x37\x7c\xff\x04\xb0\xb4\x59\xfc\x9b\x56\xaf\x1b\x51\xf4\x73\x43\xa3\xa6\xe4\xfd\xc1\xea\xca\xbc\xad\x77\x56", \
  (const uint8_t *)"\x23\xec\x4e\xc4\x67\x4d\x68\xac\x54\x31\xe8\xba\x84\xd7\xac\x24\xcb\x5a\x66\x70\x2e\xc5\x65\x01\x4d\x16\x4a\x72\x18\x2a\x66\xc7", \
  (const uint8_t *)"\x8a\x7d\xac\x53\xe1\xbe\x46\x60\x72\x31\x92\x0b\x0c\x71\x05\x6a\x27\xbe\x16\xb6\x7a\x2f\xc0\xd8\x64\x4d\x5f\x87\x08\xa2\x8d\xd1",

#define IMAGE_CHUNK_SIZE (128 * 1024)
#define IMAGE_HASH_SHA256
#define BOARD_CAPABILITIES_ADDR 0x0C00FF00
#define CODE_ALIGNMENT 0x200

// SHARED WITH MAKEFILE
#define FLASH_START 0x0C000000
#define BOARDLOADER_START 0x0C004000
#define BOOTLOADER_START 0x0C010000
#define FIRMWARE_START 0x0C050000
#define STORAGE_1_OFFSET 0x30000
#define STORAGE_2_OFFSET 0x50000
#define NORCOW_SECTOR_SIZE (8 * 8 * 1024)         // 64 kB
#define BOARDLOADER_IMAGE_MAXSIZE (6 * 8 * 1024)  // 48 kB
#define BOOTLOADER_IMAGE_MAXSIZE (16 * 8 * 1024)  // 128 kB
#define FIRMWARE_IMAGE_MAXSIZE (208 * 8 * 1024)   // 1664 kB
#define BOARDLOADER_SECTOR_START 0x2
#define BOARDLOADER_SECTOR_END 0x7
#define BOOTLOADER_SECTOR_START 0x8
#define BOOTLOADER_SECTOR_END 0x17
#define FIRMWARE_SECTOR_START 0x28
#define FIRMWARE_SECTOR_END 0xF7
#define STORAGE_1_SECTOR_START 0x18
#define STORAGE_1_SECTOR_END 0x1F
#define STORAGE_2_SECTOR_START 0x20
#define STORAGE_2_SECTOR_END 0x27

#endif
