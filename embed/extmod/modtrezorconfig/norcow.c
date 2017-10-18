#include <string.h>

#include "norcow.h"
#include "norcow_config.h"

#ifdef NORCOW_UNIX
#ifndef NORCOW_FILE
#error Undefined NORCOW_FILE
#endif
#include <stdio.h>
uint8_t norcow_buffer[NORCOW_SECTOR_COUNT * NORCOW_SECTOR_SIZE];
#endif

#ifdef NORCOW_STM32
#ifndef NORCOW_SECTORS
#error Undefined NORCOW_SECTORS
#endif
#ifndef NORCOW_ADDRESSES
#error Undefined NORCOW_ADDRESSES
#endif
static uint32_t norcow_sectors[NORCOW_SECTOR_COUNT] = NORCOW_SECTORS;
static uint32_t norcow_addresses[NORCOW_SECTOR_COUNT] = NORCOW_ADDRESSES;
#include STM32_HAL_H
#endif

static uint8_t norcow_active_sector = 0;
static uint32_t norcow_active_offset = 0;

/*
 * Synchronizes in-memory storage with file on disk (UNIX only)
 */
#ifdef NORCOW_UNIX
static void norcow_sync(void)
{
    FILE *f = fopen(NORCOW_FILE, "wb");
    if (f) {
        fwrite(norcow_buffer, sizeof(norcow_buffer), 1, f);
        fclose(f);
    }
}
#endif

/*
 * Erases sector
 */
static bool norcow_erase(uint8_t sector)
{
    if (sector >= NORCOW_SECTOR_COUNT) {
        return false;
    }
#ifdef NORCOW_UNIX
    memset(norcow_buffer + sector * NORCOW_SECTOR_SIZE, 0xFF, NORCOW_SECTOR_SIZE);
    norcow_sync();
    return true;
#endif
#ifdef NORCOW_STM32
    HAL_FLASH_Unlock();
    __HAL_FLASH_CLEAR_FLAG(FLASH_FLAG_EOP | FLASH_FLAG_OPERR | FLASH_FLAG_WRPERR | FLASH_FLAG_PGAERR | FLASH_FLAG_PGPERR | FLASH_FLAG_PGSERR);
    FLASH_EraseInitTypeDef EraseInitStruct;
    EraseInitStruct.TypeErase = FLASH_TYPEERASE_SECTORS;
    EraseInitStruct.VoltageRange = FLASH_VOLTAGE_RANGE_3;
    EraseInitStruct.NbSectors = 1;
    EraseInitStruct.Sector = norcow_sectors[sector];
    HAL_StatusTypeDef r;
    uint32_t SectorError = 0;
    r = HAL_FLASHEx_Erase(&EraseInitStruct, &SectorError);
    HAL_FLASH_Lock();
    return r == HAL_OK;
#endif
    return false;
}

/*
 * Returns pointer to sector, starting with offset
 * Fails when there is not enough space for data of given size
 */
static const void *norcow_ptr(uint8_t sector, uint32_t offset, uint32_t size)
{
    if (sector >= NORCOW_SECTOR_COUNT) {
        return NULL;
    }
    if (offset + size > NORCOW_SECTOR_SIZE) {
        return NULL;
    }
#ifdef NORCOW_UNIX
    return (const void *)(norcow_buffer + sector * NORCOW_SECTOR_SIZE + offset);
#endif
#ifdef NORCOW_STM32
    return (const void *)(norcow_addresses[sector] + offset);
#endif
}

/*
 * Writes data to given sector, starting from offset
 */
static bool norcow_write(uint8_t sector, uint32_t offset, uint32_t prefix, const uint8_t *data, uint16_t len)
{
    if (offset % 4) { // we write only at 4-byte boundary
        return false;
    }
    const uint8_t *ptr = (const uint8_t *)norcow_ptr(sector, offset, sizeof(uint32_t) + len);
    if (!ptr) {
        return false;
    }
#ifdef NORCOW_UNIX
    // check whether we are about just change 1s to 0s
    // and bailout if not
    if ((*(uint32_t *)ptr & prefix) != prefix) {
        return false;
    }
    for (size_t i = 0; i < len; i++) {
        if ((ptr[sizeof(uint32_t) + i] & data[i]) != data[i]) {
            return false;
        }
    }
    memcpy((void *)ptr, &prefix, sizeof(uint32_t));
    memcpy((void *)(ptr + sizeof(uint32_t)), data, len);
    norcow_sync();
    return true;
#endif
#ifdef NORCOW_STM32
    HAL_FLASH_Unlock();
    __HAL_FLASH_CLEAR_FLAG(FLASH_FLAG_EOP | FLASH_FLAG_OPERR | FLASH_FLAG_WRPERR | FLASH_FLAG_PGAERR | FLASH_FLAG_PGPERR | FLASH_FLAG_PGSERR);
    uint32_t addr = (uint32_t)ptr;
    HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, addr, prefix);
    addr += 4;
    for (size_t i = 0; i < (len + 3) / sizeof(uint32_t); i++) {
        const uint32_t *d = (const uint32_t *)(data + i * sizeof(uint32_t));
        HAL_FLASH_Program(FLASH_TYPEPROGRAM_WORD, addr, *d);
        addr += 4;
    }
    HAL_FLASH_Lock();
    return true;
#endif
    return false;
}

#define ALIGN4(X) (X) = ((X) + 3) & ~3

