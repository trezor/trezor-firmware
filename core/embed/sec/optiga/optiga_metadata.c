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

/*
 * Serialization of Optiga data object metadata.
 *
 * For metadata description see:
 * https://github.com/Infineon/optiga-trust-m/blob/develop/documents/OPTIGA%E2%84%A2%20Trust%20M%20Solution%20Reference%20Manual.md#metadata-expression
 */

#ifdef SECURE_MODE

#include <trezor_rtl.h>

#include <sec/optiga_commands.h>

#include "memzero.h"

const optiga_metadata_item OPTIGA_META_LCS_OPERATIONAL =
    OPTIGA_META_VALUE(OPTIGA_LCS_OP);
const optiga_metadata_item OPTIGA_META_ACCESS_ALWAYS =
    OPTIGA_META_VALUE(OPTIGA_ACCESS_COND_ALW);
const optiga_metadata_item OPTIGA_META_ACCESS_NEVER =
    OPTIGA_META_VALUE(OPTIGA_ACCESS_COND_NEV);
const optiga_metadata_item OPTIGA_META_KEY_USE_ENC =
    OPTIGA_META_VALUE(OPTIGA_KEY_USAGE_ENC);
const optiga_metadata_item OPTIGA_META_KEY_USE_KEYAGREE =
    OPTIGA_META_VALUE(OPTIGA_KEY_USAGE_KEYAGREE);
const optiga_metadata_item OPTIGA_META_VERSION_DEFAULT = {
    (const uint8_t[]){0x00, 0x00}, 2};

static const struct {
  size_t offset;
  uint8_t tag;
  const optiga_metadata_item *default_value;
} METADATA_OFFSET_TAG_MAP[] = {
    {offsetof(optiga_metadata, lcso), 0xC0, &OPTIGA_META_LCS_OPERATIONAL},
    {offsetof(optiga_metadata, version), 0xC1, &OPTIGA_META_VERSION_DEFAULT},
    {offsetof(optiga_metadata, max_size), 0xC4, NULL},
    {offsetof(optiga_metadata, used_size), 0xC5, NULL},
    {offsetof(optiga_metadata, change), 0xD0, &OPTIGA_META_ACCESS_NEVER},
    {offsetof(optiga_metadata, read), 0xD1, &OPTIGA_META_ACCESS_NEVER},
    {offsetof(optiga_metadata, execute), 0xD3, &OPTIGA_META_ACCESS_NEVER},
    {offsetof(optiga_metadata, meta_update), 0xD8, NULL},
    {offsetof(optiga_metadata, algorithm), 0xE0, NULL},
    {offsetof(optiga_metadata, key_usage), 0xE1, NULL},
    {offsetof(optiga_metadata, data_type), 0xE8, NULL},
    {offsetof(optiga_metadata, reset_type), 0xF0, NULL},
};

static const size_t METADATA_TAG_COUNT =
    sizeof(METADATA_OFFSET_TAG_MAP) / sizeof(METADATA_OFFSET_TAG_MAP[0]);

optiga_result optiga_parse_metadata(const uint8_t *serialized,
                                    size_t serialized_size,
                                    optiga_metadata *metadata) {
  memzero(metadata, sizeof(*metadata));

  if (serialized_size < 2 || serialized[0] != 0x20 ||
      (size_t)(serialized[1] + 2) != serialized_size) {
    return OPTIGA_ERR_PARAM;
  }

  size_t pos = 2;
  while (pos < serialized_size) {
    if (pos + 2 >= serialized_size) {
      return OPTIGA_ERR_PARAM;
    }

    uint8_t len = serialized[pos + 1];
    if (pos + 2 + len > serialized_size) {
      return OPTIGA_ERR_PARAM;
    }

    // Determine metadata type from tag.
    optiga_metadata_item *item = NULL;
    for (size_t i = 0; i < METADATA_TAG_COUNT; ++i) {
      if (METADATA_OFFSET_TAG_MAP[i].tag == serialized[pos]) {
        item = (void *)((char *)metadata + METADATA_OFFSET_TAG_MAP[i].offset);
        break;
      }
    }

    if (item == NULL || item->ptr != NULL) {
      // Invalid tag or multiply defined tag.
      return OPTIGA_ERR_PARAM;
    }

    item->ptr = &serialized[pos + 2];
    item->len = len;
    pos += 2 + len;
  }

  if (pos != serialized_size) {
    return OPTIGA_ERR_PARAM;
  }

  return OPTIGA_SUCCESS;
}

optiga_result optiga_serialize_metadata(const optiga_metadata *metadata,
                                        uint8_t *serialized,
                                        size_t max_serialized,
                                        size_t *serialized_size) {
  *serialized_size = 0;
  if (max_serialized < 2) {
    return OPTIGA_ERR_SIZE;
  }

  serialized[0] = 0x20;  // Metadata constructed TLV-Object tag.
  size_t pos = 2;        // Leave room for length byte.

  for (size_t i = 0; i < METADATA_TAG_COUNT; ++i) {
    optiga_metadata_item *item =
        (void *)((char *)metadata + METADATA_OFFSET_TAG_MAP[i].offset);
    if (item->ptr == NULL) {
      continue;
    }

    if (max_serialized < pos + 2 + item->len) {
      return OPTIGA_ERR_SIZE;
    }

    serialized[pos++] = METADATA_OFFSET_TAG_MAP[i].tag;
    serialized[pos++] = item->len;
    memcpy(&serialized[pos], item->ptr, item->len);
    pos += item->len;
  }

  // Set length byte.
  if (pos - 2 > 256) {
    return OPTIGA_ERR_SIZE;
  }
  serialized[1] = pos - 2;

  *serialized_size = pos;
  return OPTIGA_SUCCESS;
}

// Returns true if all items defined in the expected metadata have the same
// value in the stored metadata, i.e. items that are not defined in the expected
// metadata may have arbitrary value in the stored metadata.
bool optiga_compare_metadata(const optiga_metadata *expected,
                             const optiga_metadata *stored) {
  for (size_t i = 0; i < METADATA_TAG_COUNT; ++i) {
    const optiga_metadata_item *expected_item =
        (void *)((char *)expected + METADATA_OFFSET_TAG_MAP[i].offset);
    if (expected_item->ptr == NULL) {
      // Ignore undefined items.
      continue;
    }

    const optiga_metadata_item *stored_item =
        (void *)((char *)stored + METADATA_OFFSET_TAG_MAP[i].offset);
    if (stored_item->ptr == NULL) {
      if (METADATA_OFFSET_TAG_MAP[i].default_value == NULL) {
        return false;
      }
      stored_item = METADATA_OFFSET_TAG_MAP[i].default_value;
    }

    if (stored_item->len != expected_item->len ||
        memcmp(stored_item->ptr, expected_item->ptr, expected_item->len) != 0) {
      return false;
    }
  }
  return true;
}

#endif  // SECURE_MODE
