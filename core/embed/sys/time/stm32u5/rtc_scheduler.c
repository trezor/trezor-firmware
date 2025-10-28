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

#include "rtc_scheduler.h"

bool rtc_schedule_push(rtc_wakeup_schedule_t *sch, rtc_wakeup_event_t *event) {
  uint8_t new_head = (sch->head + 1) % MAX_SCHEDULE_LEN;
  if (new_head == sch->tail) {
    // Queue is full
    return false;
  }

  // Sweep the queue backwards and find the correct position for the new event
  uint8_t idx = sch->head;

  while (true) {
    if (idx == sch->tail) {
      // Reached the beginning of the queue
      sch->events[idx] = *event;
      break;
    }

    uint8_t prev_idx = (idx + MAX_SCHEDULE_LEN - 1) % MAX_SCHEDULE_LEN;

    if (sch->events[prev_idx].timestamp >= event->timestamp) {
      // Move the already present event forward
      sch->events[idx] = sch->events[prev_idx];
    } else {
      sch->events[idx] = *event;
      break;
    }

    idx = prev_idx;
  }

  sch->head = new_head;

  return true;
}

bool rtc_schedule_pop(rtc_wakeup_schedule_t *sch, rtc_wakeup_event_t *event) {
  if (sch->head == sch->tail) {
    // Queue is empty
    return false;
  }

  *event = sch->events[sch->tail];
  sch->tail = (sch->tail + 1) % MAX_SCHEDULE_LEN;

  return true;
}

bool rtc_schedule_remove(rtc_wakeup_schedule_t *sch, uint32_t event_id) {
  if (sch->head == sch->tail) {
    return false;
  }

  // Sweep the queue, if you hit the id, remove the event and shift
  // remaining items backward
  uint8_t idx = sch->tail;
  uint8_t next_idx;
  uint8_t item_found = false;

  while (idx != sch->head) {
    if (sch->events[idx].id == event_id) {
      item_found = true;
    }

    next_idx = (idx + 1) % MAX_SCHEDULE_LEN;

    if (item_found) {
      sch->events[idx] = sch->events[next_idx];
    }

    idx = next_idx;
  }

  if (item_found) {
    sch->head = (sch->head + MAX_SCHEDULE_LEN - 1) % MAX_SCHEDULE_LEN;
    return true;
  } else {
    return false;
  }
}
