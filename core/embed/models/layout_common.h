#ifndef LAYOUT_COMMON_H
#define LAYOUT_COMMON_H

#include "flash.h"

// OTP blocks allocation
#define FLASH_OTP_BLOCK_BATCH 0
#define FLASH_OTP_BLOCK_BOOTLOADER_VERSION 1
#define FLASH_OTP_BLOCK_VENDOR_HEADER_LOCK 2
#define FLASH_OTP_BLOCK_RANDOMNESS 3
#define FLASH_OTP_BLOCK_DEVICE_VARIANT 4

#define STORAGE_AREAS_COUNT (2)

extern const flash_area_t STORAGE_AREAS[STORAGE_AREAS_COUNT];
extern const flash_area_t BOARDLOADER_AREA;
extern const flash_area_t SECRET_AREA;
extern const flash_area_t BOOTLOADER_AREA;
extern const flash_area_t FIRMWARE_AREA;
extern const flash_area_t WIPE_AREA;
extern const flash_area_t ALL_WIPE_AREA;

#endif