/*
 * Reads one item starting from offset
 */
static bool read_item(uint8_t sector, uint32_t offset, uint16_t *key, const void **val, uint16_t *len, uint32_t *pos)
{
    *pos = offset;

    const void *k = norcow_ptr(sector, *pos, 2);
    if (k == NULL) return false;
    *pos += 2;
    memcpy(key, k, sizeof(uint16_t));
    if (*key == 0xFFFF) {
        return false;
    }

    const void *l = norcow_ptr(sector, *pos, 2);
    if (l == NULL) return false;
    *pos += 2;
    memcpy(len, l, sizeof(uint16_t));

    *val = norcow_ptr(sector, *pos, *len);
    if (*val == NULL) return false;
    *pos += *len;
    ALIGN4(*pos);
    return true;
}

/*
 * Writes one item starting from offset
 */
static bool write_item(uint8_t sector, uint32_t offset, uint16_t key, const void *val, uint16_t len, uint32_t *pos)
{
    uint32_t prefix = (len << 16) | key;
    *pos = offset + sizeof(uint32_t) + len;
    ALIGN4(*pos);
    return norcow_write(sector, offset, prefix, val, len);
}

/*
 * Finds item in given sector
 */
static bool find_item(uint8_t sector, uint16_t key, const void **val, uint16_t *len)
{
    *val = 0;
    *len = 0;
    uint32_t offset = 0;
    for (;;) {
        uint16_t k, l;
        const void *v;
        uint32_t pos;
        bool r = read_item(sector, offset, &k, &v, &l, &pos);
        if (!r) break;
        if (key == k) {
            *val = v;
            *len = l;
        }
        offset = pos;
    }
    return (*val);
}

/*
 * Finds first unused offset in given sector
 */
static uint32_t find_free_offset(uint8_t sector)
{
    uint32_t offset = 0;
    for (;;) {
        uint16_t key, len;
        const void *val;
        uint32_t pos;
        bool r = read_item(sector, offset, &key, &val, &len, &pos);
        if (!r) break;
        offset = pos;
    }
    return offset;
}

/*
 * Compacts active sector and sets new active sector
 */
static void compact()
{
    uint8_t norcow_next_sector = (norcow_active_sector + 1) % NORCOW_SECTOR_COUNT;

    uint32_t offset = 0, offsetw = 0;

    for (;;) {
        // read item
        uint16_t k, l;
        const void *v;
        uint32_t pos;
        bool r = read_item(norcow_active_sector, offset, &k, &v, &l, &pos);
        if (!r) break;
        offset = pos;

        // check if not already saved
        const void *v2;
        uint16_t l2;
        r = find_item(norcow_next_sector, k, &v2, &l2);
        if (r) {
            continue;
        }

        // scan for latest instance
        uint32_t offsetr = offset;
        for (;;) {
            uint16_t k2;
            uint32_t posr;
            r = read_item(norcow_active_sector, offsetr, &k2, &v2, &l2, &posr);
            if (!r) break;
            if (k == k2) {
                v = v2;
                l = l2;
            }
            offsetr = posr;
        }

        // copy the last item
        uint32_t posw;
        r = write_item(norcow_next_sector, offsetw, k, v, l, &posw);
        if (!r) { } // TODO: error
        offsetw = posw;
    }

    norcow_erase(norcow_active_sector);
    norcow_active_sector = norcow_next_sector;
    norcow_active_offset = find_free_offset(norcow_active_sector);
}

/*
 * Initializes storage
 */
bool norcow_init(void)
{
#ifdef NORCOW_UNIX
    memset(norcow_buffer, 0xFF, sizeof(norcow_buffer));
    FILE *f = fopen(NORCOW_FILE, "rb");
    if (f) {
        size_t r = fread(norcow_buffer, sizeof(norcow_buffer), 1, f);
        fclose(f);
        if (r != 1) {
            memset(norcow_buffer, 0xFF, sizeof(norcow_buffer));
        }
    }
#endif
    // detect active sector (inactive sectors are empty = start with 0xFF)
    for (uint8_t i = 0; i < NORCOW_SECTOR_COUNT; i++) {
        const uint8_t *b = norcow_ptr(i, 0, 1);
        if (b != NULL && *b != 0xFF) {
            norcow_active_sector = i;
            break;
        }
    }
    norcow_active_offset = find_free_offset(norcow_active_sector);
    return true;
}

/*
 * Wipe the storage
 */
bool norcow_wipe(void)
{
    for (uint8_t i = 0; i < NORCOW_SECTOR_COUNT; i++) {
        if (!norcow_erase(i)) {
            return false;
        }
    }
    norcow_active_sector = 0;
    norcow_active_offset = 0;
    return true;
}

/*
 * Looks for the given key, returns status of the operation
 */
bool norcow_get(uint16_t key, const void **val, uint16_t *len)
{
    return find_item(norcow_active_sector, key, val, len);
}

/*
 * Sets the given key, returns status of the operation
 */
bool norcow_set(uint16_t key, const void *val, uint16_t len)
{
    // check whether there is enough free space
    // and compact if full
    if (norcow_active_offset + sizeof(uint32_t) + len > NORCOW_SECTOR_SIZE) {
        compact();
    }
    // write item
    uint32_t pos;
    bool r = write_item(norcow_active_sector, norcow_active_offset, key, val, len, &pos);
    if (r) {
        norcow_active_offset = pos;
    }
    return r;
}
