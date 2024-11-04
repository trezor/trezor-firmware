#ifndef MODELS_MODEL_T2B1_H_
#define MODELS_MODEL_T2B1_H_

#include "bootloaders/bootloader_hashes.h"

#define MODEL_NAME "Safe 3"
#define MODEL_FULL_NAME "Trezor Safe 3"
#define MODEL_INTERNAL_NAME "T2B1"
#define MODEL_INTERNAL_NAME_TOKEN T2B1
#define MODEL_INTERNAL_NAME_QSTR MP_QSTR_T2B1
#define MODEL_USB_MANUFACTURER "SatoshiLabs"
#define MODEL_USB_PRODUCT "TREZOR"

/*** PRODUCTION KEYS  ***/
#define MODEL_BOARDLOADER_KEYS \
  (const uint8_t *)"\x54\x9a\x45\x55\x70\x08\xd5\x51\x8a\x9a\x15\x1d\xc6\xa3\x56\x8c\xf7\x38\x30\xa7\xfe\x41\x9f\x26\x26\xd9\xf3\x0d\x02\x4b\x2b\xec", \
  (const uint8_t *)"\xc1\x6c\x70\x27\xf8\xa3\x96\x26\x07\xbf\x24\xcd\xec\x2e\x3c\xd2\x34\x4e\x1f\x60\x71\xe8\x26\x0b\x3d\xda\x52\xb1\xa5\x10\x7c\xb7", \
  (const uint8_t *)"\x87\x18\x0f\x93\x31\x78\xb2\x83\x2b\xee\x2d\x70\x46\xc7\xf4\xb9\x83\x00\xca\x7d\x7f\xb2\xe4\x56\x71\x69\xc8\x73\x0a\x1c\x40\x20",

#define MODEL_BOOTLOADER_KEYS \
  (const uint8_t *)"\xbf\x4e\x6f\x00\x4f\xcb\x32\xce\xc6\x83\xf2\x2c\x88\xc1\xa8\x6c\x15\x18\xc6\xde\x8a\xc9\x70\x02\xd8\x4a\x63\xbe\xa3\xe3\x75\xdd", \
  (const uint8_t *)"\xd2\xde\xf6\x91\xc1\xe9\xd8\x09\xd8\x19\x0c\xf7\xaf\x93\x5c\x10\x68\x8f\x68\x98\x34\x79\xb4\xee\x9a\xba\xc1\x91\x04\x87\x8e\xc1", \
  (const uint8_t *)"\x07\xc8\x51\x34\x94\x6b\xf8\x9f\xa1\x9b\xdc\x2c\x5e\x5f\xf9\xce\x01\x29\x65\x08\xee\x08\x63\xd0\xff\x6d\x63\x33\x1d\x1a\x25\x16",

#define IMAGE_CHUNK_SIZE (128 * 1024)
#define IMAGE_HASH_BLAKE2S

#define DISPLAY_JUMP_BEHAVIOR DISPLAY_RETAIN_CONTENT
#define DISPLAY_RESX 128
#define DISPLAY_RESY 64

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

#define SECRET_START 0x08100000
#define SECRET_MAXSIZE (1 * 16 * 1024)  // 16 kB
#define SECRET_SECTOR_START 12
#define SECRET_SECTOR_END 12

#define ASSETS_START 0x08104000
#define ASSETS_MAXSIZE (2 * 16 * 1024)  // 32 kB
#define ASSETS_SECTOR_START 13
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

// RAM layout
#define KERNEL_STACK_SIZE (8 * 1024)
#define KERNEL_CCMRAM_SIZE (16 * 1024)
#define KERNEL_FRAMEBUFFER_SIZE (8 * 1024)
#define KERNEL_SRAM_SIZE (1 * 1024)

#define BOOTARGS_SIZE 0x100
#define CODE_ALIGNMENT 0x200
#define COREAPP_ALIGNMENT 0x200

#endif
