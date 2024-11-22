/*
 * This file is part of the Trezor project, https://trezor.io/
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
#include "flash_area.h"
#include "memzero.h"
#include "norcow.h"
#include "storage_utils.h"

// NRC2 = 4e524332
#define NORCOW_MAGIC ((uint32_t)0x3243524e)
// NRCW = 4e524357
#define NORCOW_MAGIC_V0 ((uint32_t)0x5743524e)

#define NORCOW_MAGIC_LEN sizeof(uint32_t)
#define NORCOW_VERSION_LEN sizeof(uint32_t)

// The offset from the beginning of the sector where stored items start.
#define NORCOW_STORAGE_START \
  FLASH_ALIGN(NORCOW_HEADER_LEN + NORCOW_MAGIC_LEN + NORCOW_VERSION_LEN)

// The key value which is used to indicate that the entry is not set.
#define NORCOW_KEY_FREE (0xFFFF)

// The key value which is used to indicate that the entry has been deleted.
#define NORCOW_KEY_DELETED (0x0000)

#define NORCOW_KEY_LEN 2
#define NORCOW_LEN_LEN 2

// The index of the active reading sector and writing sector. These should be
// equal except when storage version upgrade or compaction is in progress.
static uint8_t norcow_active_sector = 0;
static uint8_t norcow_write_sector = 0;

// The norcow version of the reading sector.
static uint32_t norcow_active_version = 0;

// The offset of the first free item in the writing sector.
static uint32_t norcow_free_offset = 0;

// Tracks how much data was already flashed in update_bytes function
static uint16_t norcow_write_buffer_flashed = 0;

static const void *norcow_ptr(uint8_t sector, uint32_t offset, uint32_t size);
static secbool find_item(uint8_t sector, uint16_t key, const void **val,
                         uint16_t *len);

#ifdef FLASH_BIT_ACCESS
#include "norcow_bitwise.h"
#else
#include "norcow_blockwise.h"
#endif

/*
 * Returns pointer to sector, starting with offset
 * Fails when there is not enough space for data of given size
 */
static const void *norcow_ptr(uint8_t sector, uint32_t offset, uint32_t size) {
  ensure(sectrue * (sector <= NORCOW_SECTOR_COUNT), "invalid sector");
  return flash_area_get_address(&STORAGE_AREAS[sector], offset, size);
}

/*
 * Erases sector (and sets a magic)
 */
static void erase_sector(uint8_t sector, secbool set_magic) {
#if NORCOW_HEADER_LEN > 0
  // Backup the sector header.
  uint32_t header_backup[NORCOW_HEADER_LEN / sizeof(uint32_t)] = {0};
  const void *sector_start = norcow_ptr(sector, 0, NORCOW_HEADER_LEN);
  memcpy(header_backup, sector_start, sizeof(header_backup));
#endif

  ensure(flash_area_erase(&STORAGE_AREAS[sector], NULL), "erase failed");

#if NORCOW_HEADER_LEN > 0
  // Copy the sector header back.
  ensure(flash_unlock_write(), NULL);
  for (uint32_t i = 0; i < NORCOW_HEADER_LEN / sizeof(uint32_t); ++i) {
    ensure(flash_write_word(norcow_sectors[sector], i * sizeof(uint32_t),
                            header_backup[i]),
           NULL);
  }
  ensure(flash_lock_write(), NULL);
#endif

  if (sectrue == set_magic) {
    ensure(flash_unlock_write(), NULL);
#if FLASH_BLOCK_WORDS == 1
    flash_block_t block_magic = {NORCOW_MAGIC};
    ensure(flash_area_write_block(&STORAGE_AREAS[sector], NORCOW_HEADER_LEN,
                                  block_magic),
           NULL);
    flash_block_t block_version = {~NORCOW_VERSION};
    ensure(flash_area_write_block(&STORAGE_AREAS[sector],
                                  NORCOW_HEADER_LEN + NORCOW_MAGIC_LEN,
                                  block_version),
           "set version failed");
#else
    flash_block_t block = {NORCOW_MAGIC, ~NORCOW_VERSION};
    ensure(flash_area_write_block(&STORAGE_AREAS[sector], NORCOW_HEADER_LEN,
                                  block),
           "set magic and version failed");
#endif
    ensure(flash_lock_write(), NULL);
  }
}

/*
 * Finds the offset from the beginning of the sector where stored items start.
 */
static secbool find_start_offset(uint8_t sector, uint32_t *offset,
                                 uint32_t *version) {
  const uint32_t *magic = norcow_ptr(sector, NORCOW_HEADER_LEN,
                                     NORCOW_MAGIC_LEN + NORCOW_VERSION_LEN);
  if (magic == NULL) {
    return secfalse;
  }

  if (*magic == NORCOW_MAGIC) {
    *offset = NORCOW_STORAGE_START;
    *version = ~(magic[1]);
  } else if (*magic == NORCOW_MAGIC_V0) {
    *offset = NORCOW_HEADER_LEN + NORCOW_MAGIC_LEN;
    *version = 0;
  } else {
    return secfalse;
  }

  return sectrue;
}

