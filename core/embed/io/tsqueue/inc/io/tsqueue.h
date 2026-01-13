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

#ifndef TREZORHAL_TSQUEUE_H
#define TREZORHAL_TSQUEUE_H

#include <trezor_types.h>

typedef struct {
  uint8_t *buffer;  // Pointer to the data buffer
  uint16_t len;     // Length of data in the buffer
  int32_t id;       // ID of the entry
  bool used;        // Used flag
  bool aborted;     // Aborted flag
} tsqueue_entry_t;

typedef struct {
  tsqueue_entry_t *entries;  // Array of queue entries
  uint16_t rix;              // Read index
  uint16_t wix;              // Write index
  uint16_t qlen;             // Queue length
  uint16_t size;             // Size of each buffer
  int32_t next_id;           // ID of the next item
} tsqueue_t;

// Initialize the queue
void tsqueue_init(tsqueue_t *queue, tsqueue_entry_t *entries,
                  uint8_t *buffer_mem, uint16_t size, uint16_t qlen);

void tsqueue_reset(tsqueue_t *queue);

// Insert data into the queue
bool tsqueue_enqueue(tsqueue_t *queue, const uint8_t *data, uint16_t len,
                     int32_t *id);

// Read data from the queue
bool tsqueue_dequeue(tsqueue_t *queue, uint8_t *data, uint16_t max_len,
                     uint16_t *len, int32_t *id);

// Checks if the queue is full
bool tsqueue_full(tsqueue_t *queue);

// Checks if the queue is empty
bool tsqueue_empty(tsqueue_t *queue);

// Aborts item in the queue
// The space in the queue is not freed until the item is attempted to be read
bool tsqueue_abort(tsqueue_t *queue, int32_t id, uint8_t *data,
                   uint16_t max_len, uint16_t *len);

#endif
