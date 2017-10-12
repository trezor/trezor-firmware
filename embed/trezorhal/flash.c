#include STM32_HAL_H

#include <string.h>
#include "flash.h"

int flash_init(void)
{
    return 0;
}

bool flash_unlock(void)
{
    HAL_FLASH_Unlock();
    __HAL_FLASH_CLEAR_FLAG(FLASH_FLAG_EOP | FLASH_FLAG_OPERR | FLASH_FLAG_WRPERR | FLASH_FLAG_PGAERR | FLASH_FLAG_PGPERR | FLASH_FLAG_PGSERR);
    return true;
}

bool flash_lock(void)
{
    HAL_FLASH_Lock();
    return true;
}

bool flash_erase_sectors(int start, int end, void (*progress)(uint16_t val))
{
    if (!flash_unlock()) {
        return false;
    }
    FLASH_EraseInitTypeDef EraseInitStruct;
    EraseInitStruct.TypeErase = FLASH_TYPEERASE_SECTORS;
    EraseInitStruct.VoltageRange = FLASH_VOLTAGE_RANGE_3;
    EraseInitStruct.NbSectors = 1;
    uint32_t SectorError = 0;
    for (int i = start; i <= end; i++) {
        EraseInitStruct.Sector = i;
        if (HAL_FLASHEx_Erase(&EraseInitStruct, &SectorError) != HAL_OK) {
            flash_lock();
            return false;
        }
        if (progress) {
            progress(1000 * (i - start + 1) / (end - start + 1));
        }
    }
    flash_lock();
    return true;
}

bool flash_write_byte(uint32_t address, uint8_t data)
{
    return HAL_OK == HAL_FLASH_Program(FLASH_TYPEPROGRAM_BYTE, address, data);
}

bool flash_write_word(uint32_t address, uint32_t data)
{
    return HAL_OK == HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, address, data);
}

#define FLASH_OTP_LOCK_BASE       0x1FFF7A00U

bool flash_otp_read(uint8_t block, uint8_t offset, uint8_t *data, uint8_t datalen)
{
    if (block >= FLASH_OTP_NUM_BLOCKS || offset + datalen > FLASH_OTP_BLOCK_SIZE) {
        return false;
    }
    for (uint8_t i = 0; i < datalen; i++) {
        data[i] = *(__IO uint8_t *)(FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE + offset + i);
    }
    return true;
}

bool flash_otp_write(uint8_t block, uint8_t offset, const uint8_t *data, uint8_t datalen)
{
    if (block >= FLASH_OTP_NUM_BLOCKS || offset + datalen > FLASH_OTP_BLOCK_SIZE) {
        return false;
    }
    if (!flash_unlock()) {
        return false;
    }
    bool ret = false;
    for (uint8_t i = 0; i < datalen; i++) {
        ret = flash_write_byte(FLASH_OTP_BASE + block * FLASH_OTP_BLOCK_SIZE + offset + i, data[i]);
        if (!ret) {
            break;
        }
    }
    flash_lock();
    return ret;
}

bool flash_otp_lock(uint8_t block)
{
    if (block >= FLASH_OTP_NUM_BLOCKS) {
        return false;
    }
    if (!flash_unlock()) {
        return false;
    }
    HAL_StatusTypeDef ret = HAL_FLASH_Program(FLASH_TYPEPROGRAM_BYTE, FLASH_OTP_LOCK_BASE + block, 0x00);
    flash_lock();
    return ret == HAL_OK;
}

bool flash_otp_is_locked(uint8_t block)
{
    return *(__IO uint8_t *)(FLASH_OTP_LOCK_BASE + block) == 0x00;
}
