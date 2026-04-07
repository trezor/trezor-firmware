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

#ifdef KERNEL_MODE

#include <sys/irq.h>
#include <sys/rtc.h>
#include <sys/rtc_scheduler.h>

typedef struct {
  uint32_t timestamp;
  uint32_t id;
  rtc_wakeup_callback_t callback;
  void *callback_context;
} rtc_wakeup_event_t;

typedef struct {
  uint8_t head;
  uint8_t tail;
  rtc_wakeup_event_t events[MAX_SCHEDULE_LEN];
} rtc_wakeup_schedule_t;

uint32_t rtc_event_id_counter = 0;

rtc_wakeup_schedule_t g_rtc_wakeup_schedule = {
    .head = 0,
    .tail = 0,
};

static bool rtc_scheduler_push(rtc_wakeup_event_t *event);
static bool rtc_scheduler_pop(rtc_wakeup_event_t *event);
static bool rtc_scheduler_remove(uint32_t id);
rtc_wakeup_event_t *rtc_scheduler_get_head(void);

void rtc_scheduler_callback(void *context) {
  // Call events that exceeds the current timestamp
  while (true) {
    rtc_wakeup_event_t *next_event = rtc_scheduler_get_head();
    if (next_event == NULL) {
      break;
    }

    uint32_t current_timestamp;
    rtc_get_timestamp(&current_timestamp);
    if (next_event->timestamp > current_timestamp) {
      break;
    }

    // Call the event callback
    if (next_event->callback != NULL) {
      next_event->callback(next_event->callback_context);
    }

    // Remove the event from the schedule
    rtc_scheduler_pop(next_event);
  }

  // Start the next event if any
  rtc_wakeup_event_t *next_event = rtc_scheduler_get_head();
  if (next_event != NULL) {
    rtc_wakeup_timer_start(next_event->timestamp, &rtc_scheduler_callback,
                           next_event);
  }
}

bool rtc_schedule_wakeup_event(uint32_t wakeup_timestamp,
                               rtc_wakeup_callback_t callback, void *context,
                               rtc_event_id_t *event_id) {
  irq_key_t irq_key = irq_lock();

  // Increment event ID
  rtc_event_id_counter++;
  if (rtc_event_id_counter == 0) {
    rtc_event_id_counter = 1;  // Avoid zero ID
  }

  rtc_wakeup_event_t new_event = {
      .timestamp = wakeup_timestamp,
      .id = rtc_event_id_counter,
      .callback = callback,
      .callback_context = context,
  };

  // Push new event to the schedule
  if (!rtc_scheduler_push(&new_event)) {
    irq_unlock(irq_key);
    return false;
  }

  rtc_wakeup_timer_stop();

  rtc_wakeup_event_t *head = rtc_scheduler_get_head();
  if (head == NULL) {
    irq_unlock(irq_key);
    return false;
  }

  // Return new event ID
  if (event_id != NULL) {
    *event_id = new_event.id;
  }

  rtc_wakeup_timer_start(head->timestamp, &rtc_scheduler_callback, NULL);

  irq_unlock(irq_key);

  return true;
}

bool rtc_cancel_wakeup_event(uint32_t event_id) {
  irq_key_t irq_key = irq_lock();

  rtc_wakeup_timer_stop();

  rtc_scheduler_remove(event_id);

  rtc_wakeup_event_t *head = rtc_scheduler_get_head();
  if (head == NULL) {
    irq_unlock(irq_key);
    return false;
  }

  rtc_wakeup_timer_start(head->timestamp, &rtc_scheduler_callback, head);
  irq_unlock(irq_key);

  return true;
}

static bool rtc_scheduler_push(rtc_wakeup_event_t *event) {
  rtc_wakeup_schedule_t *sch = &g_rtc_wakeup_schedule;

  uint8_t new_tail = (sch->tail + 1) % MAX_SCHEDULE_LEN;
  if (new_tail == sch->head) {
    // Queue is full
    return false;
  }

  // Sweep the queue backwards and find the correct position for the new event
  uint8_t idx = sch->tail;

  while (idx != sch->head) {
    uint8_t prev_idx = (idx + MAX_SCHEDULE_LEN - 1) % MAX_SCHEDULE_LEN;

    if (sch->events[prev_idx].timestamp <= event->timestamp) {
      break;
    }

    sch->events[idx] = sch->events[prev_idx];
    idx = prev_idx;
  }

  // Insert the new event
  sch->events[idx] = *event;

  sch->tail = new_tail;

  return true;
}

static bool rtc_scheduler_pop(rtc_wakeup_event_t *event) {
  rtc_wakeup_schedule_t *sch = &g_rtc_wakeup_schedule;

  if (sch->head == sch->tail) {
    // Queue is empty
    return false;
  }

  *event = sch->events[sch->head];
  sch->head = (sch->head + 1) % MAX_SCHEDULE_LEN;

  return true;
}

static bool rtc_scheduler_remove(uint32_t id) {
  rtc_wakeup_schedule_t *sch = &g_rtc_wakeup_schedule;

  if (sch->head == sch->tail) {
    return false;
  }

  // Sweep the queue, if you hit the id, remove the event and shift
  // remaining items backward
  uint8_t idx = sch->head;
  uint8_t next_idx;
  uint8_t item_found = false;

  while (idx != sch->tail) {
    if (sch->events[idx].id == id) {
      item_found = true;
    }

    next_idx = (idx + 1) % MAX_SCHEDULE_LEN;

    if (item_found) {
      sch->events[idx] = sch->events[next_idx];
    }

    idx = next_idx;
  }

  if (item_found) {
    sch->tail = (sch->tail + MAX_SCHEDULE_LEN - 1) % MAX_SCHEDULE_LEN;
    return true;
  } else {
    return false;
  }

  return true;
}

rtc_wakeup_event_t *rtc_scheduler_get_head(void) {
  rtc_wakeup_schedule_t *sch = &g_rtc_wakeup_schedule;

  if (sch->head == sch->tail) {
    // Queue is empty
    return NULL;
  }

  return &sch->events[sch->head];
}

#endif
