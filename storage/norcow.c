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
#include "flash.h"
#include "memzero.h"
#include "norcow.h"
#include "storage_utils.h"

// NRC2 = 4e524332
#define NORCOW_MAGIC ((uint32_t)0x3243524e)
// NRCW = 4e524357
#define NORCOW_MAGIC_V0 ((uint32_t)0x5743524e)

#define NORCOW_MAGIC_LEN sizeof(uint32_t)
#define NORCOW_VERSION_LEN sizeof(uint32_t)

// The key value which is used to indicate that the entry is not set.
#define NORCOW_KEY_FREE (0xFFFF)

// The key value which is used to indicate that the entry has been deleted.
#define NORCOW_KEY_DELETED (0x0000)

#define NORCOW_KEY_LEN 2
#define NORCOW_LEN_LEN 2

#ifdef FLASH_BYTE_ACCESS
#define COUNTER_TAIL_WORDS 2
#define NORCOW_MAX_PREFIX_LEN (FLASH_BLOCK_SIZE)
// The offset from the beginning of the sector where stored items start.
#define NORCOW_STORAGE_START \
  (NORCOW_HEADER_LEN + NORCOW_MAGIC_LEN + NORCOW_VERSION_LEN)

#else
#define COUNTER_TAIL_WORDS 0
// Small items are encoded more efficiently.
#define NORCOW_SMALL_ITEM_SIZE \
  (FLASH_BLOCK_SIZE - NORCOW_LEN_LEN - NORCOW_KEY_LEN)
// Larger items store first part of data with the same QW as key
#define NORCOW_VALID_FLAG 0xFE
#define NORCOW_VALID_FLAG_LEN 1
#define NORCOW_DATA_OPT_SIZE (FLASH_BLOCK_SIZE - NORCOW_VALID_FLAG_LEN)
#define NORCOW_MAX_PREFIX_LEN (FLASH_BLOCK_SIZE + NORCOW_VALID_FLAG_LEN)
// The offset from the beginning of the sector where stored items start.
#define NORCOW_STORAGE_START (NORCOW_HEADER_LEN + FLASH_BLOCK_SIZE)
#endif

// The index of the active reading sector and writing sector. These should be
// equal except when storage version upgrade or compaction is in progress.
static uint8_t norcow_active_sector = 0;
static uint8_t norcow_write_sector = 0;

// The norcow version of the reading sector.
static uint32_t norcow_active_version = 0;

// The offset of the first free item in the writing sector.
static uint32_t norcow_free_offset = 0;

static uint16_t norcow_write_buffer_flashed = 0;
#ifndef FLASH_BYTE_ACCESS
static flash_block_t norcow_write_buffer = {0};
static uint16_t norcow_write_buffer_filled = 0;
static uint16_t norcow_write_buffer_filled_data = 0;
static int32_t norcow_write_buffer_key = -1;
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
 * Writes data to given sector, starting from offset
 */
