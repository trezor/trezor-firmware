#ifndef MODELS_MODEL_D001_H_
#define MODELS_MODEL_D001_H_

#include "bootloaders/bootloader_hashes.h"

#define MODEL_NAME "D001"
#define MODEL_FULL_NAME "Trezor DIY 1"
#define MODEL_INTERNAL_NAME "D001"
#define MODEL_INTERNAL_NAME_TOKEN D001
#define MODEL_INTERNAL_NAME_QSTR MP_QSTR_D001
#define MODEL_USB_MANUFACTURER "Trezor DIY"
#define MODEL_USB_PRODUCT MODEL_FULL_NAME
#define MODEL_HOMESCREEN_MAXSIZE 16384

/*** Discovery uses DEV keys in any build variant ***/
#define MODEL_BOARDLOADER_KEYS \
  (const uint8_t *)"\xdb\x99\x5f\xe2\x51\x69\xd1\x41\xca\xb9\xbb\xba\x92\xba\xa0\x1f\x9f\x2e\x1e\xce\x7d\xf4\xcb\x2a\xc0\x51\x90\xf3\x7f\xcc\x1f\x9d", \
  (const uint8_t *)"\x21\x52\xf8\xd1\x9b\x79\x1d\x24\x45\x32\x42\xe1\x5f\x2e\xab\x6c\xb7\xcf\xfa\x7b\x6a\x5e\xd3\x00\x97\x96\x0e\x06\x98\x81\xdb\x12", \
  (const uint8_t *)"\x22\xfc\x29\x77\x92\xf0\xb6\xff\xc0\xbf\xcf\xdb\x7e\xdb\x0c\x0a\xa1\x4e\x02\x5a\x36\x5e\xc0\xe3\x42\xe8\x6e\x38\x29\xcb\x74\xb6",

#define MODEL_BOOTLOADER_KEYS \
  (const uint8_t *)"\xd7\x59\x79\x3b\xbc\x13\xa2\x81\x9a\x82\x7c\x76\xad\xb6\xfb\xa8\xa4\x9a\xee\x00\x7f\x49\xf2\xd0\x99\x2d\x99\xb8\x25\xad\x2c\x48", \
  (const uint8_t *)"\x63\x55\x69\x1c\x17\x8a\x8f\xf9\x10\x07\xa7\x47\x8a\xfb\x95\x5e\xf7\x35\x2c\x63\xe7\xb2\x57\x03\x98\x4c\xf7\x8b\x26\xe2\x1a\x56", \
  (const uint8_t *)"\xee\x93\xa4\xf6\x6f\x8d\x16\xb8\x19\xbb\x9b\xeb\x9f\xfc\xcd\xfc\xdc\x14\x12\xe8\x7f\xee\x6a\x32\x4c\x2a\x99\xa1\xe0\xe6\x71\x48",

#define IMAGE_CHUNK_SIZE (128 * 1024)
#define IMAGE_HASH_BLAKE2S

#define DISPLAY_JUMP_BEHAVIOR DISPLAY_RESET_CONTENT

// SHARED WITH MAKEFILE
// common

#define NORCOW_SECTOR_SIZE (1 * 64 * 1024)  // 64 kB
#define FLASH_START 0x08000000

// FLASH layout
#define BOARDLOADER_START 0x08000000
#define BOARDLOADER_MAXSIZE (3 * 16 * 1024)  // 48 kB
#define BOARDLOADER_SECTOR_START 0
#define BOARDLOADER_SECTOR_END 2

#define BOARDCAPS_START 0x0800BF00
#define BOARDCAPS_MAXSIZE 0x100

#define UNUSED_1_START 0x0800C000
#define UNUSED_1_MAXSIZE (1 * 16 * 1024)  // 16 kB
#define UNUSED_1_SECTOR_START 3
#define UNUSED_1_SECTOR_END 3

#define STORAGE_1_START 0x08010000
#define STORAGE_1_MAXSIZE (1 * 64 * 1024)  // 64 kB
#define STORAGE_1_SECTOR_START 4
#define STORAGE_1_SECTOR_END 4

#define BOOTLOADER_START 0x08020000
#define BOOTLOADER_MAXSIZE (1 * 128 * 1024)  // 128 kB
#define BOOTLOADER_SECTOR_START 5
#define BOOTLOADER_SECTOR_END 5

#define FIRMWARE_START 0x08040000
#define FIRMWARE_MAXSIZE (13 * 128 * 1024)  // 1664 kB
#define FIRMWARE_P1_START 0x08040000
#define FIRMWARE_P1_MAXSIZE (6 * 128 * 1024)
#define FIRMWARE_P1_SECTOR_START 6
#define FIRMWARE_P1_SECTOR_END 11
// part of firmware P1
#define KERNEL_START 0x08040000
#define KERNEL_MAXSIZE (4 * 128 * 1024)

#define ASSETS_START 0x08100000
#define ASSETS_MAXSIZE (3 * 16 * 1024)  // 48 kB
#define ASSETS_SECTOR_START 12
#define ASSETS_SECTOR_END 14

#define UNUSED_2_START 0x0810C000
#define UNUSED_2_MAXSIZE (1 * 16 * 1024)  // 16 kB
#define UNUSED_2_SECTOR_START 15
#define UNUSED_2_SECTOR_END 15

#define STORAGE_2_START 0x08110000
#define STORAGE_2_MAXSIZE (1 * 64 * 1024)  // 64 kB
#define STORAGE_2_SECTOR_START 16
#define STORAGE_2_SECTOR_END 16

#define FIRMWARE_P2_START 0x08120000
#define FIRMWARE_P2_MAXSIZE (7 * 128 * 1024)
#define FIRMWARE_P2_SECTOR_START 17
#define FIRMWARE_P2_SECTOR_END 23

// Ram layout - shared boardloader, bootloader, prodtest
#define S_MAIN_STACK_START 0x10000000
#define S_MAIN_STACK_SIZE (16 * 1024)

#define S_FB1_RAM_START 0x10004000
#define S_FB1_RAM_SIZE (0)

#define S_MAIN_RAM_START 0x10004000
#define S_MAIN_RAM_SIZE (48 * 1024 - 0x100)

// RAM layout - kernel
#define K_MAIN_STACK_START 0x10000000
#define K_MAIN_STACK_SIZE (8 * 1024)

#define K_FB1_RAM_START 0x1000C000
#define K_FB1_RAM_SIZE (0)

#define K_MAIN_RAM_START 0x1000C000
#define K_MAIN_RAM_SIZE (16 * 1024 - 0x100)

// RAM layout - common
#define BOOTARGS_START 0x1000FF00
#define BOOTARGS_SIZE 0x100

#define DMABUF_RAM_START 0x20000000
#define DMABUF_RAM_SIZE (1 * 1024)

#define AUX1_RAM_START (0x20000400)
#define AUX1_RAM_SIZE (191 * 1024)

#define AUX2_RAM_START 0x10002000
#define AUX2_RAM_SIZE (40 * 1024)

// misc
#define CODE_ALIGNMENT 0x200
#define COREAPP_ALIGNMENT 0x200

#endif
