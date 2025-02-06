#ifndef MODELS_MODEL_T3B1_H_
#define MODELS_MODEL_T3B1_H_

#include "bootloaders/bootloader_hashes.h"

#include <rtl/sizedefs.h>

#define MODEL_NAME "Safe 3"
#define MODEL_FULL_NAME "Trezor Safe 3"
#define MODEL_INTERNAL_NAME "T3B1"
#define MODEL_INTERNAL_NAME_TOKEN T3B1
#define MODEL_INTERNAL_NAME_QSTR MP_QSTR_T3B1
#define MODEL_USB_MANUFACTURER "Trezor Company"
#define MODEL_USB_PRODUCT MODEL_FULL_NAME
#define MODEL_HOMESCREEN_MAXSIZE 16384

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

#define DISPLAY_JUMP_BEHAVIOR DISPLAY_RETAIN_CONTENT
#define RSOD_INFINITE_LOOP 1

// SHARED WITH MAKEFILE, LINKER SCRIPT etc.
// misc
#define FLASH_START 0x0C004000
#define NORCOW_SECTOR_SIZE (8 * 8 * 1024)  // 64 kB

// FLASH layout
#define SECRET_START 0x0C000000
#define SECRET_MAXSIZE (2 * 8 * 1024)  // 8 kB
#define SECRET_SECTOR_START 0x0
#define SECRET_SECTOR_END 0x1

// overlaps with secret
#define BHK_START 0x0C002000
#define BHK_MAXSIZE (1 * 8 * 1024)  // 8 kB
#define BHK_SECTOR_START 0x1
#define BHK_SECTOR_END 0x1

#define BOARDLOADER_START 0x0C004000
#define BOARDLOADER_MAXSIZE (6 * 8 * 1024)  // 48 kB
#define BOARDLOADER_SECTOR_START 0x2
#define BOARDLOADER_SECTOR_END 0x7

#define BOARDCAPS_START 0x0C00FF00
#define BOARDCAPS_MAXSIZE 0x100

#define BOOTLOADER_START 0x0C010000
#define BOOTLOADER_MAXSIZE (16 * 8 * 1024)  // 128 kB
#define BOOTLOADER_SECTOR_START 0x8
#define BOOTLOADER_SECTOR_END 0x17

#define STORAGE_1_START 0x0C030000
#define STORAGE_1_MAXSIZE (8 * 8 * 1024)  // 64 kB
#define STORAGE_1_SECTOR_START 0x18
#define STORAGE_1_SECTOR_END 0x1F

#define STORAGE_2_START 0x0C040000
#define STORAGE_2_MAXSIZE (8 * 8 * 1024)  // 64 kB
#define STORAGE_2_SECTOR_START 0x20
#define STORAGE_2_SECTOR_END 0x27

#define FIRMWARE_START 0x0C050000
#define FIRMWARE_MAXSIZE (208 * 8 * 1024)  // 1664 kB
#define FIRMWARE_SECTOR_START 0x28
#define FIRMWARE_SECTOR_END 0xF7
#define KERNEL_START 0x0C050000
#define KERNEL_MAXSIZE (512 * 1024)  // 512 kB

#define ASSETS_START 0x0C1F0000
#define ASSETS_MAXSIZE (8 * 8 * 1024)  // 64 kB
#define ASSETS_SECTOR_START 0xF8
#define ASSETS_SECTOR_END 0xFF

// RAM layout
#define AUX1_RAM_START 0x30000000
#define AUX1_RAM_SIZE (192 * 1024 - 512)

// 256 bytes skipped - trustzone alignment vs fixed bootargs position

#define BOOTARGS_START 0x3002FF00
#define BOOTARGS_SIZE 0x100

#define MAIN_RAM_START 0x30030000
#define MAIN_RAM_SIZE (24 * 1024 - 512)

#define SAES_RAM_START 0x30035E00
#define SAES_RAM_SIZE 512

#define AUX2_RAM_START 0x30036000
#define AUX2_RAM_SIZE (544 * 1024)

#define FB1_RAM_START 0x300BE000
#define FB1_RAM_SIZE (0x2000)

#define FB2_RAM_START 0x300C0000
#define FB2_RAM_SIZE (0)

// misc
#define CODE_ALIGNMENT 0x200
#define COREAPP_ALIGNMENT 0x2000

#endif
