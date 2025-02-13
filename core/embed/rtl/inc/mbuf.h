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

typedef struct {
  uint8_t* ptr;
  size_t size;
  size_t offset;
} mbuf_t;

static inline mbuf_t mbuf_init(uint8_t* ptr, size_t size) {
  mbuf_t mbuf = {
      .ptr = ptr,
      .size = size,
      .offset = 0,
      .error = false,
  };
  return mbuf;
}

static inline size_t mbuf_len(const mbuf_t* mbuf) { return mbuf->offset; }

static inline size_t mbuf_remaining(const mbuf_t* mbuf) {
  return mbuf->size - mbuf->offset;
}

static inline bool mbuf_error(const mbuf_t* mbuf) { return mbuf->error; }

static inline bool mbuf_ok(const mbuf_t* mbuf) { return !mbuf->error; }

static inline bool mbuf_skip(mbuf_t* mbuf, size_t len) {
  if (mbuf->error || mbuf->offset + len > mbuf->size) {
    mbuf->error = true;
    return false;
  }
  mbuf->offset += len;
  return true;
}

static inline bool mbuf_write(mbuf_t* mbuf, const void* data, size_t len) {
  if (mbuf->error || mbuf->offset + len > mbuf->size) {
    mbuf->error = true;
    return false;
  }
  memcpy(mbuf->ptr + mbuf->offset, data, len);
  mbuf->offset += len;
  return true;
}

static inline bool mbuf_read(mbuf_t* mbuf, void* data, size_t len) {
  if (mbuf->error || mbuf->offset + len > mbuf->size) {
    return false;
  }
  memcpy(data, mbuf->ptr + mbuf->offset, len);
  mbuf->offset += len;
  return true;
}

static inline bool mbuf_set_u8(mbuf_t* mbuf, size_t offset, uint8_t value) {
  if (mbuf->error || offset >= mbuf->size) {
    mbuf->error = true;
    return false;
  }
  mbuf->ptr[offset] = value;
  return true;
}

static inline bool mbuf_write_u8(mbuf_t* mbuf, uint8_t value) {
  if (mbuf->error || mbuf->offset >= mbuf->size) {
    mbuf->error = true;
    return false;
  }
  mbuf->ptr[mbuf->offset++] = value;
  return true;
}

static inline bool mbuf_write_u16le(mbuf_t* mbuf, uint16_t value) {
  if (mbuf->error || mbuf->offset + 2 > mbuf->size) {
    mbuf->error = true;
    return false;
  }
  mbuf->ptr[mbuf->offset++] = value & 0xFF;
  mbuf->ptr[mbuf->offset++] = value >> 8;
  return true;
}

static inline bool mbuf_write_u16be(mbuf_t* mbuf, uint16_t value) {
  if (mbuf->error || mbuf->offset + 2 > mbuf->size) {
    mbuf->error = true;
    return false;
  }
  mbuf->ptr[mbuf->offset++] = value >> 8;
  mbuf->ptr[mbuf->offset++] = value & 0xFF;
  return true;
}

static inline bool mbuf_read_u8(mbuf_t* mbuf, uint8_t* value) {
  if (mbuf->error || mbuf->offset >= mbuf->size) {
    return false;
  }
  *value = mbuf->ptr[mbuf->offset++];
  return true;
}

static inline bool mbuf_read_u16le(mbuf_t* mbuf, uint16_t* value) {
  if (mbuf->error || mbuf->offset + 2 > mbuf->size) {
    return false;
  }
  *value = mbuf->ptr[mbuf->offset++];
  *value |= mbuf->ptr[mbuf->offset++] << 8;
  return true;
}
