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

#include <stdbool.h>
#include "flash_common.h"

#define COUNTER_TAIL_WORDS 0
// Small items are encoded more efficiently.
#define NORCOW_SMALL_ITEM_SIZE \
  (FLASH_BLOCK_SIZE - NORCOW_LEN_LEN - NORCOW_KEY_LEN)
#define NORCOW_VALID_FLAG 0xFF
#define NORCOW_VALID_FLAG_LEN 1
#define NORCOW_DATA_OPT_SIZE (FLASH_BLOCK_SIZE - NORCOW_VALID_FLAG_LEN)
#define NORCOW_MAX_PREFIX_LEN (FLASH_BLOCK_SIZE + NORCOW_VALID_FLAG_LEN)

/**
 * Blockwise NORCOW storage.
 *
 * The items can have two different formats:
 *
 * 1. Small items
 * Small items are stored in one block, the first two bytes are the key, the
 * next two bytes are the length of the value, followed by the value itself.
 * This format is used for items with length <= NORCOW_SMALL_ITEM_SIZE.
 *
 * 2. Large items
 * Large items are stored in multiple blocks, the first block contains the key
 * and the length of the value.
 * Next blocks contain the value itself. If the last value block is not full,
 * it includes the valid flag NORCOW_VALID_FLAG. Otherwise the valid flag is
 * stored in the next block separately.
 * This format is used for items with length > NORCOW_SMALL_ITEM_SIZE.
 *
 *
 * For both formats, the remaining space in the blocks is padded with 0xFF.
 */

// Buffer for update bytes function, used to avoid writing partial blocks
static flash_block_t norcow_write_buffer = {0};
// Tracks how much data is in the buffer, not yet flashed
static uint16_t norcow_write_buffer_filled = 0;
// Key of the item being updated, -1 if no update is in progress
static int32_t norcow_write_buffer_key = -1;

/*
 * Writes data to given sector, starting from offset
 */
