/*
 * Copyright (c) Jan Pochyla, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <string.h>
#include <stdio.h>

#include "../trezorhal/flash.h"

#ifndef FLASH_FILE
#define FLASH_FILE "/var/tmp/trezor.config"
#endif

#define SECTOR_COUNT 24

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

static uint8_t flash_buffer[0x200000];

static void flash_sync(void)
{
    FILE *f = fopen(FLASH_FILE, "wb");
    if (f) {
        fwrite(flash_buffer, sizeof(flash_buffer), 1, f);
        fclose(f);
    }
}

static void flash_read(void)
{
    FILE *f = fopen(FLASH_FILE, "rb");
    if (f) {
        fread(flash_buffer, sizeof(flash_buffer), 1, f);
        fclose(f);
    }
}

int flash_init(void)
{
    memset(flash_buffer, 0xFF, sizeof(flash_buffer));
    flash_read();
    return 0;
}

void flash_set_option_bytes(void)
{
}

bool flash_unlock(void)
{
    return true;
}

bool flash_lock(void)
{
    return true;
}

const void *flash_get_address(uint8_t sector, uint32_t offset, uint32_t size)
{
    if (sector >= SECTOR_COUNT) {
        return NULL;
    }
    uint32_t sector_size = sector_table[sector + 1] - sector_table[sector];
    if (offset + size > sector_size) {
        return NULL;
    }
    uint32_t sector_offset = sector_table[sector] - sector_table[0];
    return flash_buffer + sector_offset + offset;
}

bool flash_erase_sectors(const uint8_t *sectors, int len, void (*progress)(int pos, int len))
{
    if (progress) {
        progress(0, len);
    }
    for (int i = 0; i < len; i++) {
        uint8_t sector = sectors[i];
        uint32_t offset = sector_table[sector] - sector_table[0];
        uint32_t size = sector_table[sector + 1] - sector_table[sector];
        memset(flash_buffer + offset, 0xFF, size);
        if (progress) {
            progress(i + 1, len);
        }
        flash_sync();
    }
    return true;
}

bool flash_write_byte_rel(uint8_t sector, uint32_t offset, uint8_t data)
{
    uint8_t *flash = (uint8_t *)flash_get_address(sector, offset, sizeof(data));
    if (!flash) {
        return false;
    }
    if ((flash[0] & data) != data) {
        return false;  // we cannot change zeroes to ones
    }
    flash[0] = data;
    flash_sync();
    return true;
}

bool flash_write_word_rel(uint8_t sector, uint32_t offset, uint32_t data)
{
    if (offset % 4) {  // we write only at 4-byte boundary
        return false;
    }
    uint32_t *flash = (uint32_t *)flash_get_address(sector, offset, sizeof(data));
    if (!flash) {
        return false;
    }
    if ((flash[0] & data) != data) {
        return false;  // we cannot change zeroes to ones
    }
    flash[0] = data;
    flash_sync();
    return true;
}

bool flash_read_word_rel(uint8_t sector, uint32_t offset, uint32_t *data)
{
    if (offset % 4) {  // we read only at 4-byte boundary
        return false;
    }
    uint32_t *flash = (uint32_t *)flash_get_address(sector, offset, sizeof(data));
    if (!flash) {
        return false;
    }
    data[0] = flash[0];
    return true;
}

bool flash_otp_read(uint8_t block, uint8_t offset, uint8_t *data, uint8_t datalen)
{
    return false;
}

bool flash_otp_write(uint8_t block, uint8_t offset, const uint8_t *data, uint8_t datalen)
{
    return false;
}

bool flash_otp_lock(uint8_t block)
{
    return false;
}

bool flash_otp_is_locked(uint8_t block)
{
    return false;
}