/*
 * Finds item in given sector
 */
static secbool find_item(uint8_t sector, uint16_t key, const void **val,
                         uint16_t *len) {
  *val = NULL;
  *len = 0;

  uint32_t offset = 0;
  uint32_t version = 0;
  if (sectrue != find_start_offset(sector, &offset, &version)) {
    return secfalse;
  }

  for (;;) {
    uint16_t k = 0, l = 0;
    const void *v = NULL;
    uint32_t pos = 0;
    if (sectrue != read_item(sector, offset, &k, &v, &l, &pos)) {
      break;
    }
    if (key == k) {
      *val = v;
      *len = l;
    }
    offset = pos;
  }
  return sectrue * (*val != NULL);
}

/*
 * Finds first unused offset in given sector
 */
static uint32_t find_free_offset(uint8_t sector) {
  uint32_t offset = 0;
  uint32_t version = 0;
  if (sectrue != find_start_offset(sector, &offset, &version)) {
    return secfalse;
  }

  for (;;) {
    uint16_t key = 0, len = 0;
    const void *val = NULL;
    uint32_t pos = 0;
    if (sectrue != read_item(sector, offset, &key, &val, &len, &pos)) {
      break;
    }
    offset = pos;
  }
  return offset;
}

/*
 * Compacts active sector and sets new active sector
 */
static void compact(void) {
  uint32_t offsetr = 0;
  uint32_t version = 0;
  if (sectrue != find_start_offset(norcow_active_sector, &offsetr, &version)) {
    return;
  }

  norcow_write_sector = (norcow_active_sector + 1) % NORCOW_SECTOR_COUNT;
  erase_sector(norcow_write_sector, sectrue);
  uint32_t offsetw = NORCOW_STORAGE_START;

  for (;;) {
    // read item
    uint16_t k = 0, l = 0;
    const void *v = NULL;
    uint32_t posr = 0;
    secbool r = read_item(norcow_active_sector, offsetr, &k, &v, &l, &posr);
    if (sectrue != r) {
      break;
    }
    offsetr = posr;

    // skip deleted items
    if (k == NORCOW_KEY_DELETED) {
      continue;
    }

    // copy the item
    uint32_t posw = 0;
    ensure(write_item(norcow_write_sector, offsetw, k, v, l, &posw),
           "compaction write failed");
    offsetw = posw;
  }

  erase_sector(norcow_active_sector, secfalse);
  norcow_active_sector = norcow_write_sector;
  norcow_active_version = NORCOW_VERSION;
  norcow_free_offset = find_free_offset(norcow_write_sector);
}

/*
 * Initializes storage
 */
void norcow_init(uint32_t *norcow_version) {
  secbool found = secfalse;
  *norcow_version = 0;
  norcow_active_sector = 0;
  // detect active sector - starts with magic and has highest version
  for (uint8_t i = 0; i < NORCOW_SECTOR_COUNT; i++) {
    uint32_t offset = 0;
    if (sectrue == find_start_offset(i, &offset, &norcow_active_version) &&
        norcow_active_version >= *norcow_version) {
      found = sectrue;
      norcow_active_sector = i;
      *norcow_version = norcow_active_version;
    }
  }

  // If no active sectors found or version downgrade, then erase.
  if (sectrue != found || *norcow_version > NORCOW_VERSION) {
    norcow_wipe();
    *norcow_version = NORCOW_VERSION;
  } else if (*norcow_version < NORCOW_VERSION) {
    // Prepare write sector for storage upgrade.
    norcow_write_sector = (norcow_active_sector + 1) % NORCOW_SECTOR_COUNT;
    erase_sector(norcow_write_sector, sectrue);
    norcow_free_offset = find_free_offset(norcow_write_sector);
  } else {
    norcow_write_sector = norcow_active_sector;
    norcow_free_offset = find_free_offset(norcow_write_sector);
  }
}

/*
 * Wipe the storage
 */
void norcow_wipe(void) {
  // Erase the active sector first, because it contains sensitive data.
  erase_sector(norcow_active_sector, sectrue);

#if STORAGE_INSECURE_TESTING_MODE && !PRODUCTION
  // skip erasing inactive sectors
#else
  for (uint8_t i = 0; i < NORCOW_SECTOR_COUNT; i++) {
    if (i != norcow_active_sector) {
      erase_sector(i, secfalse);
    }
  }
#endif
  norcow_active_version = NORCOW_VERSION;
  norcow_write_sector = norcow_active_sector;
  norcow_free_offset = NORCOW_STORAGE_START;
}

