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

// Number of frame buffers used (1 or 2)
// If 1 buffer is selected, some animations may not
// be so smooth but the memory usage is lower.
#define FRAME_BUFFER_COUNT 2

// Each frame buffer can be in one of the following states:
typedef struct {
  int16_t index;
} fb_queue_entry;

typedef struct {
  // Queue entries
  fb_queue_entry entries[FRAME_BUFFER_COUNT];

  // Read index
  // (accessed & updated in the context of the interrupt handlers
  uint8_t rix;
  // Write index
  // (accessed & updated in context of the main thread)
  uint8_t wix;

  // Flag indicating that the head of the queue has been peaked
  bool peaked;

} fb_queue_t;

// Initializes the queue and make it empty
// Clear peeked flag
void fb_queue_reset(fb_queue_t* queue);

// Inserts a new element to the tail of the queue
bool fb_queue_put(fb_queue_t* queue, int16_t index);

// Removes an element from the queue head, returns -1 if the queue is empty
// Clear peeked flag
int16_t fb_queue_take(fb_queue_t* queue);
// Returns true if the queue is empty
bool fb_queue_empty(fb_queue_t* queue);

// Waits until the queue is not empty
void fb_queue_wait(fb_queue_t* queue);

// Returns the head of the queue (or -1 if the queue is empty)
// Set peeked flag if the queue is not empty
int16_t fb_queue_peek(fb_queue_t* queue);

// Return if the head was already peeked
bool fb_queue_peeked(fb_queue_t* queue);
