#include STM32_HAL_H

#include <string.h>

#include "crypto.h"
#include "display.h"
#include "sdcard.h"

#define STAGE2_START   0x08010000

#define BOOTLOADER_PRINT(X) display_print(X, -1)
#define BOOTLOADER_PRINTLN(X) display_print(X "\n", -1)

void SystemClock_Config(void);

void __attribute__((noreturn)) nlr_jump_fail(void *val) {
    for (;;) {}
}

void __attribute__((noreturn)) __fatal_error(const char *msg) {
    for (volatile uint32_t delay = 0; delay < 10000000; delay++) {
    }
    display_print("FATAL ERROR:\n", -1);
    display_print(msg, -1);
    display_print("\n", -1);
    for (;;) {
        __WFI();
    }
}

void mp_hal_stdout_tx_str(const char *str) {
}

void halt(void)
{
    BOOTLOADER_PRINTLN("HALT!");
    for (;;) {
        display_backlight(255);
        HAL_Delay(950);
        display_backlight(0);
        HAL_Delay(50);
    }
}

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
    if (cap < 1024 * 1024) {
        BOOTLOADER_PRINTLN("SD card too small");
        sdcard_power_off();
        return false;
    }

    uint8_t buf[SDCARD_BLOCK_SIZE] __attribute__((aligned(4)));

    sdcard_read_blocks(buf, 0, 1);

    sdcard_power_off();

    if (parse_header(buf, NULL, NULL, NULL)) {
        BOOTLOADER_PRINTLN("SD card header is valid");
        return true;
    } else {
        BOOTLOADER_PRINTLN("SD card header is invalid");
        return false;
    }
}

bool copy_sdcard(void)
{

    BOOTLOADER_PRINT("erasing flash ");

    // erase flash (except stage 1)
    HAL_FLASH_Unlock();
    FLASH_EraseInitTypeDef EraseInitStruct;
    __HAL_FLASH_CLEAR_FLAG(FLASH_FLAG_EOP | FLASH_FLAG_OPERR | FLASH_FLAG_WRPERR |
                           FLASH_FLAG_PGAERR | FLASH_FLAG_PGPERR | FLASH_FLAG_PGSERR);
    EraseInitStruct.TypeErase = TYPEERASE_SECTORS;
    EraseInitStruct.VoltageRange = VOLTAGE_RANGE_3; // voltage range needs to be 2.7V to 3.6V
    EraseInitStruct.NbSectors = 1;
    uint32_t SectorError = 0;
    for (int i = 3; i <= 11; i++) { // TODO: change start to 2
        EraseInitStruct.Sector = i;
        if (HAL_FLASHEx_Erase(&EraseInitStruct, &SectorError) != HAL_OK) {
            HAL_FLASH_Lock();
            BOOTLOADER_PRINTLN(" failed");
            return false;
        }
        BOOTLOADER_PRINT(".");
    }
    BOOTLOADER_PRINTLN(" done");

    BOOTLOADER_PRINTLN("copying new stage 2 from SD card");

    sdcard_power_on();

    // copy stage 2 from SD card to Flash
    uint32_t buf[SDCARD_BLOCK_SIZE / sizeof(uint32_t)];
    sdcard_read_blocks((uint8_t *)buf, 0, 1);

    uint32_t codelen;
    if (!parse_header((uint8_t *)buf, &codelen, NULL, NULL)) {
        BOOTLOADER_PRINTLN("wrong header");
        return false;
    }

    for (int i = 0; i < codelen / SDCARD_BLOCK_SIZE; i++) {
        sdcard_read_blocks((uint8_t *)buf, i, 1);
        for (int j = 0; j < SDCARD_BLOCK_SIZE / sizeof(uint32_t); j++) {
            if (HAL_FLASH_Program(TYPEPROGRAM_WORD, STAGE2_START + i * SDCARD_BLOCK_SIZE + j * sizeof(uint32_t), buf[j]) != HAL_OK) {
                BOOTLOADER_PRINTLN("copy failed");
                sdcard_power_off();
                HAL_FLASH_Lock();
                return false;
            }
        }
    }

    sdcard_power_off();
    HAL_FLASH_Lock();

    BOOTLOADER_PRINTLN("done");

    return true;
}

int main(void)
{

    periph_init();

    BOOTLOADER_PRINTLN("TREZOR Bootloader");
    BOOTLOADER_PRINTLN("=================");
    BOOTLOADER_PRINTLN("starting stage 1");

    if (check_sdcard()) {
        if (!copy_sdcard()) {
            halt();
        }
    }

    BOOTLOADER_PRINTLN("checking stage 2");
    if (parse_header((const uint8_t *)STAGE2_START, NULL, NULL, NULL)) {
        BOOTLOADER_PRINTLN("valid stage 2 header");
        if (check_signature((const uint8_t *)STAGE2_START)) {
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

    halt();

    return 0;
}
