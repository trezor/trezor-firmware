/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
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

static void flash_from_sdcard(uint8_t sector, uint32_t source, uint32_t length)
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
            ensure(flash_write_word(sector, i * SDCARD_BLOCK_SIZE + j * sizeof(uint32_t), buf[j]), NULL);
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

    static const uint8_t sectors[] = {
        FLASH_SECTOR_BOARDLOADER_START,
        1,
        FLASH_SECTOR_BOARDLOADER_END,
        FLASH_SECTOR_BOOTLOADER,
    };
    display_printf("erasing sectors");
    ensure(flash_erase_sectors(sectors, sizeof(sectors), progress_callback), "flash_erase_sectors");
    display_printf("\n");
    display_printf("erased\n");

    ensure(flash_unlock(), NULL);

    ensure(sdcard_power_on(), NULL);

#define BOARDLOADER_CHUNK_SIZE  (16 * 1024)
#define BOARDLOADER_TOTAL_SIZE  (3 * BOARDLOADER_CHUNK_SIZE)
#define BOOTLOADER_TOTAL_SIZE   (128 * 1024)

    flash_from_sdcard(FLASH_SECTOR_BOARDLOADER_START,   0 * BOARDLOADER_CHUNK_SIZE, BOARDLOADER_CHUNK_SIZE);
    flash_from_sdcard(1,                                1 * BOARDLOADER_CHUNK_SIZE, BOARDLOADER_CHUNK_SIZE);
    flash_from_sdcard(FLASH_SECTOR_BOARDLOADER_END,     2 * BOARDLOADER_CHUNK_SIZE, BOARDLOADER_CHUNK_SIZE);
    flash_from_sdcard(FLASH_SECTOR_BOOTLOADER,          BOARDLOADER_TOTAL_SIZE,     BOOTLOADER_TOTAL_SIZE);

    display_printf("done\n");
    sdcard_power_off();
    ensure(flash_lock(), NULL);

    return 0;
}
