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

typedef enum {
  TSQUEUE_ENTRY_EMPTY = 0,
  TSQUEUE_ENTRY_ALLOCATED = 1,
  TSQUEUE_ENTRY_FULL = 2,
  TSQUEUE_ENTRY_PROCESSING = 3,
} tsqueue_entry_state_t;

typedef struct {
  uint8_t *buffer;              // Pointer to the data buffer
  tsqueue_entry_state_t state;  // State of the queue entry
  uint16_t len;                 // Length of data in the buffer
  uint32_t id;                  // ID of the entry
  bool aborted;                 // Aborted flag
} tsqueue_entry_t;

typedef struct {
  tsqueue_entry_t *entries;  // Array of queue entries
  int rix;                   // Read index
  int fix;                   // Finalize index
  int pix;                   // Process index
  int wix;                   // Write index
  int qlen;                  // Queue length
  bool overrun;              // Overrun flag
  uint16_t overrun_count;    // Overrun counter
  uint16_t size;             // Size of each buffer
  uint32_t next_id;          // ID of the next item
} tsqueue_t;

// Initialize the queue
void tsqueue_init(tsqueue_t *queue, tsqueue_entry_t *entries,
                  uint8_t *buffer_mem, uint16_t size, int qlen);

void tsqueue_reset(tsqueue_t *queue);

// Insert data into the queue
bool tsqueue_insert(tsqueue_t *queue, const uint8_t *data, uint16_t len,
                    uint32_t *id);

// Allocate an entry in the queue
// Returns a pointer to the allocated buffer
// Fails if some item is already allocated, NULL
// To be used instead of insert function, in conjunction with tsqueue_finalize
uint8_t *tsqueue_allocate(tsqueue_t *queue, uint32_t *id);

// Finalize an allocated entry
bool tsqueue_finalize(tsqueue_t *queue, const uint8_t *buffer, uint16_t len);

// Read data from the queue
bool tsqueue_read(tsqueue_t *queue, uint8_t *data, uint16_t max_len,
                  uint16_t *len);

// Process an entry in the queue
// Returns a pointer to the buffer to be processed
// Fails if some item is already being processed, returns NULL
// To be used in conjunction with tsqueue_process_done
uint8_t *tsqueue_process(tsqueue_t *queue, uint16_t *len);

// Mark processing as done
bool tsqueue_process_done(tsqueue_t *queue, uint8_t *data, uint16_t max_len,
                          uint16_t *len, bool *aborted);

// Checks if the queue is full
bool tsqueue_full(tsqueue_t *queue);

// Aborts item in the queue
// The space in the queue is not freed until the item is attempted to be read
bool tsqueue_abort(tsqueue_t *queue, uint32_t id, uint8_t *data,
                   uint16_t max_len, uint16_t *len);

#endif
