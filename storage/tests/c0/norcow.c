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

// NRCW = 4e524357
#define NORCOW_MAGIC ((uint32_t)0x5743524e)
#define NORCOW_MAGIC_LEN (sizeof(uint32_t))

static const uint8_t norcow_sectors[NORCOW_SECTOR_COUNT] = NORCOW_SECTORS;
static uint8_t norcow_active_sector = 0;
static uint32_t norcow_active_offset = NORCOW_MAGIC_LEN;

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
  ensure(flash_unlock(), NULL);

  // write prefix
  ensure(flash_write_word(norcow_sectors[sector], offset, prefix), NULL);

  if (len > 0) {
    offset += sizeof(uint32_t);
    // write data
    for (uint16_t i = 0; i < len; i++, offset++) {
      ensure(flash_write_byte(norcow_sectors[sector], offset, data[i]), NULL);
    }
    // pad with zeroes
    for (; offset % 4; offset++) {
      ensure(flash_write_byte(norcow_sectors[sector], offset, 0x00), NULL);
    }
  }
  ensure(flash_lock(), NULL);
  return sectrue;
}

/*
 * Erases sector (and sets a magic)
 */
static void norcow_erase(uint8_t sector, secbool set_magic) {
  ensure(sectrue * (sector <= NORCOW_SECTOR_COUNT), "invalid sector");
  ensure(flash_erase_sector(norcow_sectors[sector]), "erase failed");
  if (sectrue == set_magic) {
    ensure(norcow_write(sector, 0, NORCOW_MAGIC, NULL, 0), "set magic failed");
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
  if (*key == 0xFFFF) {
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
  uint32_t prefix = (len << 16) | key;
  *pos = offset + sizeof(uint32_t) + len;
  ALIGN4(*pos);
  return norcow_write(sector, offset, prefix, val, len);
}

/*
 * Finds item in given sector
 */
static secbool find_item(uint8_t sector, uint16_t key, const void **val,
                         uint16_t *len) {
  *val = 0;
  *len = 0;
  uint32_t offset = NORCOW_MAGIC_LEN;
  for (;;) {
    uint16_t k, l;
    const void *v;
    uint32_t pos;
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
  uint32_t offset = NORCOW_MAGIC_LEN;
  for (;;) {
    uint16_t key, len;
    const void *val;
    uint32_t pos;
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
static void compact() {
  uint8_t norcow_next_sector = (norcow_active_sector + 1) % NORCOW_SECTOR_COUNT;
  norcow_erase(norcow_next_sector, sectrue);

  uint32_t offset = NORCOW_MAGIC_LEN, offsetw = NORCOW_MAGIC_LEN;

  for (;;) {
    // read item
    uint16_t k, l;
    const void *v;
    uint32_t pos;
    secbool r = read_item(norcow_active_sector, offset, &k, &v, &l, &pos);
    if (sectrue != r) {
      break;
    }
    offset = pos;

    // check if not already saved
    const void *v2;
    uint16_t l2;
    r = find_item(norcow_next_sector, k, &v2, &l2);
    if (sectrue == r) {
      continue;
    }

    // scan for latest instance
    uint32_t offsetr = offset;
    for (;;) {
      uint16_t k2;
      uint32_t posr;
      r = read_item(norcow_active_sector, offsetr, &k2, &v2, &l2, &posr);
      if (sectrue != r) {
        break;
      }
      if (k == k2) {
        v = v2;
        l = l2;
      }
      offsetr = posr;
    }

    // copy the last item
    uint32_t posw;
    ensure(write_item(norcow_next_sector, offsetw, k, v, l, &posw),
           "compaction write failed");
    offsetw = posw;
  }

  norcow_erase(norcow_active_sector, secfalse);
  norcow_active_sector = norcow_next_sector;
  norcow_active_offset = find_free_offset(norcow_active_sector);
}

/*
 * Initializes storage
 */
void norcow_init(void) {
  flash_init();
  secbool found = secfalse;
  // detect active sector - starts with magic
  for (uint8_t i = 0; i < NORCOW_SECTOR_COUNT; i++) {
    const uint32_t *magic = norcow_ptr(i, 0, NORCOW_MAGIC_LEN);
    if (magic != NULL && *magic == NORCOW_MAGIC) {
      found = sectrue;
      norcow_active_sector = i;
      break;
    }
  }
  // no active sectors found - let's erase
  if (sectrue == found) {
    norcow_active_offset = find_free_offset(norcow_active_sector);
  } else {
    norcow_wipe();
  }
}

/*
 * Wipe the storage
 */
void norcow_wipe(void) {
  norcow_erase(0, sectrue);
  for (uint8_t i = 1; i < NORCOW_SECTOR_COUNT; i++) {
    norcow_erase(i, secfalse);
  }
  norcow_active_sector = 0;
  norcow_active_offset = NORCOW_MAGIC_LEN;
}

/*
 * Looks for the given key, returns status of the operation
 */
secbool norcow_get(uint16_t key, const void **val, uint16_t *len) {
  return find_item(norcow_active_sector, key, val, len);
}

/*
 * Sets the given key, returns status of the operation
 */
secbool norcow_set(uint16_t key, const void *val, uint16_t len) {
  // check whether there is enough free space
  // and compact if full
  if (norcow_active_offset + sizeof(uint32_t) + len > NORCOW_SECTOR_SIZE) {
    compact();
  }
  // write item
  uint32_t pos;
  secbool r = write_item(norcow_active_sector, norcow_active_offset, key, val,
                         len, &pos);
  if (sectrue == r) {
    norcow_active_offset = pos;
  }
  return r;
}

/*
 * Update a word in flash at the given pointer.  The pointer must point
 * into the NORCOW area.
 */
secbool norcow_update(uint16_t key, uint16_t offset, uint32_t value) {
  const void *ptr;
  uint16_t len;
  if (sectrue != find_item(norcow_active_sector, key, &ptr, &len)) {
    return secfalse;
  }
  if ((offset & 3) != 0 || offset >= len) {
    return secfalse;
  }
  uint32_t sector_offset =
      (const uint8_t *)ptr -
      (const uint8_t *)norcow_ptr(norcow_active_sector, 0, NORCOW_SECTOR_SIZE) +
      offset;
  ensure(flash_unlock(), NULL);
  ensure(flash_write_word(norcow_sectors[norcow_active_sector], sector_offset,
                          value),
         NULL);
  ensure(flash_lock(), NULL);
  return sectrue;
}
