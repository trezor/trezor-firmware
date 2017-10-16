#ifndef TREZORHAL_FLASH_H
#define TREZORHAL_FLASH_H

#include <stdint.h>
#include "secbool.h"

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

// note: FLASH_SR_RDERR is STM32F42xxx and STM32F43xxx specific (STM32F427) (reference RM0090 section 3.7.5)
#define FLASH_STATUS_ALL_FLAGS (FLASH_SR_RDERR | FLASH_SR_PGSERR | FLASH_SR_PGPERR | FLASH_SR_PGAERR | FLASH_SR_WRPERR | FLASH_SR_SOP | FLASH_SR_EOP)

extern const uint32_t FLASH_SECTOR_TABLE[FLASH_SECTOR_COUNT + 1];

secbool flash_unlock(void);
secbool flash_lock(void);

secbool flash_erase_sectors(const uint8_t *sectors, int len, void (*progress)(int pos, int len));
secbool flash_write_byte(uint32_t address, uint8_t data);
secbool flash_write_word(uint32_t address, uint32_t data);
secbool flash_write_byte_rel(uint32_t sector, uint32_t offset, uint8_t data);
secbool flash_write_word_rel(uint32_t sector, uint32_t offset, uint32_t data);
secbool flash_read_word_rel(uint32_t sector, uint32_t offset, uint32_t *data);

#define FLASH_OTP_NUM_BLOCKS      16
#define FLASH_OTP_BLOCK_SIZE      32

secbool flash_otp_read(uint8_t block, uint8_t offset, uint8_t *data, uint8_t datalen);
secbool flash_otp_write(uint8_t block, uint8_t offset, const uint8_t *data, uint8_t datalen);
secbool flash_otp_lock(uint8_t block);
secbool flash_otp_is_locked(uint8_t block);

#endif // TREZORHAL_FLASH_H
