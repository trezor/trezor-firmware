#ifndef __TREZORHAL_FLASH_H__
#define __TREZORHAL_FLASH_H__

#include <stdbool.h>
#include <stdint.h>

#define FLASH_SECTOR_BOARDLOADER_START 0
#define FLASH_SECTOR_BOARDLOADER_END   1

#define FLASH_SECTOR_STORAGE_START     2
#define FLASH_SECTOR_STORAGE_END       3

#define FLASH_SECTOR_BOOTLOADER_START  4
#define FLASH_SECTOR_BOOTLOADER_END    4

#define FLASH_SECTOR_FIRMWARE_START    5
#define FLASH_SECTOR_FIRMWARE_END      11

int flash_init(void);

void flash_set_option_bytes(void);

bool flash_unlock(void);
bool flash_lock(void);

bool flash_erase_sectors(int start, int end, void (*progress)(uint16_t val));
bool flash_write_byte(uint32_t address, uint8_t data);
bool flash_write_word(uint32_t address, uint32_t data);

bool flash_otp_read(uint8_t block, uint8_t offset, uint8_t *data, uint8_t datalen);
bool flash_otp_write(uint8_t block, uint8_t offset, const uint8_t *data, uint8_t datalen);
bool flash_otp_lock(uint8_t block);
bool flash_otp_is_locked(uint8_t block);

#endif
