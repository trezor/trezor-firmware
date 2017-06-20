#ifndef __TREZORHAL_FLASH_H__
#define __TREZORHAL_FLASH_H__

int flash_init(void);

void flash_set_option_bytes(void);

#define FLASH_SECTOR_BOARDLOADER_START 0
#define FLASH_SECTOR_BOARDLOADER_END   1

#define FLASH_SECTOR_STORAGE_START     2
#define FLASH_SECTOR_STORAGE_END       3

#define FLASH_SECTOR_BOOTLOADER_START  4
#define FLASH_SECTOR_BOOTLOADER_END    4

#define FLASH_SECTOR_FIRMWARE_START    5
#define FLASH_SECTOR_FIRMWARE_END      11

int flash_erase_sectors(int start, int end, void (*progress)(void));

#endif
