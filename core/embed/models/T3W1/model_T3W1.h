#ifndef MODELS_MODEL_T3W1_H_
#define MODELS_MODEL_T3W1_H_

// #include "bootloaders/bootloader_hashes.h"

#include <rtl/sizedefs.h>

#define MODEL_NAME "T3W1"
#define MODEL_FULL_NAME "Trezor T3W1"
#define MODEL_INTERNAL_NAME "T3W1"
#define MODEL_INTERNAL_NAME_TOKEN T3W1
#define MODEL_INTERNAL_NAME_QSTR MP_QSTR_T3W1
#define MODEL_USB_MANUFACTURER "Trezor Company"
#define MODEL_USB_PRODUCT MODEL_FULL_NAME

#define MODEL_BOARDLOADER_KEYS \
  (const uint8_t *)"\xe8\x91\x2f\x81\xb3\xe7\x80\xee\x65\x0e\xd3\x85\x6d\xb5\x32\x6e\x0b\x9e\xff\x10\x36\x4b\x33\x91\x93\xe7\xa8\xf1\x0f\x76\x21\xb9", \
  (const uint8_t *)"\xbd\xe7\x0a\x38\xee\xe6\x33\xd2\x6f\x43\x4e\xee\x2f\x53\x6d\xf4\x57\xb8\xde\xb8\xbd\x98\x82\x94\xf4\xa0\xc8\xd9\x05\x49\x03\xd2", \
  (const uint8_t *)"\xa8\x5b\x60\x1d\xfb\xda\x1d\x22\xcc\xb5\xdd\x49\x2d\x26\x03\x4d\x87\xf6\x7f\x2a\x0b\x85\x84\xb7\x77\x44\x39\x46\x1f\xc4\x71\xa9",

#define MODEL_BOOTLOADER_KEYS \
  (const uint8_t *)"\x32\x0e\x11\x1e\x9d\xde\xd5\xfe\x7f\x5d\x41\xfd\x37\x2e\xf0\xe9\x1b\x2d\xfa\x4c\x6c\xdc\x9f\xe5\x22\x1b\xfb\x16\xaa\xf9\x17\x75", \
  (const uint8_t *)"\x2e\x34\x9f\x8d\x06\xb2\x33\x42\x62\xec\xb6\x03\xed\x04\xcb\x5a\x7c\xc0\xb6\x60\xeb\xe3\xcd\x5c\x29\x72\xb5\xcd\x1f\x38\xef\x85", \
  (const uint8_t *)"\xab\x0d\x3f\x91\xa4\xad\xf7\x44\x71\x9d\xba\x66\x17\x83\xec\x54\x9f\x73\xa4\xe4\x54\x57\xcb\x6d\x02\x75\x2a\x40\xfb\x63\xd3\xbf",

#define IMAGE_CHUNK_SIZE SIZE_256K
#define IMAGE_HASH_SHA256

#define DISPLAY_JUMP_BEHAVIOR DISPLAY_RESET_CONTENT

// SHARED WITH MAKEFILE, LINKER SCRIPT etc.
// misc
#define FLASH_START 0x0C004000
#define NORCOW_SECTOR_SIZE (16 * 8 * 1024)  // 128 kB

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
#define BOARDLOADER_MAXSIZE (8 * 8 * 1024)  // 64 kB
#define BOARDLOADER_SECTOR_START 0x2
#define BOARDLOADER_SECTOR_END 0x9

#define BOARDCAPS_START 0x0C013F00
#define BOARDCAPS_MAXSIZE 0x100

#define BOOTLOADER_START 0x0C014000
#define BOOTLOADER_MAXSIZE (24 * 8 * 1024)  // 192 kB
#define BOOTLOADER_SECTOR_START 0x0A
#define BOOTLOADER_SECTOR_END 0x21

#define FIRMWARE_START 0x0C044000
#define FIRMWARE_MAXSIZE (430 * 8 * 1024)  // 3440 kB
#define FIRMWARE_SECTOR_START 0x22
#define FIRMWARE_SECTOR_END 0x1CF
#define KERNEL_START 0x0C044000
#define KERNEL_MAXSIZE (512 * 1024)  // 512 kB
#define KERNEL_U_FLASH_SIZE 512

#define STORAGE_1_START 0x0C3A0000
#define STORAGE_1_MAXSIZE (16 * 8 * 1024)  // 128 kB
#define STORAGE_1_SECTOR_START 0x1D0
#define STORAGE_1_SECTOR_END 0x1DF

#define STORAGE_2_START 0x0C3C0000
#define STORAGE_2_MAXSIZE (16 * 8 * 1024)  // 128 kB
#define STORAGE_2_SECTOR_START 0x1E0
#define STORAGE_2_SECTOR_END 0x1EF

#define ASSETS_START 0x0C3E0000
#define ASSETS_MAXSIZE (16 * 8 * 1024)  // 128 kB
#define ASSETS_SECTOR_START 0x1F0
#define ASSETS_SECTOR_END 0x1FF

// RAM layout
#define BOOTARGS_START 0x30000000
#define BOOTARGS_SIZE 0x200

#define FB1_RAM_START 0x30000200
#define FB1_RAM_SIZE (768 * 1024 - 512)

#define MAIN_RAM_START 0x300C0000
#define MAIN_RAM_SIZE (64 * 1024 - 512)

#define SAES_RAM_START 0x300CFE00
#define SAES_RAM_SIZE 512

#define FB2_RAM_START 0x300D0000
#define FB2_RAM_SIZE (768 * 1024)

#define AUX1_RAM_START 0x30190000
#define AUX1_RAM_SIZE (896 * 1024)

// misc
#define CODE_ALIGNMENT 0x400
#define COREAPP_ALIGNMENT 0x2000

#endif