#ifdef FLASH_BYTE_ACCESS
static secbool write_item(uint8_t sector, uint32_t offset, uint16_t key,
                          const uint8_t *data, uint16_t len, uint32_t *pos) {
  if (sector >= NORCOW_SECTOR_COUNT) {
    return secfalse;
  }

  if (offset + NORCOW_MAX_PREFIX_LEN + len > NORCOW_SECTOR_SIZE) {
    return secfalse;
  }

  uint32_t prefix = ((uint32_t)len << 16) | key;

  ensure(flash_unlock_write(), NULL);

  // write prefix
  ensure(flash_area_write_word(&STORAGE_AREAS[sector], offset, prefix), NULL);
  offset += NORCOW_MAX_PREFIX_LEN;

  if (data != NULL) {
    // write data
    for (uint16_t i = 0; i < len; i++, offset++) {
      ensure(flash_area_write_byte(&STORAGE_AREAS[sector], offset, data[i]),
             NULL);
    }
  } else {
    offset += len;
  }

  // pad with zeroes
  for (; offset % FLASH_BLOCK_SIZE; offset++) {
    ensure(flash_area_write_byte(&STORAGE_AREAS[sector], offset, 0x00), NULL);
  }

  ensure(flash_lock_write(), NULL);
  *pos = offset;
  return sectrue;
}
#else
static secbool write_item(uint8_t sector, uint32_t offset, uint16_t key,
                          const uint8_t *data, uint16_t len, uint32_t *pos) {
  if (sector >= NORCOW_SECTOR_COUNT) {
    return secfalse;
  }

  flash_block_t block = {len | ((uint32_t)key << 16)};
  if (len <= NORCOW_SMALL_ITEM_SIZE) {
    // the whole item fits into one block, let's not waste space
    if (offset + FLASH_BLOCK_SIZE > NORCOW_SECTOR_SIZE) {
      return secfalse;
    }

    if (len > 0) {
      memcpy(&block[1], data, len);  // write data
    }

    ensure(flash_unlock_write(), NULL);
    ensure(flash_area_write_block(&STORAGE_AREAS[sector], offset, block), NULL);
    ensure(flash_lock_write(), NULL);
    *pos = offset + FLASH_BLOCK_SIZE;
  } else {
    uint16_t len_adjusted = FLASH_ALIGN(len);

    if (offset + NORCOW_MAX_PREFIX_LEN + len_adjusted > NORCOW_SECTOR_SIZE) {
      return secfalse;
    }

    ensure(flash_unlock_write(), NULL);

    // write len
    ensure(flash_area_write_block(&STORAGE_AREAS[sector], offset, block), NULL);
    offset += FLASH_BLOCK_SIZE;

    *pos = FLASH_ALIGN(offset + NORCOW_VALID_FLAG_LEN + len);
    if (data != NULL) {
      // write key and first data part
      uint16_t len_to_write =
          len > NORCOW_DATA_OPT_SIZE ? NORCOW_DATA_OPT_SIZE : len;
      memset(block, 0, sizeof(block));
      block[0] = NORCOW_VALID_FLAG;
      memcpy(&(((uint8_t *)block)[NORCOW_VALID_FLAG_LEN]), data, len_to_write);
      ensure(flash_area_write_block(&STORAGE_AREAS[sector], offset, block),
             NULL);
      offset += FLASH_BLOCK_SIZE;
      data += len_to_write;
      len -= len_to_write;

      while (len > 0) {
        len_to_write = len > FLASH_BLOCK_SIZE ? FLASH_BLOCK_SIZE : len;
        memset(block, 0, sizeof(block));
        memcpy(block, data, len_to_write);
        ensure(flash_area_write_block(&STORAGE_AREAS[sector], offset, block),
               NULL);
        offset += FLASH_BLOCK_SIZE;
        data += len_to_write;
        len -= len_to_write;
      }
      memzero(block, sizeof(block));
    }

    ensure(flash_lock_write(), NULL);
  }
  return sectrue;
}
#endif

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
    ensure(flash_area_write_block(&STORAGE_AREAS[sector], NORCOW_HEADER_LEN,
                                  NORCOW_MAGIC),
           NULL);
    ensure(flash_area_write_block(&STORAGE_AREAS[sector],
                                  NORCOW_HEADER_LEN + NORCOW_MAGIC_LEN,
                                  ~NORCOW_VERSION),
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
 * Reads one item starting from offset
 */
static secbool read_item(uint8_t sector, uint32_t offset, uint16_t *key,
                         const void **val, uint16_t *len, uint32_t *pos) {
  *pos = offset;

#ifdef FLASH_BYTE_ACCESS
  const void *k = norcow_ptr(sector, *pos, NORCOW_KEY_LEN);
  if (k == NULL) return secfalse;
  *pos += NORCOW_KEY_LEN;
  memcpy(key, k, sizeof(uint16_t));
  if (*key == NORCOW_KEY_FREE) {
    return secfalse;
  }

  const void *l = norcow_ptr(sector, *pos, NORCOW_LEN_LEN);
  if (l == NULL) return secfalse;
  *pos += NORCOW_LEN_LEN;
  memcpy(len, l, sizeof(uint16_t));
#else
  const void *l = norcow_ptr(sector, *pos, NORCOW_LEN_LEN);
  if (l == NULL) return secfalse;
  memcpy(len, l, sizeof(uint16_t));

  if (*len <= NORCOW_SMALL_ITEM_SIZE) {
    *pos += NORCOW_LEN_LEN;
    const void *k = norcow_ptr(sector, *pos, NORCOW_KEY_LEN);
    if (k == NULL) return secfalse;
    memcpy(key, k, sizeof(uint16_t));
    if (*key == NORCOW_KEY_FREE) {
      return secfalse;
    }
    *pos += NORCOW_KEY_LEN;
  } else {
    *pos += NORCOW_LEN_LEN;
    const void *k = norcow_ptr(sector, *pos, NORCOW_KEY_LEN);
    if (k == NULL) return secfalse;

    *pos += (NORCOW_KEY_LEN + NORCOW_SMALL_ITEM_SIZE);

    const void *flg = norcow_ptr(sector, *pos, NORCOW_VALID_FLAG_LEN);
    if (flg == NULL) return secfalse;

    *pos += NORCOW_VALID_FLAG_LEN;
    if (*((const uint8_t *)flg) == 0) {
      // Deleted item.
      *key = NORCOW_KEY_DELETED;
    } else {
      memcpy(key, k, sizeof(uint16_t));
      if (*key == NORCOW_KEY_FREE) {
        return secfalse;
      }
    }
  }

#endif

  *val = norcow_ptr(sector, *pos, *len);
  if (*val == NULL) return secfalse;
  *pos = FLASH_ALIGN(*pos + *len);
  return sectrue;
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

  for (uint8_t i = 0; i < NORCOW_SECTOR_COUNT; i++) {
    if (i != norcow_active_sector) {
      erase_sector(i, secfalse);
    }
  }
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

void norcow_delete_head(const flash_area_t *area, uint32_t len,
                        uint32_t *val_offset) {
  ensure(flash_unlock_write(), NULL);
#ifdef FLASH_BYTE_ACCESS
  // Update the prefix to indicate that the item has been deleted.
  uint32_t prefix = (uint32_t)len << 16;
  ensure(
      flash_area_write_word(area, *val_offset - NORCOW_MAX_PREFIX_LEN, prefix),
      NULL);
#else
  // Move to the beginning of the block.
  if (len <= NORCOW_SMALL_ITEM_SIZE) {
    // Will delete the entire small item, setting the length to 0
    *val_offset -= NORCOW_LEN_LEN + NORCOW_KEY_LEN;
  } else {
    // Will update the flag to indicate that the old item has been deleted.
    // Deletes a portion of old item data too.
    *val_offset -= NORCOW_VALID_FLAG_LEN;
  }

  flash_block_t block = {0};
  ensure(flash_area_write_block(area, *val_offset, block), NULL);

  // Move to the next block.
  *val_offset += FLASH_BLOCK_SIZE;
#endif
  ensure(flash_lock_write(), NULL);
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
#ifdef FLASH_BYTE_ACCESS
    if (val != NULL && len_old == len) {
      secbool updated = sectrue;
      ensure(flash_unlock_write(), NULL);
      for (uint16_t i = 0; i < len; i++) {
        if (sectrue != flash_area_write_byte(area, val_offset + i,
                                             ((const uint8_t *)val)[i])) {
          updated = secfalse;
          break;
        }
      }
      ensure(flash_lock_write(), NULL);
      if (sectrue == updated) {
        return sectrue;
      }
    }
#endif
  }

  // Delete the old item.
  if (sectrue == *found) {
    uint32_t end = val_offset + len_old;
    norcow_delete_head(area, len_old, &val_offset);

    // Delete the old item data.
    ensure(flash_unlock_write(), NULL);
    flash_block_t block = {0};
    while (val_offset < end) {
      ensure(flash_area_write_block(area, val_offset, block), NULL);
      val_offset += FLASH_BLOCK_SIZE;
    }

    ensure(flash_lock_write(), NULL);
  }

  // Check whether there is enough free space and compact if full.
  if (norcow_free_offset + NORCOW_MAX_PREFIX_LEN + len > NORCOW_SECTOR_SIZE) {
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

  uint32_t end = val_offset + len;
  norcow_delete_head(area, len, &val_offset);

  // Delete the item data.
  ensure(flash_unlock_write(), NULL);
  flash_block_t block = {0};
  while (val_offset < end) {
    ensure(flash_area_write_block(area, val_offset, block), NULL);
    val_offset += FLASH_BLOCK_SIZE;
  }

  ensure(flash_lock_write(), NULL);

  return sectrue;
}

#ifdef FLASH_BYTE_ACCESS
/*
 * Update a word in flash at the given pointer.  The pointer must point
 * into the NORCOW area.
 */
secbool norcow_update_word(uint16_t key, uint16_t offset, uint32_t value) {
  const void *ptr = NULL;
  uint16_t len = 0;
  if (sectrue != find_item(norcow_write_sector, key, &ptr, &len)) {
    return secfalse;
  }
  if (!FLASH_IS_ALIGNED(offset) || offset >= len) {
    return secfalse;
  }
  uint32_t sector_offset =
      (const uint8_t *)ptr -
      (const uint8_t *)norcow_ptr(norcow_write_sector, 0, NORCOW_SECTOR_SIZE) +
      offset;
  ensure(flash_unlock_write(), NULL);
  ensure(flash_area_write_word(&STORAGE_AREAS[norcow_write_sector],
                               sector_offset, value),
         NULL);
  ensure(flash_lock_write(), NULL);
  return sectrue;
}
#endif

secbool norcow_set_counter(uint16_t key, uint32_t count) {
  // The count is stored as a 32-bit integer followed by a tail of "1" bits,
  // which is used as a tally.
  uint32_t value[1 + COUNTER_TAIL_WORDS] = {0};
  value[0] = count;
  memset(&value[1], 0xff, sizeof(value) - sizeof(value[0]));
  return norcow_set(key, value, sizeof(value));
}

secbool norcow_next_counter(uint16_t key, uint32_t *count) {
  uint16_t len = 0;
  const uint32_t *val_stored = NULL;
  if (sectrue != norcow_get(key, (const void **)&val_stored, &len)) {
    *count = 0;
    return norcow_set_counter(key, 0);
  }

  if (len < sizeof(uint32_t) || len % sizeof(uint32_t) != 0) {
    return secfalse;
  }
  uint16_t len_words = len / sizeof(uint32_t);

  uint16_t i = 1;
  while (i < len_words && val_stored[i] == 0) {
    ++i;
  }

  *count = val_stored[0] + 1 + 32 * (i - 1);
  if (*count < val_stored[0]) {
    // Value overflow.
    return secfalse;
  }

  if (i < len_words) {
    *count += hamming_weight(~val_stored[i]);
    if (*count < val_stored[0]) {
      // Value overflow.
      return secfalse;
    }
#ifdef FLASH_BYTE_ACCESS
    return norcow_update_word(key, sizeof(uint32_t) * i, val_stored[i] >> 1);
#else
    return norcow_set_counter(key, *count);
#endif
  } else {
    return norcow_set_counter(key, *count);
  }
}

/*
 * Update the value of the given key starting at the given offset.
 */
secbool norcow_update_bytes(const uint16_t key, const uint8_t *data,
                            const uint16_t len) {
  const void *ptr = NULL;
  uint16_t allocated_len = 0;
  if (sectrue != find_item(norcow_write_sector, key, &ptr, &allocated_len)) {
    return secfalse;
  }
#ifndef FLASH_BYTE_ACCESS
  if (allocated_len <= NORCOW_SMALL_ITEM_SIZE) {
    // small items are not updated in place
    return secfalse;
  }
#endif
  if (norcow_write_buffer_flashed + len > allocated_len) {
    return secfalse;
  }
  uint32_t sector_offset =
      (const uint8_t *)ptr -
      (const uint8_t *)norcow_ptr(norcow_write_sector, 0, NORCOW_SECTOR_SIZE);

  const flash_area_t *area = &STORAGE_AREAS[norcow_write_sector];
  ensure(flash_unlock_write(), NULL);
#ifdef FLASH_BYTE_ACCESS
  sector_offset += norcow_write_buffer_flashed;
  for (uint16_t i = 0; i < len; i++, sector_offset++) {
    ensure(flash_area_write_byte(area, sector_offset, data[i]), NULL);
  }
  norcow_write_buffer_flashed += len;
  if (norcow_write_buffer_flashed >= allocated_len) {
    norcow_write_buffer_flashed = 0;
  }
#else
  if (norcow_write_buffer_key != key && norcow_write_buffer_key != -1) {
    // some other update bytes is in process, abort
    return secfalse;
  }

  if (norcow_write_buffer_key == -1) {
    memset(norcow_write_buffer, 0, sizeof(norcow_write_buffer));
    norcow_write_buffer_key = key;
    norcow_write_buffer[0] = NORCOW_VALID_FLAG;
    norcow_write_buffer_filled = NORCOW_VALID_FLAG_LEN;
    norcow_write_buffer_filled_data = 0;
    norcow_write_buffer_flashed = 0;
  }

  uint16_t tmp_len = len;
  uint16_t flash_offset =
      sector_offset - NORCOW_VALID_FLAG_LEN + norcow_write_buffer_flashed;
  while (tmp_len > 0) {
    uint16_t buffer_space = FLASH_BLOCK_SIZE - norcow_write_buffer_filled;
    uint16_t data_to_copy = (tmp_len > buffer_space ? buffer_space : tmp_len);
    memcpy(&((uint8_t *)norcow_write_buffer)[norcow_write_buffer_filled], data,
           data_to_copy);
    data += data_to_copy;
    norcow_write_buffer_filled += data_to_copy;
    norcow_write_buffer_filled_data += data_to_copy;
    tmp_len -= data_to_copy;

    if (norcow_write_buffer_filled == FLASH_BLOCK_SIZE ||
        (norcow_write_buffer_filled_data + norcow_write_buffer_flashed) ==
            allocated_len + NORCOW_VALID_FLAG_LEN) {
      ensure(flash_area_write_block(area, flash_offset, norcow_write_buffer),
             NULL);
      ensure(flash_area_write_block(area, flash_offset, norcow_write_buffer),
             NULL);
      flash_offset += FLASH_BLOCK_SIZE;
      norcow_write_buffer_filled = 0;
      norcow_write_buffer_flashed += FLASH_BLOCK_SIZE;
      memset(norcow_write_buffer, 0, sizeof(norcow_write_buffer));

      if ((norcow_write_buffer_flashed) >=
          allocated_len + NORCOW_VALID_FLAG_LEN) {
        norcow_write_buffer_key = -1;
        norcow_write_buffer_flashed = 0;
      }
      norcow_write_buffer_filled_data = 0;
    }
  }

#endif
  ensure(flash_lock_write(), NULL);
  return sectrue;
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
