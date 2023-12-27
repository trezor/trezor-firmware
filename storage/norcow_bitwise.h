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

#include "flash_common.h"

#define COUNTER_TAIL_WORDS 2
#define NORCOW_MAX_PREFIX_LEN (NORCOW_KEY_LEN + NORCOW_LEN_LEN)

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
  offset += sizeof(prefix);

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

/*
 * Reads one item starting from offset
 */
static secbool read_item(uint8_t sector, uint32_t offset, uint16_t *key,
                         const void **val, uint16_t *len, uint32_t *pos) {
  *pos = offset;
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

  *val = norcow_ptr(sector, *pos, *len);
  if (*val == NULL) return secfalse;
  *pos = FLASH_ALIGN(*pos + *len);
  return sectrue;
}

void norcow_delete_head(const flash_area_t *area, uint16_t len,
                        uint32_t val_offset) {
  ensure(flash_unlock_write(), NULL);
  // Update the prefix to indicate that the item has been deleted.
  uint32_t prefix = (uint32_t)len << 16;
  ensure(flash_area_write_word(area, val_offset - sizeof(prefix), prefix),
         NULL);
  ensure(flash_lock_write(), NULL);
}

void norcow_delete_item(const flash_area_t *area, uint16_t len,
                        uint32_t val_offset) {
  uint32_t end = val_offset + len;
  norcow_delete_head(area, len, val_offset);

  // Delete the item data.
  ensure(flash_unlock_write(), NULL);
  flash_block_t block = {0};
  while (val_offset < end) {
    ensure(flash_area_write_block(area, val_offset, block), NULL);
    val_offset += FLASH_BLOCK_SIZE;
  }

  ensure(flash_lock_write(), NULL);
}

/*
 * Tries to update a part of flash memory with a given value.
 */
static secbool flash_area_write_bytes(const flash_area_t *area, uint32_t offset,
                                      uint16_t dest_len, const void *val,
                                      uint16_t len) {
  if (val == NULL || dest_len != len) {
    return secfalse;
  }

  secbool updated = sectrue;
  ensure(flash_unlock_write(), NULL);
  for (uint16_t i = 0; i < len; i++) {
    if (sectrue !=
        flash_area_write_byte(area, offset + i, ((const uint8_t *)val)[i])) {
      updated = secfalse;
      break;
    }
  }
  ensure(flash_lock_write(), NULL);
  return updated;
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
    return norcow_update_word(key, sizeof(uint32_t) * i, val_stored[i] >> 1);
  } else {
    return norcow_set_counter(key, *count);
  }
}

/*
 * Update the value of the given key. The value is updated sequentially,
 * starting from position 0, caller needs to ensure that all bytes are updated
 * by calling this function enough times.
 */
secbool norcow_update_bytes(const uint16_t key, const uint8_t *data,
                            const uint16_t len) {
  const void *ptr = NULL;
  uint16_t allocated_len = 0;
  if (sectrue != find_item(norcow_write_sector, key, &ptr, &allocated_len)) {
    return secfalse;
  }

  if (norcow_write_buffer_flashed + len > allocated_len) {
    return secfalse;
  }
  uint32_t sector_offset =
      (const uint8_t *)ptr -
      (const uint8_t *)norcow_ptr(norcow_write_sector, 0, NORCOW_SECTOR_SIZE);

  const flash_area_t *area = &STORAGE_AREAS[norcow_write_sector];
  ensure(flash_unlock_write(), NULL);

  sector_offset += norcow_write_buffer_flashed;
  for (uint16_t i = 0; i < len; i++, sector_offset++) {
    ensure(flash_area_write_byte(area, sector_offset, data[i]), NULL);
  }
  norcow_write_buffer_flashed += len;
  if (norcow_write_buffer_flashed >= allocated_len) {
    norcow_write_buffer_flashed = 0;
  }

  ensure(flash_lock_write(), NULL);
  return sectrue;
}
