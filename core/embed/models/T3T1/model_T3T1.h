#ifndef MODELS_MODEL_T3T1_H_
#define MODELS_MODEL_T3T1_H_

#include "bootloaders/bootloader_hashes.h"

#include "sizedefs.h"

#define MODEL_NAME "Safe 5"
#define MODEL_FULL_NAME "Trezor Safe 5"
#define MODEL_INTERNAL_NAME "T3T1"
#define MODEL_INTERNAL_NAME_TOKEN T3T1
#define MODEL_INTERNAL_NAME_QSTR MP_QSTR_T3T1
#define MODEL_USB_MANUFACTURER "Trezor Company"
#define MODEL_USB_PRODUCT MODEL_FULL_NAME

#define MODEL_BOARDLOADER_KEYS \
  (const uint8_t *)"\x76\xaf\x42\x6e\x61\x40\x6b\xad\x7c\x07\x7b\x40\x9c\x66\xfd\xe3\x9f\xb8\x17\x91\x93\x13\xae\x1e\x4c\x02\x53\x5c\x80\xbe\xed\x96", \
  (const uint8_t *)"\x61\x97\x51\xdc\x8d\x2d\x09\xd7\xe5\xdf\xb9\x9e\x41\xf6\x06\xde\xbd\xf4\x19\xf8\x5a\x81\x43\xe8\xe5\x39\x9e\xa6\x7a\x39\x88\xc7", \
  (const uint8_t *)"\xab\xf9\x4b\x66\x15\xa7\xdd\xe2\xa8\x71\xf7\xd6\x2c\x38\xef\xc7\xd9\xd8\xf6\x01\x0d\x88\x46\xbe\xe6\x36\xe4\xf3\xe6\x58\xa3\x8c",

#define MODEL_BOOTLOADER_KEYS \
  (const uint8_t *)"\x33\x8b\x94\x9b\x7e\x3b\x26\x47\x0d\x4f\xe3\x69\x6f\xd6\xff\xf2\x87\x57\x26\x5d\x14\xcc\xa4\x8e\xbf\x2d\xb9\x7b\x4f\x5b\xc0\x39", \
  (const uint8_t *)"\x28\x68\x20\x27\x73\x0b\x78\x32\x01\xb0\x5a\x8c\x9d\x11\x68\x54\x47\xc1\x72\x97\xdb\x71\xb8\xa6\x0d\xc6\x93\xa4\x46\x10\x75\x1d", \
  (const uint8_t *)"\x9f\xbf\x31\xb4\xe3\x51\xa4\xcc\x81\xc7\x59\x95\xb2\x25\x7f\x0a\x71\x69\x26\x8d\xa5\xa4\x4e\x94\xb6\xa5\x59\x0d\x43\x4e\x32\xda",

#define IMAGE_CHUNK_SIZE (128 * 1024)
#define IMAGE_HASH_SHA256
#define DISPLAY_JUMP_BEHAVIOR DISPLAY_RETAIN_CONTENT

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
#define BHK_MAXSIZE (2 * 8 * 1024)  // 8 kB
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
#define KERNEL_U_FLASH_SIZE 512

#define ASSETS_START 0x0C1F0000
#define ASSETS_MAXSIZE (8 * 8 * 1024)  // 64 kB
#define ASSETS_SECTOR_START 0xF8
#define ASSETS_SECTOR_END 0xFF

// RAM layout
#define KERNEL_U_RAM_SIZE 512
#define KERNEL_SRAM1_SIZE 16 * 1024
#define KERNEL_SRAM2_SIZE 8 * 1024
#define KERNEL_SRAM3_SIZE 0x38400

#define BOOTARGS_SIZE 0x100
#define CODE_ALIGNMENT 0x200

#endif
