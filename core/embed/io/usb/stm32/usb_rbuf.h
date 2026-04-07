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

#pragma once

#include <trezor_types.h>

/** Ring buffer structure */
typedef struct {
  uint8_t *buf;
  size_t cap;
  size_t used;
  uint8_t *rptr;
  uint8_t *wptr;
} usb_rbuf_t;

/**
 * @brief Initialize the ring buffer.
 *
 * The buffer memory must be provided by the caller and must remain valid
 * for the lifetime of the ring buffer.
 *
 * @param b Pointer to the ring buffer structure to initialize.
 * @param buf Pointer to the buffer memory.
 * @param buf_size Size of the buffer memory in bytes.
 */
void usb_rbuf_init(usb_rbuf_t *b, uint8_t *buf, size_t buf_size);

/**
 * @brief Reset the ring buffer to an empty state.
 *
 * This function clears the contents of the ring buffer and resets
 * the read and write pointers to the beginning of the buffer.
 *
 * @param b Pointer to the ring buffer structure to reset.
 */
void usb_rbuf_reset(usb_rbuf_t *b);

/**
 * @brief Get the number of bytes used in the ring buffer.
 *
 * @param b Pointer to the ring buffer structure.
 * @return Number of bytes used in the ring buffer.
 */
size_t usb_rbuf_used_bytes(usb_rbuf_t *b);

/**
 * @brief Get the number of unused bytes in the ring buffer.
 *
 * @param b Pointer to the ring buffer structure.
 * @return Number of unused bytes in the ring buffer.
 */
size_t usb_rbuf_unused_bytes(usb_rbuf_t *b);

/**
 * @brief Check if the ring buffer is empty.
 *
 * @param b Pointer to the ring buffer structure.
 * @return true if the ring buffer is empty, false otherwise.
 */
bool usb_rbuf_is_empty(usb_rbuf_t *b);

/**
 * @brief Check if the ring buffer is full.
 *
 * @param b Pointer to the ring buffer structure.
 * @return true if the ring buffer is full, false otherwise.
 */
bool usb_rbuf_is_full(usb_rbuf_t *b);

/**
 * @brief Read data from the ring buffer.
 *
 * This function reads up to `buf_size` bytes from the ring buffer into
 * the provided `buf`. The actual number of bytes read is returned.
 *
 * @param b Pointer to the ring buffer structure.
 * @param buf Pointer to the buffer where read data will be stored.
 * @param buf_size Size of the buffer in bytes.
 * @return Number of bytes actually read from the ring buffer.
 */
size_t usb_rbuf_read(usb_rbuf_t *b, uint8_t *buf, size_t buf_size);

/**
 * @brief Write data to the ring buffer.
 *
 * This function writes up to `data_size` bytes from the provided `data`
 * buffer into the ring buffer. The actual number of bytes written is returned.
 *
 * @param b Pointer to the ring buffer structure.
 * @param data Pointer to the data to be written to the ring buffer.
 * @param data_size Size of the data in bytes.
 * @return Number of bytes actually written to the ring buffer.
 */
size_t usb_rbuf_write(usb_rbuf_t *b, const uint8_t *data, size_t data_size);
