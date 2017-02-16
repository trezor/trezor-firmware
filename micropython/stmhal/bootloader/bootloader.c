#include STM32_HAL_H

#include <string.h>

#include "crypto.h"
#include "ui.h"
#include "display.h"
#include "sdcard.h"

#define STAGE2_SECTOR  4
#define STAGE2_START   0x08010000
#define STAGE2_SIZE    (64 * 1024)

void SystemClock_Config(void);

void periph_init(void)
{
    HAL_Init();

    SystemClock_Config();

    __GPIOA_CLK_ENABLE();
    __GPIOB_CLK_ENABLE();
    __GPIOC_CLK_ENABLE();
    __GPIOD_CLK_ENABLE();

    sdcard_init();

    display_init();
    display_clear();
    display_backlight(255);
}

void check_sdcard()
{
    if (!sdcard_is_present()) return;

    sdcard_power_on();

    uint64_t cap = sdcard_get_capacity_in_bytes();
    if (cap < SDCARD_BLOCK_SIZE + STAGE2_SIZE) {
        sdcard_power_off();
        return;
    }

    uint8_t buf[SDCARD_BLOCK_SIZE] __attribute__((aligned(4)));

    sdcard_read_blocks(buf, 0, 1);

    if (!check_header(buf)) {
        sdcard_power_off();
        return;
    }

    // erase STAGE2_SECTOR
    HAL_FLASH_Unlock();
    FLASH_EraseInitTypeDef EraseInitStruct;
    __HAL_FLASH_CLEAR_FLAG(FLASH_FLAG_EOP | FLASH_FLAG_OPERR | FLASH_FLAG_WRPERR |
                           FLASH_FLAG_PGAERR | FLASH_FLAG_PGPERR | FLASH_FLAG_PGSERR);
    EraseInitStruct.TypeErase = TYPEERASE_SECTORS;
    EraseInitStruct.VoltageRange = VOLTAGE_RANGE_3; // voltage range needs to be 2.7V to 3.6V
    EraseInitStruct.Sector = STAGE2_SECTOR;
    EraseInitStruct.NbSectors = 1;
    uint32_t SectorError = 0;
    if (HAL_FLASHEx_Erase(&EraseInitStruct, &SectorError) != HAL_OK) {
        HAL_FLASH_Lock();
        sdcard_power_off();
        return;
    }

    // copy stage 2 from SD card to Flash
    uint32_t src;
    int block = 0;
    int offset = 256;

    for (int i = 0; i < STAGE2_SIZE / 4; i++) {
        memcpy(&src, buf + offset, 4);
        if (HAL_FLASH_Program(TYPEPROGRAM_WORD, STAGE2_START + i * 4, src) != HAL_OK) {
            break;
        }
        offset += 4;
        if (offset == SDCARD_BLOCK_SIZE) {
            offset = 0;
            block++;
            sdcard_read_blocks(buf, block, 1);
        }
    }
    HAL_FLASH_Lock();
    sdcard_power_off();
}


int main(void) {

    periph_init();

    screen_stage1();

    check_sdcard();

    check_signature();

    if (check_header((const uint8_t *)STAGE2_START)) {
        screen_stage2_jump();
        // TODO: jump to second stage
    }

    screen_stage2_invalid();

    for (;;) {
        display_backlight(255);
        HAL_Delay(950);
        display_backlight(0);
        HAL_Delay(50);
    }

    return 0;
}
