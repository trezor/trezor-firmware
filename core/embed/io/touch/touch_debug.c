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

#include "touch_debug.h"

#include <io/touch.h>
#include <rtl/logging.h>
#include <string.h>
#include <util/tsqueue.h>

#define TOUCH_DEBUG_QUEUE_SIZE 8

LOG_DECLARE(touch_debug)

typedef struct {
  uint32_t queue_items[TOUCH_DEBUG_QUEUE_SIZE];
  tsqueue_entry_t queue_entries[TOUCH_DEBUG_QUEUE_SIZE];
  tsqueue_t queue;
  uint32_t state;
  bool state_active;
} touch_debug_t;

static touch_debug_t touch_debug;

void touch_debug_init(void) {
  memset(&touch_debug, 0, sizeof(touch_debug_t));
  tsqueue_init(&touch_debug.queue, touch_debug.queue_entries,
               (uint8_t*)touch_debug.queue_items, sizeof(uint32_t),
               TOUCH_DEBUG_QUEUE_SIZE);
}

void touch_debug_deinit(void) {
  memset(&touch_debug, 0, sizeof(touch_debug_t));
}

void touch_debug_start(uint32_t x, uint32_t y) {
  uint32_t event = TOUCH_START | touch_pack_xy(x, y);

  if (!tsqueue_enqueue(&touch_debug.queue, (uint8_t*)&event, sizeof(event),
                       NULL)) {
    LOG_WARN("touch debug queue full");
  }
}

void touch_debug_end(uint32_t x, uint32_t y) {
  uint32_t event = TOUCH_END | touch_pack_xy(x, y);

  if (!tsqueue_enqueue(&touch_debug.queue, (uint8_t*)&event, sizeof(event),
                       NULL)) {
    LOG_WARN("touch debug queue full");
  }
}

void touch_debug_click(uint32_t x, uint32_t y) {
  uint32_t event = TOUCH_START | touch_pack_xy(x, y);

  if (!tsqueue_enqueue(&touch_debug.queue, (uint8_t*)&event, sizeof(event),
                       NULL)) {
    LOG_WARN("touch debug queue full");
  }

  event = TOUCH_END | touch_pack_xy(x, y);

  if (!tsqueue_enqueue(&touch_debug.queue, (uint8_t*)&event, sizeof(event),
                       NULL)) {
    LOG_WARN("touch debug queue full");
  }
}

bool touch_debug_active(void) { return touch_debug.state_active; }

uint32_t touch_debug_get_state(void) { return touch_debug.state; }

void touch_debug_next(void) {
  uint32_t state = 0;

  if (!tsqueue_dequeue(&touch_debug.queue, (uint8_t*)&state, sizeof(state),
                       NULL, NULL)) {
    return;
  }

  touch_debug.state = state;

  if (TOUCH_END & state) {
    touch_debug.state_active = false;
  } else {
    touch_debug.state_active = true;
  }
}
