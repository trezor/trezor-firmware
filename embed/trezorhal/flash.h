#ifndef __TREZORHAL_FLASH_H__
#define __TREZORHAL_FLASH_H__

#include <stdbool.h>
#include <stdint.h>

// see docs/memory.md for more information

#define FLASH_SECTOR_BOARDLOADER_START       0
//                                           1
#define FLASH_SECTOR_BOARDLOADER_END         2

#define FLASH_SECTOR_PIN_AREA                3

#define FLASH_SECTOR_STORAGE_1               4

#define FLASH_SECTOR_BOOTLOADER              5

#define FLASH_SECTOR_FIRMWARE_START          6
//                                           7
//                                           8
//                                           9
//                                          10
#define FLASH_SECTOR_FIRMWARE_END           11

#define FLASH_SECTOR_UNUSED_START           12
//                                          13
//                                          14
#define FLASH_SECTOR_UNUSED_END             15

#define FLASH_SECTOR_STORAGE_2              16

#define FLASH_SECTOR_FIRMWARE_EXTRA_START   17
//                                          18
//                                          19
//                                          20
//                                          21
//                                          22
#define FLASH_SECTOR_FIRMWARE_EXTRA_END     23

#define FLASH_SECTOR_COUNT 24

extern const uint32_t FLASH_SECTOR_TABLE[FLASH_SECTOR_COUNT + 1];

void flash_set_option_bytes(void);

bool flash_unlock(void);
bool flash_lock(void);

bool flash_erase_sectors(const uint8_t *sectors, int len, void (*progress)(int pos, int len));
bool flash_write_byte(uint32_t address, uint8_t data);
bool flash_write_word(uint32_t address, uint32_t data);

#define FLASH_OTP_NUM_BLOCKS      16
#define FLASH_OTP_BLOCK_SIZE      32

bool flash_otp_read(uint8_t block, uint8_t offset, uint8_t *data, uint8_t datalen);
bool flash_otp_write(uint8_t block, uint8_t offset, const uint8_t *data, uint8_t datalen);
bool flash_otp_lock(uint8_t block);
bool flash_otp_is_locked(uint8_t block);

#endif
