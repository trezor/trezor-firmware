#include STM32_HAL_H

#include <string.h>

#include "common.h"
#include "display.h"
#include "image.h"
#include "flash.h"
#include "sdcard.h"
#include "version.h"

#define IMAGE_MAGIC   0x425A5254 // TRZB
#define IMAGE_MAXSIZE (1 * 64 * 1024 + 7 * 128 * 1024)

void pendsv_isr_handler(void) {
    __fatal_error("pendsv", __FILE__, __LINE__, __FUNCTION__);
}

bool check_sdcard(void)
{
    display_printf("checking for SD card\n");

    if (!sdcard_is_present()) {
        display_printf("no SD card found\n");
        return false;
    }

    display_printf("SD card found\n");

    sdcard_power_on();

    uint64_t cap = sdcard_get_capacity_in_bytes();
    if (cap < 1024 * 1024) {
        display_printf("SD card too small\n");
        sdcard_power_off();
        return false;
    }

    uint32_t buf[SDCARD_BLOCK_SIZE / sizeof(uint32_t)];

    sdcard_read_blocks(buf, 0, 1);

    sdcard_power_off();

    if (image_parse_header((const uint8_t *)buf, IMAGE_MAGIC, IMAGE_MAXSIZE, NULL)) {
        display_printf("SD card header is valid\n");
        return true;
    } else {
        display_printf("SD card header is invalid\n");
        return false;
    }
}

static void progress_callback(void) {
    display_printf(".");
}

bool copy_sdcard(void)
{
    display_printf("erasing flash ");

    // erase flash (except boardloader)
    if (0 != flash_erase_sectors(FLASH_SECTOR_BOARDLOADER_END + 1, FLASH_SECTOR_FIRMWARE_END, progress_callback)) {
        display_printf(" failed\n");
        return false;
    }
    display_printf(" done\n");

    display_printf("copying new bootloader from SD card\n");

    sdcard_power_on();

    // copy bootloader from SD card to Flash
    uint32_t buf[SDCARD_BLOCK_SIZE / sizeof(uint32_t)];
    sdcard_read_blocks((uint8_t *)buf, 0, 1);

    image_header hdr;
    if (!image_parse_header((const uint8_t *)buf, IMAGE_MAGIC, IMAGE_MAXSIZE, &hdr)) {
        display_printf("invalid header\n");
        sdcard_power_off();
        return false;
    }

    HAL_FLASH_Unlock();
    for (int i = 0; i < (HEADER_SIZE + hdr.codelen) / SDCARD_BLOCK_SIZE; i++) {
        sdcard_read_blocks((uint8_t *)buf, i, 1);
        for (int j = 0; j < SDCARD_BLOCK_SIZE / sizeof(uint32_t); j++) {
            if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, BOOTLOADER_START + i * SDCARD_BLOCK_SIZE + j * sizeof(uint32_t), buf[j]) != HAL_OK) {
                display_printf("copy failed\n");
                sdcard_power_off();
                HAL_FLASH_Lock();
                return false;
            }
        }
    }

    sdcard_power_off();
    HAL_FLASH_Lock();

    display_printf("done\n");

    return true;
}

void check_and_jump(void)
{
    display_printf("checking bootloader\n");

    image_header hdr;

    if (image_parse_header((const uint8_t *)BOOTLOADER_START, IMAGE_MAGIC, IMAGE_MAXSIZE, &hdr)) {
        display_printf("valid bootloader header\n");
    } else {
        display_printf("invalid bootloader header\n");
        return;
    }

    if (image_check_signature((const uint8_t *)BOOTLOADER_START, &hdr, NULL)) {
        display_printf("valid bootloader signature\n");
        display_printf("JUMP!\n");
        jump_to(BOOTLOADER_START + HEADER_SIZE);

    } else {
        display_printf("invalid bootloader signature\n");
    }
}

int main(void)
{
    SCB->VTOR = BOARDLOADER_START;
    periph_init();

    if (0 != display_init()) {
        __fatal_error("display_init", __FILE__, __LINE__, __FUNCTION__);
    }

    if (0 != flash_init()) {
        __fatal_error("flash_init", __FILE__, __LINE__, __FUNCTION__);
    }

    if (0 != sdcard_init()) {
        __fatal_error("sdcard_init", __FILE__, __LINE__, __FUNCTION__);
    }

    display_clear();
    display_backlight(255);

    display_printf("TREZOR Boardloader %d.%d.%d.%d\n", VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH, VERSION_BUILD);
    display_printf("==================\n");
    display_printf("starting boardloader\n");

    if (check_sdcard()) {
        if (!copy_sdcard()) {
            __fatal_error("HALT", __FILE__, __LINE__, __FUNCTION__);
        }
    }

    check_and_jump();

    __fatal_error("HALT", __FILE__, __LINE__, __FUNCTION__);

    return 0;
}
