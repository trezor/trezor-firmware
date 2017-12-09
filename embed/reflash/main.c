/*
 * Copyright (c) Jan Pochyla, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <string.h>
#include <stdlib.h>
#include <sys/types.h>

#include STM32_HAL_H

#include "common.h"
#include "display.h"
#include "flash.h"
#include "image.h"
#include "rng.h"
#include "sbu.h"
#include "sdcard.h"
#include "secbool.h"
#include "touch.h"

static void progress_callback(int pos, int len)
{
    display_printf(".");
}

static void flash_from_sdcard(uint32_t target, uint32_t source, uint32_t length)
{
    static uint32_t buf[SDCARD_BLOCK_SIZE / sizeof(uint32_t)];

    ensure(
        sectrue * (source % SDCARD_BLOCK_SIZE == 0),
        "source not a multiple of block size");
    ensure(
        sectrue * (length % SDCARD_BLOCK_SIZE == 0),
        "length not a multiple of block size");

    for (uint32_t i = 0; i < length / SDCARD_BLOCK_SIZE; i++) {
        display_printf("read %d\n", (unsigned int)(i + source / SDCARD_BLOCK_SIZE));

        ensure(
            sdcard_read_blocks(buf, i + source / SDCARD_BLOCK_SIZE, 1),
            "sdcard_read_blocks");

        for (uint32_t j = 0; j < SDCARD_BLOCK_SIZE / sizeof(uint32_t); j++) {
            ensure(
                flash_write_word(target + i * SDCARD_BLOCK_SIZE + j * sizeof(uint32_t), buf[j]),
                "flash_write_word");
        }
    }
}

int main(void)
{
    sdcard_init();
    touch_init();

    display_orientation(0);
    display_clear();
    display_backlight(255);

    ensure(
        sdcard_is_present(),
        "sdcard_is_present");

    display_printf("updating boardloader + bootloader\n");

    const uint8_t sectors[] = {
        FLASH_SECTOR_BOARDLOADER_START,
        1,
        FLASH_SECTOR_BOARDLOADER_END,
        FLASH_SECTOR_BOOTLOADER,
    };
    display_printf("erasing sectors");
    ensure(flash_erase_sectors(sectors, sizeof(sectors), progress_callback), "flash_erase_sectors");
    display_printf("\n");
    display_printf("erased\n");

    ensure(
        flash_unlock(),
        "flash_unlock");

    sdcard_power_on();

#define BOARDLOADER_SIZE (3 * 16 * 1024)
#define BOOTLOADER_SIZE  (128 * 1024)

    flash_from_sdcard(BOARDLOADER_START, 0, BOARDLOADER_SIZE);
    flash_from_sdcard(BOOTLOADER_START, BOARDLOADER_SIZE, BOOTLOADER_SIZE);

    display_printf("done\n");
    sdcard_power_off();
    flash_lock();

    return 0;
}
