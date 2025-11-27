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

#include <trezor_rtl.h>

#include <util/tsqueue.h>

#include "button_debug.h"

#define BUTTON_DEBUG_QUEUE_SIZE 8

static uint32_t button_debug_queue_items[BUTTON_DEBUG_QUEUE_SIZE];
static tsqueue_entry_t button_debug_queue_entries[BUTTON_DEBUG_QUEUE_SIZE];
static tsqueue_t button_debug_queue;
// static uint32_t button_debug_state = 0;

void button_debug_init(void) {
  tsqueue_init(&button_debug_queue, button_debug_queue_entries,
               (uint8_t*)button_debug_queue_items, sizeof(button_event_t),
               BUTTON_DEBUG_QUEUE_SIZE);
}

void button_debug_deinit(void) { tsqueue_reset(&button_debug_queue); }

void button_debug_click(button_t button) {
  button_event_t event = {0};
  event.button = button;
  event.event_type = BTN_EVENT_DOWN;
  tsqueue_enqueue(&button_debug_queue, (uint8_t*)&event, sizeof(event), NULL);

  event.event_type = BTN_EVENT_UP;
  tsqueue_enqueue(&button_debug_queue, (uint8_t*)&event, sizeof(event), NULL);
}

void button_debug_press(button_t button) {
  button_event_t event = {0};
  event.button = button;
  event.event_type = BTN_EVENT_DOWN;
  tsqueue_enqueue(&button_debug_queue, (uint8_t*)&event, sizeof(event), NULL);
}

void button_debug_release(button_t button) {
  button_event_t event = {0};
  event.button = button;
  event.event_type = BTN_EVENT_UP;
  tsqueue_enqueue(&button_debug_queue, (uint8_t*)&event, sizeof(event), NULL);
}

bool button_debug_peek(button_event_t* event) {
  if (tsqueue_empty(&button_debug_queue)) {
    return false;
  }

  return tsqueue_peek(&button_debug_queue, (uint8_t*)event, sizeof(*event),
                      NULL, NULL);
}

bool button_debug_poll(button_event_t* event) {
  if (tsqueue_empty(&button_debug_queue)) {
    return false;
  }

  return tsqueue_dequeue(&button_debug_queue, (uint8_t*)event, sizeof(*event),
                         NULL, NULL);
}
