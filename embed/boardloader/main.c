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

#include "common.h"
#include "display.h"
#include "image.h"
#include "flash.h"
#include "rng.h"
#include "sdcard.h"

#include "lowlevel.h"
#include "version.h"

const uint8_t BOARDLOADER_KEY_M = 2;
const uint8_t BOARDLOADER_KEY_N = 3;
static const uint8_t * const BOARDLOADER_KEYS[] = {
#if PRODUCTION
    (const uint8_t *)"\x0e\xb9\x85\x6b\xe9\xba\x7e\x97\x2c\x7f\x34\xea\xc1\xed\x9b\x6f\xd0\xef\xd1\x72\xec\x00\xfa\xf0\xc5\x89\x75\x9d\xa4\xdd\xfb\xa0",
    (const uint8_t *)"\xac\x8a\xb4\x0b\x32\xc9\x86\x55\x79\x8f\xd5\xda\x5e\x19\x2b\xe2\x7a\x22\x30\x6e\xa0\x5c\x6d\x27\x7c\xdf\xf4\xa3\xf4\x12\x5c\xd8",
    (const uint8_t *)"\xce\x0f\xcd\x12\x54\x3e\xf5\x93\x6c\xf2\x80\x49\x82\x13\x67\x07\x86\x3d\x17\x29\x5f\xac\xed\x72\xaf\x17\x1d\x6e\x65\x13\xff\x06",
#else
    (const uint8_t *)"\xdb\x99\x5f\xe2\x51\x69\xd1\x41\xca\xb9\xbb\xba\x92\xba\xa0\x1f\x9f\x2e\x1e\xce\x7d\xf4\xcb\x2a\xc0\x51\x90\xf3\x7f\xcc\x1f\x9d",
    (const uint8_t *)"\x21\x52\xf8\xd1\x9b\x79\x1d\x24\x45\x32\x42\xe1\x5f\x2e\xab\x6c\xb7\xcf\xfa\x7b\x6a\x5e\xd3\x00\x97\x96\x0e\x06\x98\x81\xdb\x12",
    (const uint8_t *)"\x22\xfc\x29\x77\x92\xf0\xb6\xff\xc0\xbf\xcf\xdb\x7e\xdb\x0c\x0a\xa1\x4e\x02\x5a\x36\x5e\xc0\xe3\x42\xe8\x6e\x38\x29\xcb\x74\xb6",
#endif
};

static uint32_t check_sdcard(void)
{
    if (sectrue != sdcard_power_on()) {
        return 0;
    }

    uint64_t cap = sdcard_get_capacity_in_bytes();
    if (cap < 1024 * 1024) {
        sdcard_power_off();
        return 0;
    }

    uint32_t buf[IMAGE_HEADER_SIZE / sizeof(uint32_t)];

    memset(buf, 0, sizeof(buf));

    const secbool read_status = sdcard_read_blocks(buf, 0, IMAGE_HEADER_SIZE / SDCARD_BLOCK_SIZE);

    sdcard_power_off();

    image_header hdr;

    if ((sectrue == read_status) && (sectrue == load_image_header((const uint8_t *)buf, BOOTLOADER_IMAGE_MAGIC, BOOTLOADER_IMAGE_MAXSIZE, BOARDLOADER_KEY_M, BOARDLOADER_KEY_N, BOARDLOADER_KEYS, &hdr))) {
        return hdr.codelen;
    } else {
        return 0;
    }
}

static void progress_callback(int pos, int len) {
    display_printf(".");
}

static secbool copy_sdcard(void)
{
    display_backlight(255);

    display_printf("TREZOR Boardloader\n");
    display_printf("==================\n\n");

    display_printf("bootloader found on the SD card\n\n");
    display_printf("applying bootloader in 10 seconds\n\n");
    display_printf("unplug now if you want to abort\n\n");

    uint32_t codelen;

    for (int i = 10; i >= 0; i--) {
        display_printf("%d ", i);
        hal_delay(1000);
        codelen = check_sdcard();
        if (0 == codelen) {
            display_printf("\n\nno SD card, aborting\n");
            return secfalse;
        }
    }

    display_printf("\n\nerasing flash:\n\n");

    // erase all flash (except boardloader)
    static const uint8_t sectors[] = {
        3,
        FLASH_SECTOR_STORAGE_1,
        FLASH_SECTOR_STORAGE_2,
        FLASH_SECTOR_BOOTLOADER,
        FLASH_SECTOR_FIRMWARE_START,
        7,
        8,
        9,
        10,
        FLASH_SECTOR_FIRMWARE_END,
        FLASH_SECTOR_UNUSED_START,
        13,
        14,
        FLASH_SECTOR_UNUSED_END,
        FLASH_SECTOR_FIRMWARE_EXTRA_START,
        18,
        19,
        20,
        21,
        22,
        FLASH_SECTOR_FIRMWARE_EXTRA_END,
    };
    if (sectrue != flash_erase_sectors(sectors, sizeof(sectors), progress_callback)) {
        display_printf(" failed\n");
        return secfalse;
    }
    display_printf(" done\n\n");

    ensure(flash_unlock(), NULL);

    // copy bootloader from SD card to Flash
    display_printf("copying new bootloader from SD card\n\n");

    ensure(sdcard_power_on(), NULL);

    uint32_t buf[SDCARD_BLOCK_SIZE / sizeof(uint32_t)];
    for (int i = 0; i < (IMAGE_HEADER_SIZE + codelen) / SDCARD_BLOCK_SIZE; i++) {
        ensure(sdcard_read_blocks(buf, i, 1), NULL);
        for (int j = 0; j < SDCARD_BLOCK_SIZE / sizeof(uint32_t); j++) {
            ensure(flash_write_word(FLASH_SECTOR_BOOTLOADER, i * SDCARD_BLOCK_SIZE + j * sizeof(uint32_t), buf[j]), NULL);
        }
    }

    sdcard_power_off();
    ensure(flash_lock(), NULL);

    display_printf("\ndone\n\n");
    display_printf("Unplug the device and remove the SD card\n");

    return sectrue;
}

int main(void)
{
    if (sectrue != reset_flags_check()) {
        return 1;
    }

    // need the systick timer running before many HAL operations.
    // want the PVD enabled before flash operations too.
    periph_init();

    if (sectrue != flash_configure_option_bytes()) {
        static const uint8_t sectors[] = {
            FLASH_SECTOR_STORAGE_1,
            FLASH_SECTOR_STORAGE_2,
        };
        // display is not initialized so don't call ensure
        secbool r = flash_erase_sectors(sectors, sizeof(sectors), NULL);
        (void)r;
        return 2;
    }

    clear_otg_hs_memory();

    display_init();
    sdcard_init();

    if (check_sdcard()) {
        return copy_sdcard() == sectrue ? 0 : 3;
    }

    image_header hdr;

    ensure(
        load_image_header((const uint8_t *)BOOTLOADER_START, BOOTLOADER_IMAGE_MAGIC, BOOTLOADER_IMAGE_MAXSIZE, BOARDLOADER_KEY_M, BOARDLOADER_KEY_N, BOARDLOADER_KEYS, &hdr),
        "invalid bootloader header");

    const uint8_t sectors[] = {
        FLASH_SECTOR_BOOTLOADER,
    };
    ensure(
        check_image_contents(&hdr, IMAGE_HEADER_SIZE, sectors, 1),
        "invalid bootloader hash");

    jump_to(BOOTLOADER_START + IMAGE_HEADER_SIZE);

    return 0;
}
