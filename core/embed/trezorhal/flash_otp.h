#ifndef TREZORHAL_FLASH_OTP_H
#define TREZORHAL_FLASH_OTP_H

#include <common.h>

#ifdef KERNEL_MODE

#define FLASH_OTP_NUM_BLOCKS 16
#define FLASH_OTP_BLOCK_SIZE 32

void flash_otp_init(void);

secbool __wur flash_otp_read(uint8_t block, uint8_t offset, uint8_t *data,
                             uint8_t datalen);
secbool __wur flash_otp_write(uint8_t block, uint8_t offset,
                              const uint8_t *data, uint8_t datalen);
secbool __wur flash_otp_lock(uint8_t block);
secbool __wur flash_otp_is_locked(uint8_t block);

#endif  // KERNEL_MODE

#endif  // TREZORHAL_FLASH_OTP_H