/*
 * Looks for the given key, returns status of the operation
 */
secbool norcow_get(uint16_t key, const void **val, uint16_t *len) {
  return find_item(norcow_active_sector, key, val, len);
}

/*
 * Reads the next entry in the storage starting at offset. Returns secfalse if
 * there is none.
 */
secbool norcow_get_next(uint32_t *offset, uint16_t *key, const void **val,
                        uint16_t *len) {
  if (*offset == 0) {
    uint32_t version = 0;
    if (sectrue != find_start_offset(norcow_active_sector, offset, &version)) {
      return secfalse;
    }
  }

  for (;;) {
    uint32_t pos = 0;
    secbool ret = read_item(norcow_active_sector, *offset, key, val, len, &pos);
    if (sectrue != ret) {
      break;
    }
    *offset = pos;

    // Skip deleted items.
    if (*key == NORCOW_KEY_DELETED) {
      continue;
    }

    if (norcow_active_version == 0) {
      // Check whether the item is the latest instance.
      uint32_t offsetr = *offset;
      for (;;) {
        uint16_t k = 0;
        uint16_t l = 0;
        const void *v = NULL;
        ret = read_item(norcow_active_sector, offsetr, &k, &v, &l, &offsetr);
        if (sectrue != ret) {
          // There is no newer instance of the item.
          return sectrue;
        }
        if (*key == k) {
          // There exists a newer instance of the item.
          break;
        }
      }
    } else {
      return sectrue;
    }
  }
  return secfalse;
}

/*
 * Sets the given key, returns status of the operation. If NULL is passed
 * as val, then norcow_set allocates a new key of size len. The value should
 * then be written using norcow_update_bytes().
 */
secbool norcow_set(uint16_t key, const void *val, uint16_t len) {
  secbool found = secfalse;
  return norcow_set_ex(key, val, len, &found);
}

secbool norcow_set_ex(uint16_t key, const void *val, uint16_t len,
                      secbool *found) {
  // Key 0xffff is used as a marker to indicate that the entry is not set.
  if (key == NORCOW_KEY_FREE) {
    return secfalse;
  }

  const flash_area_t *area = &STORAGE_AREAS[norcow_write_sector];
  const void *ptr = NULL;
  uint16_t len_old = 0;
  *found = find_item(norcow_write_sector, key, &ptr, &len_old);

  uint32_t val_offset = 0;
  if (sectrue == *found) {
    val_offset =
        (const uint8_t *)ptr -
        (const uint8_t *)norcow_ptr(norcow_write_sector, 0, NORCOW_SECTOR_SIZE);
    // Try to update the entry if it already exists.
    if (sectrue ==
        flash_area_write_bytes(area, val_offset, len_old, val, len)) {
      return sectrue;
    }
  }

  // Delete the old item.
  if (sectrue == *found) {
    norcow_delete_item(area, len_old, val_offset);
  }

  // Check whether there is enough free space and compact if full.
  if (norcow_free_offset + FLASH_ALIGN(NORCOW_MAX_PREFIX_LEN + len) >
      NORCOW_SECTOR_SIZE) {
    compact();
  }

  // Write new item.
  uint32_t pos = 0;
  if (sectrue != write_item(norcow_write_sector, norcow_free_offset, key, val,
                            len, &pos)) {
    return secfalse;
  }

  norcow_free_offset = pos;
  return sectrue;
}

/*
 * Deletes the given key, returns status of the operation.
 */
secbool norcow_delete(uint16_t key) {
  // Key 0xffff is used as a marker to indicate that the entry is not set.
  if (key == NORCOW_KEY_FREE) {
    return secfalse;
  }

  const flash_area_t *area = &STORAGE_AREAS[norcow_write_sector];
  const void *ptr = NULL;
  uint16_t len = 0;
  if (sectrue != find_item(norcow_write_sector, key, &ptr, &len)) {
    return secfalse;
  }

  uint32_t val_offset =
      (const uint8_t *)ptr -
      (const uint8_t *)norcow_ptr(norcow_write_sector, 0, NORCOW_SECTOR_SIZE);

  norcow_delete_item(area, len, val_offset);

  return sectrue;
}

secbool norcow_set_counter(uint16_t key, uint32_t count) {
  // The count is stored as a 32-bit integer followed by a tail of "1" bits,
  // which is used as a tally.
  uint32_t value[1 + COUNTER_TAIL_WORDS] = {0};
  value[0] = count;
  memset(&value[1], 0xff, sizeof(value) - sizeof(value[0]));
  return norcow_set(key, value, sizeof(value));
}

/*
 * Complete storage version upgrade
 */
secbool norcow_upgrade_finish(void) {
  erase_sector(norcow_active_sector, secfalse);
  norcow_active_sector = norcow_write_sector;
  norcow_active_version = NORCOW_VERSION;
  return sectrue;
}
