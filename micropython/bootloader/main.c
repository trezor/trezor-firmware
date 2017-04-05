#include STM32_HAL_H

#include <string.h>

#include "common.h"
#include "display.h"
#include "image.h"
#include "sdcard.h"

#define BOOTLOADER_FGCOLOR 0xFFFF
#define BOOTLOADER_BGCOLOR 0x0000

#define BOOTLOADER_PRINT(X)   do { display_print(X, -1);      display_print_out(BOOTLOADER_FGCOLOR, BOOTLOADER_BGCOLOR); } while(0)
#define BOOTLOADER_PRINTLN(X) do { display_print(X "\n", -1); display_print_out(BOOTLOADER_FGCOLOR, BOOTLOADER_BGCOLOR); } while(0)

#define IMAGE_MAGIC   0x4C5A5254 // TRZL
#define IMAGE_MAXSIZE (1 * 64 * 1024 + 7 * 128 * 1024)

void pendsv_isr_handler(void) {
    __fatal_error("pendsv");
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

    uint32_t buf[SDCARD_BLOCK_SIZE / sizeof(uint32_t)];

    sdcard_read_blocks(buf, 0, 1);

    sdcard_power_off();

    if (image_parse_header((const uint8_t *)buf, IMAGE_MAGIC, IMAGE_MAXSIZE, NULL)) {
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

    // erase flash (except bootloader)
    HAL_FLASH_Unlock();
    FLASH_EraseInitTypeDef EraseInitStruct;
    __HAL_FLASH_CLEAR_FLAG(FLASH_FLAG_EOP | FLASH_FLAG_OPERR | FLASH_FLAG_WRPERR |
                           FLASH_FLAG_PGAERR | FLASH_FLAG_PGPERR | FLASH_FLAG_PGSERR);
    EraseInitStruct.TypeErase = FLASH_TYPEERASE_SECTORS;
    EraseInitStruct.VoltageRange = FLASH_VOLTAGE_RANGE_3;
    EraseInitStruct.NbSectors = 1;
    uint32_t SectorError = 0;
    for (int i = 2; i < 12; i++) {
        EraseInitStruct.Sector = i;
        if (HAL_FLASHEx_Erase(&EraseInitStruct, &SectorError) != HAL_OK) {
            HAL_FLASH_Lock();
            BOOTLOADER_PRINTLN(" failed");
            return false;
        }
        BOOTLOADER_PRINT(".");
    }
    BOOTLOADER_PRINTLN(" done");

    BOOTLOADER_PRINTLN("copying new loader from SD card");

    sdcard_power_on();

    // copy loader from SD card to Flash
    uint32_t buf[SDCARD_BLOCK_SIZE / sizeof(uint32_t)];
    sdcard_read_blocks((uint8_t *)buf, 0, 1);

    image_header hdr;
    if (!image_parse_header((const uint8_t *)buf, IMAGE_MAGIC, IMAGE_MAXSIZE, &hdr)) {
        BOOTLOADER_PRINTLN("invalid header");
        sdcard_power_off();
        HAL_FLASH_Lock();
        return false;
    }

    for (int i = 0; i < (HEADER_SIZE + hdr.codelen) / SDCARD_BLOCK_SIZE; i++) {
        sdcard_read_blocks((uint8_t *)buf, i, 1);
        for (int j = 0; j < SDCARD_BLOCK_SIZE / sizeof(uint32_t); j++) {
            if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, LOADER_START + i * SDCARD_BLOCK_SIZE + j * sizeof(uint32_t), buf[j]) != HAL_OK) {
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

void check_and_jump(void)
{
    BOOTLOADER_PRINTLN("checking loader");

    image_header hdr;

    if (image_parse_header((const uint8_t *)LOADER_START, IMAGE_MAGIC, IMAGE_MAXSIZE, &hdr)) {
        BOOTLOADER_PRINTLN("valid loader header");
    } else {
        BOOTLOADER_PRINTLN("invalid loader header");
        return;
    }

    if (image_check_signature((const uint8_t *)LOADER_START, &hdr, NULL)) {
        BOOTLOADER_PRINTLN("valid loader signature");

        // TODO: remove debug wait
        BOOTLOADER_PRINTLN("waiting 1 second");
        HAL_Delay(1000);
        // end
        BOOTLOADER_PRINTLN("JUMP!");
        jump_to(LOADER_START + HEADER_SIZE);

    } else {
        BOOTLOADER_PRINTLN("invalid loader signature");
    }
}

int main(void)
{
    SCB->VTOR = BOOTLOADER_START;
    periph_init();

    sdcard_init();

    display_init();
    display_clear();
    display_backlight(255);

    BOOTLOADER_PRINTLN("TREZOR Bootloader");
    BOOTLOADER_PRINTLN("=================");
    BOOTLOADER_PRINTLN("starting bootloader");

    if (check_sdcard()) {
        if (!copy_sdcard()) {
            __fatal_error("halt");
        }
    }

    check_and_jump();

    __fatal_error("halt");

    return 0;
}
