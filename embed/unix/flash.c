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
#include <unistd.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>

#include "common.h"
#include "flash.h"
#include "profile.h"

#ifndef FLASH_FILE
#define FLASH_FILE profile_flash_path()
#endif

#define SECTOR_COUNT 24

#define FLASH_SIZE 0x200000

static const uint32_t sector_table[SECTOR_COUNT + 1] = {
    [ 0] = 0x08000000, // - 0x08003FFF |  16 KiB
    [ 1] = 0x08004000, // - 0x08007FFF |  16 KiB
    [ 2] = 0x08008000, // - 0x0800BFFF |  16 KiB
    [ 3] = 0x0800C000, // - 0x0800FFFF |  16 KiB
    [ 4] = 0x08010000, // - 0x0801FFFF |  64 KiB
    [ 5] = 0x08020000, // - 0x0803FFFF | 128 KiB
    [ 6] = 0x08040000, // - 0x0805FFFF | 128 KiB
    [ 7] = 0x08060000, // - 0x0807FFFF | 128 KiB
    [ 8] = 0x08080000, // - 0x0809FFFF | 128 KiB
    [ 9] = 0x080A0000, // - 0x080BFFFF | 128 KiB
    [10] = 0x080C0000, // - 0x080DFFFF | 128 KiB
    [11] = 0x080E0000, // - 0x080FFFFF | 128 KiB
    [12] = 0x08100000, // - 0x08103FFF |  16 KiB
    [13] = 0x08104000, // - 0x08107FFF |  16 KiB
    [14] = 0x08108000, // - 0x0810BFFF |  16 KiB
    [15] = 0x0810C000, // - 0x0810FFFF |  16 KiB
    [16] = 0x08110000, // - 0x0811FFFF |  64 KiB
    [17] = 0x08120000, // - 0x0813FFFF | 128 KiB
    [18] = 0x08140000, // - 0x0815FFFF | 128 KiB
    [19] = 0x08160000, // - 0x0817FFFF | 128 KiB
    [20] = 0x08180000, // - 0x0819FFFF | 128 KiB
    [21] = 0x081A0000, // - 0x081BFFFF | 128 KiB
    [22] = 0x081C0000, // - 0x081DFFFF | 128 KiB
    [23] = 0x081E0000, // - 0x081FFFFF | 128 KiB
    [24] = 0x08200000, // last element - not a valid sector
};

static uint8_t *flash_buffer;

static void flash_exit(void)
{
    int r = munmap(flash_buffer, FLASH_SIZE);
    ensure(sectrue * (r == 0), "munmap failed");
}

void flash_init(void)
{
    int r;

    // check whether the file exists and it has the correct size
    struct stat sb;
    r = stat(FLASH_FILE, &sb);

    // (re)create if non existant or wrong size
    if (r != 0 || sb.st_size != FLASH_SIZE) {
        int fd = open(FLASH_FILE, O_RDWR | O_CREAT | O_TRUNC, (mode_t)0600);
        ensure(sectrue * (fd >= 0), "open failed");
        for (int i = 0; i < FLASH_SIZE / 16; i++) {
            ssize_t s = write(fd, "\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF", 16);
            ensure(sectrue * (s >= 0), "write failed");
        }
        r = close(fd);
        ensure(sectrue * (r == 0), "close failed");
    }

    // mmap file
    int fd = open(FLASH_FILE, O_RDWR);
    ensure(sectrue * (fd >= 0), "open failed");

    void *map = mmap(0, FLASH_SIZE, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    ensure(sectrue * (map != MAP_FAILED), "mmap failed");

    flash_buffer = (uint8_t *)map;

    atexit(flash_exit);
}

secbool flash_unlock(void)
{
    return sectrue;
}

secbool flash_lock(void)
{
    return sectrue;
}

const void *flash_get_address(uint8_t sector, uint32_t offset, uint32_t size)
{
    if (sector >= SECTOR_COUNT) {
        return NULL;
    }
    const uint32_t sector_size = sector_table[sector + 1] - sector_table[sector];
    if (offset + size > sector_size) {
        return NULL;
    }
    const uint32_t sector_offset = sector_table[sector] - sector_table[0];
    return flash_buffer + sector_offset + offset;
}

secbool flash_erase_sectors(const uint8_t *sectors, int len, void (*progress)(int pos, int len))
{
    if (progress) {
        progress(0, len);
    }
    for (int i = 0; i < len; i++) {
        const uint8_t sector = sectors[i];
        const uint32_t offset = sector_table[sector] - sector_table[0];
        const uint32_t size = sector_table[sector + 1] - sector_table[sector];
        memset(flash_buffer + offset, 0xFF, size);
        if (progress) {
            progress(i + 1, len);
        }
    }
    return sectrue;
}

secbool flash_write_byte(uint8_t sector, uint32_t offset, uint8_t data)
{
    uint8_t *flash = (uint8_t *)flash_get_address(sector, offset, sizeof(data));
    if (!flash) {
        return secfalse;
    }
    if ((flash[0] & data) != data) {
        return secfalse;  // we cannot change zeroes to ones
    }
    flash[0] = data;
    return sectrue;
}

secbool flash_write_word(uint8_t sector, uint32_t offset, uint32_t data)
{
    if (offset % 4) {  // we write only at 4-byte boundary
        return secfalse;
    }
    uint32_t *flash = (uint32_t *)flash_get_address(sector, offset, sizeof(data));
    if (!flash) {
        return secfalse;
    }
    if ((flash[0] & data) != data) {
        return secfalse;  // we cannot change zeroes to ones
    }
    flash[0] = data;
    return sectrue;
}

secbool flash_otp_read(uint8_t block, uint8_t offset, uint8_t *data, uint8_t datalen)
{
    return secfalse;
}

secbool flash_otp_write(uint8_t block, uint8_t offset, const uint8_t *data, uint8_t datalen)
{
    return secfalse;
}

secbool flash_otp_lock(uint8_t block)
{
    return secfalse;
}

secbool flash_otp_is_locked(uint8_t block)
{
    return secfalse;
}
