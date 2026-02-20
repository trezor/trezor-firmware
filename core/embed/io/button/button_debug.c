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

#include "button_debug.h"

#include <trezor_rtl.h>

#include <io/tsqueue.h>
#include <sys/logging.h>

LOG_DECLARE(button_debug)

#define BUTTON_DEBUG_QUEUE_SIZE 8

typedef struct {
  button_event_t queue_items[BUTTON_DEBUG_QUEUE_SIZE];
  tsqueue_entry_t queue_entries[BUTTON_DEBUG_QUEUE_SIZE];
  tsqueue_t queue;
  uint32_t state;
} button_debug_t;

static button_debug_t button_debug;

void button_debug_init(void) {
  memset(&button_debug, 0, sizeof(button_debug_t));
  tsqueue_init(&button_debug.queue, button_debug.queue_entries,
               (uint8_t*)button_debug.queue_items, sizeof(button_event_t),
               BUTTON_DEBUG_QUEUE_SIZE);
}

void button_debug_deinit(void) {
  memset(&button_debug, 0, sizeof(button_debug_t));
}

void button_debug_click(button_t button) {
  button_debug_press(button);
  button_debug_release(button);
}

void button_debug_press(button_t button) {
  button_event_t event = {0};
  event.button = button;
  event.event_type = BTN_EVENT_DOWN;
  if (!tsqueue_enqueue(&button_debug.queue, (uint8_t*)&event, sizeof(event),
                       NULL)) {
    LOG_WARN("button debug queue full");
  }
}

void button_debug_release(button_t button) {
  button_event_t event = {0};
  event.button = button;
  event.event_type = BTN_EVENT_UP;
  if (!tsqueue_enqueue(&button_debug.queue, (uint8_t*)&event, sizeof(event),
                       NULL)) {
    LOG_WARN("button debug queue full");
  }
}

void button_debug_next(void) {
  button_event_t event = {0};

  if (!tsqueue_dequeue(&button_debug.queue, (uint8_t*)&event, sizeof(event),
                       NULL, NULL)) {
    return;
  }

  if (event.event_type == BTN_EVENT_DOWN) {
    button_debug.state |= (1 << event.button);
  }
  if (event.event_type == BTN_EVENT_UP) {
    button_debug.state &= ~(1 << event.button);
  }
}

uint32_t button_debug_get_state(void) { return button_debug.state; }
