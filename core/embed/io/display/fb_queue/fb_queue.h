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
typedef enum {
  // The frame buffer is empty and can be written to
  FB_STATE_EMPTY = 0,
  // The frame buffer pass passed to application
  FB_STATE_PREPARING = 1,
  // The frame buffer was written to and is ready
  // to be copied to the display
  FB_STATE_READY = 2,
  // The frame buffer is currently being copied to
  // the display
  FB_STATE_COPYING = 3,

} frame_buffer_state_t;

typedef struct {
  // Queue entries
  volatile frame_buffer_state_t entry[FRAME_BUFFER_COUNT];
  // Active index
  // (accessed & updated in the context of the interrupt handlers
  int16_t aix;
  // Read index
  // (accessed & updated in the context of the interrupt handlers
  uint8_t rix;
  // Write index
  // (accessed & updated in context of the main thread)
  uint8_t wix;

} frame_buffer_queue_t;

int16_t fb_queue_get_for_copy(volatile frame_buffer_queue_t *queue);

int16_t fb_queue_get_for_write(volatile frame_buffer_queue_t *queue);

int16_t fb_queue_get_for_transfer(volatile frame_buffer_queue_t *queue);

bool fb_queue_set_done(volatile frame_buffer_queue_t *queue);

bool fb_queue_set_switched(volatile frame_buffer_queue_t *queue);

bool fb_queue_set_ready_for_transfer(volatile frame_buffer_queue_t *queue);

void fb_queue_reset(volatile frame_buffer_queue_t *queue);

bool fb_queue_is_processed(volatile frame_buffer_queue_t *queue);
