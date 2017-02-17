#include STM32_HAL_H

#include <string.h>

#include "crypto.h"
#include "display.h"
#include "sdcard.h"

#define STAGE2_SECTOR  4
#define STAGE2_START   0x08010000
#define STAGE2_SIZE    (64 * 1024)

#define BOOTLOADER_PRINT(X) display_print(X, -1)
#define BOOTLOADER_PRINTLN(X) display_print(X "\n", -1)

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

bool check_sdcard(void)
{
    BOOTLOADER_PRINTLN("checking for SD card");

    if (!sdcard_is_present()) {
        BOOTLOADER_PRINTLN("no SD card found");
        return false;
    }

    BOOTLOADER_PRINTLN("SD card found");

    sdcard_power_on();

    uint64_t cap = sdcard_get_capacity_in_bytes();
    if (cap < STAGE2_SIZE) {
        BOOTLOADER_PRINTLN("SD card too small");
        sdcard_power_off();
        return false;
    }

    uint8_t buf[SDCARD_BLOCK_SIZE] __attribute__((aligned(4)));

    sdcard_read_blocks(buf, 0, 1);

    sdcard_power_off();

    if (check_header(buf)) {
        BOOTLOADER_PRINTLN("SD card header is valid");
        return true;
    } else {
        BOOTLOADER_PRINTLN("SD card header is invalid");
        return false;
    }
}

void copy_sdcard(void)
{

    BOOTLOADER_PRINTLN("erasing old stage 2");

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
        return;
    }

    BOOTLOADER_PRINTLN("copying new stage 2 from SD card");

    // copy stage 2 from SD card to Flash
    uint32_t buf[SDCARD_BLOCK_SIZE / sizeof(uint32_t)];

    sdcard_power_on();
    for (int i = 0; i < STAGE2_SIZE / SDCARD_BLOCK_SIZE; i++) {
        sdcard_read_blocks((uint8_t *)buf, i, 1);
        for (int j = 0; j < SDCARD_BLOCK_SIZE / sizeof(uint32_t); j++) {
            if (HAL_FLASH_Program(TYPEPROGRAM_WORD, STAGE2_START + i * SDCARD_BLOCK_SIZE + j * sizeof(uint32_t), buf[j]) != HAL_OK) {
                break;
            }
        }
    }
    sdcard_power_off();

    HAL_FLASH_Lock();

    BOOTLOADER_PRINTLN("done");
}

void halt(void)
{
    for (;;) {
        display_backlight(255);
        HAL_Delay(950);
        display_backlight(0);
        HAL_Delay(50);
    }
}

int main(void)
{

    periph_init();

    BOOTLOADER_PRINTLN("TREZOR Bootloader");
    BOOTLOADER_PRINTLN("=================");
    BOOTLOADER_PRINTLN("starting stage 1");

    if (check_sdcard()) {
        copy_sdcard();
    }

    BOOTLOADER_PRINTLN("checking stage 2");
    if (check_header((const uint8_t *)STAGE2_START)) {
        BOOTLOADER_PRINTLN("valid stage 2 header");
        if (check_signature()) {
            BOOTLOADER_PRINTLN("valid stage 2 signature");
            BOOTLOADER_PRINTLN("JUMP!");
            // TODO: jump to second stage
            halt();
        } else {
            BOOTLOADER_PRINTLN("invalid stage 2 signature");
        }
    } else {
        BOOTLOADER_PRINTLN("invalid stage 2 header");
    }

    BOOTLOADER_PRINTLN("HALT!");
    halt();

    return 0;
}
