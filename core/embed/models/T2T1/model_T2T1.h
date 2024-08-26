#ifndef MODELS_MODEL_T2T1_H_
#define MODELS_MODEL_T2T1_H_

#include "bootloaders/bootloader_hashes.h"

#define MODEL_NAME "T"
#define MODEL_FULL_NAME "Trezor Model T"
#define MODEL_INTERNAL_NAME "T2T1"
#define MODEL_INTERNAL_NAME_TOKEN T2T1
#define MODEL_INTERNAL_NAME_QSTR MP_QSTR_T2T1
#define MODEL_USB_MANUFACTURER "SatoshiLabs"
#define MODEL_USB_PRODUCT "TREZOR"

/*** PRODUCTION KEYS  ***/
#define MODEL_BOARDLOADER_KEYS \
  (const uint8_t *)"\x0e\xb9\x85\x6b\xe9\xba\x7e\x97\x2c\x7f\x34\xea\xc1\xed\x9b\x6f\xd0\xef\xd1\x72\xec\x00\xfa\xf0\xc5\x89\x75\x9d\xa4\xdd\xfb\xa0", \
  (const uint8_t *)"\xac\x8a\xb4\x0b\x32\xc9\x86\x55\x79\x8f\xd5\xda\x5e\x19\x2b\xe2\x7a\x22\x30\x6e\xa0\x5c\x6d\x27\x7c\xdf\xf4\xa3\xf4\x12\x5c\xd8", \
  (const uint8_t *)"\xce\x0f\xcd\x12\x54\x3e\xf5\x93\x6c\xf2\x80\x49\x82\x13\x67\x07\x86\x3d\x17\x29\x5f\xac\xed\x72\xaf\x17\x1d\x6e\x65\x13\xff\x06",

#define MODEL_BOOTLOADER_KEYS \
  (const uint8_t *)"\xc2\xc8\x7a\x49\xc5\xa3\x46\x09\x77\xfb\xb2\xec\x9d\xfe\x60\xf0\x6b\xd6\x94\xdb\x82\x44\xbd\x49\x81\xfe\x3b\x7a\x26\x30\x7f\x3f", \
  (const uint8_t *)"\x80\xd0\x36\xb0\x87\x39\xb8\x46\xf4\xcb\x77\x59\x30\x78\xde\xb2\x5d\xc9\x48\x7a\xed\xcf\x52\xe3\x0b\x4f\xb7\xcd\x70\x24\x17\x8a", \
  (const uint8_t *)"\xb8\x30\x7a\x71\xf5\x52\xc6\x0a\x4c\xbb\x31\x7f\xf4\x8b\x82\xcd\xbf\x6b\x6b\xb5\xf0\x4c\x92\x0f\xec\x7b\xad\xf0\x17\x88\x37\x51",

#define IMAGE_CHUNK_SIZE (128 * 1024)
#define IMAGE_HASH_BLAKE2S
#define BOARD_CAPABILITIES_ADDR 0x0800BF00
#define CODE_ALIGNMENT 0x200

// SHARED WITH MAKEFILE
#define FLASH_START 0x08000000
#define BOARDLOADER_START 0x08000000
#define BOOTLOADER_START 0x08020000
#define FIRMWARE_START 0x08040000
#define FIRMWARE_P2_START 0x08120000
#define STORAGE_1_OFFSET 0x10000
#define STORAGE_2_OFFSET 0x110000
#define NORCOW_SECTOR_SIZE (1 * 64 * 1024)         // 64 kB
#define BOARDLOADER_IMAGE_MAXSIZE (3 * 16 * 1024)  // 48 kB
#define BOOTLOADER_IMAGE_MAXSIZE (1 * 128 * 1024)  // 128 kB
#define FIRMWARE_IMAGE_MAXSIZE (13 * 128 * 1024)   // 1664 kB
#define FIRMWARE_P1_IMAGE_MAXSIZE (6 * 128 * 1024)
#define FIRMWARE_P2_IMAGE_MAXSIZE (7 * 128 * 1024)
#define BOARDLOADER_SECTOR_START 0
#define BOARDLOADER_SECTOR_END 3
#define BOOTLOADER_SECTOR_START 5
#define BOOTLOADER_SECTOR_END 5
#define FIRMWARE_SECTOR_START 6
#define FIRMWARE_SECTOR_END 11
#define FIRMWARE_P2_SECTOR_START 17
#define FIRMWARE_P2_SECTOR_END 23
#define STORAGE_1_SECTOR_START 4
#define STORAGE_1_SECTOR_END 4
#define STORAGE_2_SECTOR_START 16
#define STORAGE_2_SECTOR_END 16

#endif
