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
#include "norcow.h"

// NRC2 = 4e524332
#define NORCOW_MAGIC ((uint32_t)0x3243524e)
// NRCW = 4e524357
#define NORCOW_MAGIC_V0 ((uint32_t)0x5743524e)

#define NORCOW_WORD_SIZE (sizeof(uint32_t))
#define NORCOW_PREFIX_LEN NORCOW_WORD_SIZE
#define NORCOW_MAGIC_LEN NORCOW_WORD_SIZE
#define NORCOW_VERSION_LEN NORCOW_WORD_SIZE

// The key value which is used to indicate that the entry is not set.
#define NORCOW_KEY_FREE (0xFFFF)

// The key value which is used to indicate that the entry has been deleted.
#define NORCOW_KEY_DELETED (0x0000)

// The offset from the beginning of the sector where stored items start.
#define NORCOW_STORAGE_START \
  (NORCOW_HEADER_LEN + NORCOW_MAGIC_LEN + NORCOW_VERSION_LEN)

// Map from sector index to sector number.
static const uint8_t norcow_sectors[NORCOW_SECTOR_COUNT] = NORCOW_SECTORS;

// The index of the active reading sector and writing sector. These should be
// equal except when storage version upgrade or compaction is in progress.
static uint8_t norcow_active_sector = 0;
static uint8_t norcow_write_sector = 0;

// The norcow version of the reading sector.
static uint32_t norcow_active_version = 0;

// The offset of the first free item in the writing sector.
static uint32_t norcow_free_offset = 0;

/*
 * Returns pointer to sector, starting with offset
 * Fails when there is not enough space for data of given size
 */
static const void *norcow_ptr(uint8_t sector, uint32_t offset, uint32_t size) {
  ensure(sectrue * (sector <= NORCOW_SECTOR_COUNT), "invalid sector");
  return flash_get_address(norcow_sectors[sector], offset, size);
}

/*
 * Writes data to given sector, starting from offset
 */
static secbool norcow_write(uint8_t sector, uint32_t offset, uint32_t prefix,
                            const uint8_t *data, uint16_t len) {
  if (sector >= NORCOW_SECTOR_COUNT) {
    return secfalse;
  }

  if (offset + NORCOW_PREFIX_LEN + len > NORCOW_SECTOR_SIZE) {
    return secfalse;
  }

  ensure(flash_unlock_write(), NULL);

  // write prefix
  ensure(flash_write_word(norcow_sectors[sector], offset, prefix), NULL);
  offset += NORCOW_PREFIX_LEN;

  if (data != NULL) {
    // write data
    for (uint16_t i = 0; i < len; i++, offset++) {
      ensure(flash_write_byte(norcow_sectors[sector], offset, data[i]), NULL);
    }
  } else {
    offset += len;
  }

  // pad with zeroes
  for (; offset % NORCOW_WORD_SIZE; offset++) {
    ensure(flash_write_byte(norcow_sectors[sector], offset, 0x00), NULL);
  }

  ensure(flash_lock_write(), NULL);
  return sectrue;
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

  ensure(flash_erase(norcow_sectors[sector]), "erase failed");

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
    ensure(norcow_write(sector, NORCOW_HEADER_LEN, NORCOW_MAGIC, NULL, 0),
           "set magic failed");
    ensure(norcow_write(sector, NORCOW_HEADER_LEN + NORCOW_MAGIC_LEN,
                        ~NORCOW_VERSION, NULL, 0),
           "set version failed");
  }
}

#define ALIGN4(X) (X) = ((X) + 3) & ~3

/*
 * Reads one item starting from offset
 */
static secbool read_item(uint8_t sector, uint32_t offset, uint16_t *key,
                         const void **val, uint16_t *len, uint32_t *pos) {
  *pos = offset;

  const void *k = norcow_ptr(sector, *pos, 2);
  if (k == NULL) return secfalse;
  *pos += 2;
  memcpy(key, k, sizeof(uint16_t));
  if (*key == NORCOW_KEY_FREE) {
    return secfalse;
  }

  const void *l = norcow_ptr(sector, *pos, 2);
  if (l == NULL) return secfalse;
  *pos += 2;
  memcpy(len, l, sizeof(uint16_t));

  *val = norcow_ptr(sector, *pos, *len);
  if (*val == NULL) return secfalse;
  *pos += *len;
  ALIGN4(*pos);
  return sectrue;
}

/*
 * Writes one item starting from offset
 */
