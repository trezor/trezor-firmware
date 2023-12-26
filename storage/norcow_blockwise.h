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

#define COUNTER_TAIL_WORDS 0
// Small items are encoded more efficiently.
#define NORCOW_SMALL_ITEM_SIZE \
  (FLASH_BLOCK_SIZE - NORCOW_LEN_LEN - NORCOW_KEY_LEN)
#define NORCOW_VALID_FLAG 0xFE
#define NORCOW_VALID_FLAG_LEN 1
#define NORCOW_DATA_OPT_SIZE (FLASH_BLOCK_SIZE - NORCOW_VALID_FLAG_LEN)
#define NORCOW_MAX_PREFIX_LEN (FLASH_BLOCK_SIZE + NORCOW_VALID_FLAG_LEN)

static flash_block_t norcow_write_buffer = {0};
static uint16_t norcow_write_buffer_filled = 0;
static uint16_t norcow_write_buffer_filled_data = 0;
static int32_t norcow_write_buffer_key = -1;

/*
 * Writes data to given sector, starting from offset
 */
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

/*
 * Reads one item starting from offset
 */
static secbool read_item(uint8_t sector, uint32_t offset, uint16_t *key,
                         const void **val, uint16_t *len, uint32_t *pos) {
  *pos = offset;

  const void *l = norcow_ptr(sector, *pos, NORCOW_LEN_LEN);
  if (l == NULL) return secfalse;
  memcpy(len, l, sizeof(uint16_t));

  *pos += NORCOW_LEN_LEN;
  const void *k = norcow_ptr(sector, *pos, NORCOW_KEY_LEN);
  if (k == NULL) {
    return secfalse;
  }

  if (*len <= NORCOW_SMALL_ITEM_SIZE) {
    memcpy(key, k, sizeof(uint16_t));
    if (*key == NORCOW_KEY_FREE) {
      return secfalse;
    }
    *pos += NORCOW_KEY_LEN;
  } else {
    *pos += (NORCOW_KEY_LEN + NORCOW_SMALL_ITEM_SIZE);

    const void *flg = norcow_ptr(sector, *pos, NORCOW_VALID_FLAG_LEN);
    if (flg == NULL) {
      return secfalse;
    }

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

  *val = norcow_ptr(sector, *pos, *len);
  if (*val == NULL) return secfalse;
  *pos = FLASH_ALIGN(*pos + *len);
  return sectrue;
}

void norcow_delete_head(const flash_area_t *area, uint32_t len,
                        uint32_t *val_offset) {
  ensure(flash_unlock_write(), NULL);
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
  ensure(flash_lock_write(), NULL);
}

static secbool flash_area_write_bytes(const flash_area_t *area, uint32_t offset,
                                      uint16_t dest_len, const void *val,
                                      uint16_t len) {
  (void)area;
  (void)offset;
  (void)dest_len;
  (void)val;
  (void)len;
  return secfalse;
}

secbool norcow_next_counter(uint16_t key, uint32_t *count) {
  uint16_t len = 0;
  const uint32_t *val_stored = NULL;
  if (sectrue != norcow_get(key, (const void **)&val_stored, &len)) {
    *count = 0;
    return norcow_set_counter(key, 0);
  }

  if (len != sizeof(uint32_t)) {
    return secfalse;
  }

  *count = *val_stored + 1;
  if (*count < *val_stored) {
    // Value overflow.
    return secfalse;
  }

  return norcow_set_counter(key, *count);
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

  if (allocated_len <= NORCOW_SMALL_ITEM_SIZE) {
    // small items are not updated in place
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

  ensure(flash_lock_write(), NULL);
  return sectrue;
}
