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
#include <util/tsqueue.h>

#define TOUCH_DEBUG_QUEUE_SIZE 8

static uint32_t touch_debug_queue_items[TOUCH_DEBUG_QUEUE_SIZE];
static tsqueue_entry_t touch_debug_queue_entries[TOUCH_DEBUG_QUEUE_SIZE];
static tsqueue_t touch_debug_queue;
static uint32_t touch_debug_state;
static bool touch_debug_state_active;

void touch_debug_init(void) {
  tsqueue_init(&touch_debug_queue, touch_debug_queue_entries,
               (uint8_t*)touch_debug_queue_items, sizeof(uint32_t),
               TOUCH_DEBUG_QUEUE_SIZE);
}

void touch_debug_deinit(void) { tsqueue_reset(&touch_debug_queue); }

void touch_debug_start(uint32_t x, uint32_t y) {
  uint32_t event = TOUCH_START | touch_pack_xy(x, y);

  tsqueue_enqueue(&touch_debug_queue, (uint8_t*)&event, sizeof(event), NULL);
}

void touch_debug_end(uint32_t x, uint32_t y) {
  uint32_t event = TOUCH_END | touch_pack_xy(x, y);

  tsqueue_enqueue(&touch_debug_queue, (uint8_t*)&event, sizeof(event), NULL);
}

void touch_debug_click(uint32_t x, uint32_t y) {
  uint32_t event = TOUCH_START | touch_pack_xy(x, y);

  tsqueue_enqueue(&touch_debug_queue, (uint8_t*)&event, sizeof(event), NULL);

  event = TOUCH_END | touch_pack_xy(x, y);

  tsqueue_enqueue(&touch_debug_queue, (uint8_t*)&event, sizeof(event), NULL);
}

bool touch_debug_active(void) { return touch_debug_state_active; }

uint32_t touch_debug_get_state(void) { return touch_debug_state; }

void touch_debug_next(void) {
  if (tsqueue_empty(&touch_debug_queue)) {
    return;
  }

  uint32_t state = 0;

  tsqueue_dequeue(&touch_debug_queue, (uint8_t*)&state, sizeof(state), NULL,
                  NULL);

  touch_debug_state = state;

  if (TOUCH_END & state) {
    touch_debug_state_active = false;
  } else {
    touch_debug_state_active = true;
  }
}