static secbool write_item(uint8_t sector, uint32_t offset, uint16_t key,
                          const void *val, uint16_t len, uint32_t *pos) {
  uint32_t prefix = ((uint32_t)len << 16) | key;
  *pos = offset + NORCOW_PREFIX_LEN + len;
  ALIGN4(*pos);
  return norcow_write(sector, offset, prefix, val, len);
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
  flash_init();
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

  const uint8_t sector_num = norcow_sectors[norcow_write_sector];
  secbool ret = secfalse;
  const void *ptr = NULL;
  uint16_t len_old = 0;
  *found = find_item(norcow_write_sector, key, &ptr, &len_old);

  // Try to update the entry if it already exists.
  uint32_t offset = 0;
  if (sectrue == *found) {
    offset =
        (const uint8_t *)ptr -
        (const uint8_t *)norcow_ptr(norcow_write_sector, 0, NORCOW_SECTOR_SIZE);
    if (val != NULL && len_old == len) {
      ret = sectrue;
      ensure(flash_unlock_write(), NULL);
      for (uint16_t i = 0; i < len; i++) {
        if (sectrue != flash_write_byte(sector_num, offset + i,
                                        ((const uint8_t *)val)[i])) {
          ret = secfalse;
          break;
        }
      }
      ensure(flash_lock_write(), NULL);
    }
  }

  // If the update was not possible then write the entry as a new item.
  if (secfalse == ret) {
    // Delete the old item.
    if (sectrue == *found) {
      ensure(flash_unlock_write(), NULL);

      // Update the prefix to indicate that the old item has been deleted.
      uint32_t prefix = (uint32_t)len_old << 16;
      ensure(flash_write_word(sector_num, offset - NORCOW_PREFIX_LEN, prefix),
             NULL);

      // Delete the old item data.
      uint32_t end = offset + len_old;
      while (offset < end) {
        ensure(flash_write_word(sector_num, offset, 0x00000000), NULL);
        offset += NORCOW_WORD_SIZE;
      }

      ensure(flash_lock_write(), NULL);
    }
    // Check whether there is enough free space and compact if full.
    if (norcow_free_offset + NORCOW_PREFIX_LEN + len > NORCOW_SECTOR_SIZE) {
      compact();
    }
    // Write new item.
    uint32_t pos = 0;
    ret = write_item(norcow_write_sector, norcow_free_offset, key, val, len,
                     &pos);
    if (sectrue == ret) {
      norcow_free_offset = pos;
    }
  }
  return ret;
}

/*
 * Deletes the given key, returns status of the operation.
 */
secbool norcow_delete(uint16_t key) {
  // Key 0xffff is used as a marker to indicate that the entry is not set.
  if (key == NORCOW_KEY_FREE) {
    return secfalse;
  }

  const uint8_t sector_num = norcow_sectors[norcow_write_sector];
  const void *ptr = NULL;
  uint16_t len = 0;
  if (sectrue != find_item(norcow_write_sector, key, &ptr, &len)) {
    return secfalse;
  }

  uint32_t offset =
      (const uint8_t *)ptr -
      (const uint8_t *)norcow_ptr(norcow_write_sector, 0, NORCOW_SECTOR_SIZE);

  ensure(flash_unlock_write(), NULL);

  // Update the prefix to indicate that the item has been deleted.
  uint32_t prefix = (uint32_t)len << 16;
  ensure(flash_write_word(sector_num, offset - NORCOW_PREFIX_LEN, prefix),
         NULL);

  // Delete the item data.
  uint32_t end = offset + len;
  while (offset < end) {
    ensure(flash_write_word(sector_num, offset, 0x00000000), NULL);
    offset += NORCOW_WORD_SIZE;
  }

  ensure(flash_lock_write(), NULL);

  return sectrue;
}

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
  if ((offset & 3) != 0 || offset >= len) {
    return secfalse;
  }
  uint32_t sector_offset =
      (const uint8_t *)ptr -
      (const uint8_t *)norcow_ptr(norcow_write_sector, 0, NORCOW_SECTOR_SIZE) +
      offset;
  ensure(flash_unlock_write(), NULL);
  ensure(flash_write_word(norcow_sectors[norcow_write_sector], sector_offset,
                          value),
         NULL);
  ensure(flash_lock_write(), NULL);
  return sectrue;
}

/*
 * Update the value of the given key starting at the given offset.
 */
secbool norcow_update_bytes(const uint16_t key, const uint16_t offset,
                            const uint8_t *data, const uint16_t len) {
  const void *ptr = NULL;
  uint16_t allocated_len = 0;
  if (sectrue != find_item(norcow_write_sector, key, &ptr, &allocated_len)) {
    return secfalse;
  }
  if (offset + len > allocated_len) {
    return secfalse;
  }
  uint32_t sector_offset =
      (const uint8_t *)ptr -
      (const uint8_t *)norcow_ptr(norcow_write_sector, 0, NORCOW_SECTOR_SIZE) +
      offset;
  uint8_t sector = norcow_sectors[norcow_write_sector];
  ensure(flash_unlock_write(), NULL);
  for (uint16_t i = 0; i < len; i++, sector_offset++) {
    ensure(flash_write_byte(sector, sector_offset, data[i]), NULL);
  }
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