static secbool write_item(uint8_t sector, uint32_t offset, uint16_t key,
                          const uint8_t *data, uint16_t len, uint32_t *pos) {
  if (sector >= NORCOW_SECTOR_COUNT) {
    return secfalse;
  }

  flash_block_t block = {((uint32_t)len << 16) | key};
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
    if (offset + FLASH_ALIGN(NORCOW_MAX_PREFIX_LEN + len) >
        NORCOW_SECTOR_SIZE) {
      return secfalse;
    }

    ensure(flash_unlock_write(), NULL);

    // write len
    ensure(flash_area_write_block(&STORAGE_AREAS[sector], offset, block), NULL);
    offset += FLASH_BLOCK_SIZE;

    *pos = FLASH_ALIGN(offset + NORCOW_VALID_FLAG_LEN + len);
    if (data != NULL) {
      // write all blocks except the last one
      while ((uint32_t)(len + NORCOW_VALID_FLAG_LEN) > FLASH_BLOCK_SIZE) {
        memcpy(block, data, FLASH_BLOCK_SIZE);
        ensure(flash_area_write_block(&STORAGE_AREAS[sector], offset, block),
               NULL);
        offset += FLASH_BLOCK_SIZE;
        data += FLASH_BLOCK_SIZE;
        len -= FLASH_BLOCK_SIZE;
      }
      // write the last block
      memset(block, 0xFF, sizeof(block));
      memcpy(block, data, len);
      ((uint8_t *)block)[len] = NORCOW_VALID_FLAG;
      ensure(flash_area_write_block(&STORAGE_AREAS[sector], offset, block),
             NULL);
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

  const void *k = norcow_ptr(sector, *pos, NORCOW_KEY_LEN);
  if (k == NULL) {
    return secfalse;
  }
  *pos += NORCOW_KEY_LEN;

  const void *l = norcow_ptr(sector, *pos, NORCOW_LEN_LEN);
  if (l == NULL) return secfalse;
  memcpy(len, l, sizeof(uint16_t));

  if (*len <= NORCOW_SMALL_ITEM_SIZE) {
    memcpy(key, k, sizeof(uint16_t));
    if (*key == NORCOW_KEY_FREE) {
      return secfalse;
    }
    *pos += NORCOW_LEN_LEN;
  } else {
    *pos = offset + FLASH_BLOCK_SIZE;

    uint32_t flg_pos = *pos + *len;

    const void *flg = norcow_ptr(sector, flg_pos, NORCOW_VALID_FLAG_LEN);
    if (flg == NULL) {
      return secfalse;
    }

    if (*((const uint8_t *)flg) != NORCOW_VALID_FLAG) {
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
  if (*len <= NORCOW_SMALL_ITEM_SIZE) {
    *pos = FLASH_ALIGN(*pos + *len);
  } else {
    *pos = FLASH_ALIGN(*pos + *len + NORCOW_VALID_FLAG_LEN);
  }
  return sectrue;
}

void norcow_delete_item(const flash_area_t *area, uint32_t len,
                        uint32_t val_offset) {
  uint32_t end;

  // Move to the beginning of the block.
  if (len <= NORCOW_SMALL_ITEM_SIZE) {
    // Will delete the entire small item, setting the length to 0
    end = val_offset + NORCOW_SMALL_ITEM_SIZE;
    val_offset -= NORCOW_LEN_LEN + NORCOW_KEY_LEN;
  } else {
    end = val_offset + len + NORCOW_VALID_FLAG_LEN;
  }

  // Delete the item head + data.
  ensure(flash_unlock_write(), NULL);
  flash_block_t block = {0};
  while (val_offset < end) {
    ensure(flash_area_write_block(area, val_offset, block), NULL);
    val_offset += FLASH_BLOCK_SIZE;
  }

  ensure(flash_lock_write(), NULL);
}

static secbool flash_area_write_bytes(const flash_area_t *area, uint32_t offset,
                                      uint16_t dest_len, const void *val,
                                      uint16_t len) {
  uint8_t *ptr = (uint8_t *)flash_area_get_address(area, offset, dest_len);

  if (val == NULL || ptr == NULL || dest_len != len) {
    return secfalse;
  }

  return memcmp(val, ptr, len) == 0 ? sectrue : secfalse;
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
 * Update the value of the given key. The value is updated sequentially,
 * starting from position 0, caller needs to ensure that all bytes are updated
 * by calling this function enough times.
 *
 * The new value is flashed by blocks, if the data
 * passed here do not fill the block it is stored until next call in buffer.
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

  uint32_t sector_offset =
      (const uint8_t *)ptr -
      (const uint8_t *)norcow_ptr(norcow_write_sector, 0, NORCOW_SECTOR_SIZE);

  const flash_area_t *area = &STORAGE_AREAS[norcow_write_sector];

  if (norcow_write_buffer_key != key && norcow_write_buffer_key != -1) {
    // some other update bytes is in process, abort
    return secfalse;
  }

  if (norcow_write_buffer_key == -1) {
    memset(norcow_write_buffer, 0xFF, sizeof(norcow_write_buffer));
    norcow_write_buffer_key = key;
    norcow_write_buffer_filled = 0;
    norcow_write_buffer_flashed = 0;
  }

  if (norcow_write_buffer_flashed + norcow_write_buffer_filled + len >
      allocated_len) {
    return secfalse;
  }

  uint16_t tmp_len = len;
  uint16_t flash_offset = sector_offset + norcow_write_buffer_flashed;

  ensure(flash_unlock_write(), NULL);
  while (tmp_len > 0) {
    uint16_t buffer_space = FLASH_BLOCK_SIZE - norcow_write_buffer_filled;
    uint16_t data_to_copy = (tmp_len > buffer_space ? buffer_space : tmp_len);
    memcpy(&((uint8_t *)norcow_write_buffer)[norcow_write_buffer_filled], data,
           data_to_copy);
    data += data_to_copy;
    norcow_write_buffer_filled += data_to_copy;
    tmp_len -= data_to_copy;

    bool all_data_received = (norcow_write_buffer_filled +
                              norcow_write_buffer_flashed) == allocated_len;
    bool block_full = norcow_write_buffer_filled == FLASH_BLOCK_SIZE;

    if (block_full || all_data_received) {
      if (!block_full) {
        // all data has been received, add valid flag to last block
        ((uint8_t *)norcow_write_buffer)[norcow_write_buffer_filled] =
            NORCOW_VALID_FLAG;
      }

      ensure(flash_area_write_block(area, flash_offset, norcow_write_buffer),
             NULL);
      flash_offset += FLASH_BLOCK_SIZE;

      if (block_full && all_data_received) {
        // last block of data couldn't fit the valid flag, write it in next
        // block
        memset(norcow_write_buffer, 0xFF, sizeof(norcow_write_buffer));
        ((uint8_t *)norcow_write_buffer)[0] = NORCOW_VALID_FLAG;
        ensure(flash_area_write_block(area, flash_offset, norcow_write_buffer),
               NULL);
        flash_offset += FLASH_BLOCK_SIZE;
      }

      norcow_write_buffer_filled = 0;
      norcow_write_buffer_flashed += FLASH_BLOCK_SIZE;
      memset(norcow_write_buffer, 0xFF, sizeof(norcow_write_buffer));

      if (all_data_received) {
        norcow_write_buffer_key = -1;
        norcow_write_buffer_flashed = 0;
      }
    }
  }

  ensure(flash_lock_write(), NULL);
  return sectrue;
}
