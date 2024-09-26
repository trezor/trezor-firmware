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

#include <sys/irq.h>
#include <util/tsqueue.h>

// Initialize the queue
void tsqueue_init(tsqueue_t *queue, tsqueue_entry_t *entries,
                  uint8_t *buffer_mem, uint16_t size, uint16_t qlen) {
  irq_key_t key = irq_lock();
  queue->entries = entries;
  queue->qlen = qlen;
  queue->size = size;

  for (int i = 0; i < qlen; i++) {
    queue->entries[i].buffer = buffer_mem + i * size;
  }

  tsqueue_reset(queue);

  irq_unlock(key);
}

static void tsqueue_entry_reset(tsqueue_entry_t *entry, uint32_t data_size) {
  entry->len = 0;
  entry->used = 0;
  entry->aborted = false;
  entry->id = 0;
  memset(entry->buffer, 0, data_size);
}

void tsqueue_reset(tsqueue_t *queue) {
  irq_key_t key = irq_lock();
  queue->rix = 0;
  queue->wix = 0;
  queue->next_id = 1;

  for (int i = 0; i < queue->qlen; i++) {
    tsqueue_entry_reset(&queue->entries[i], queue->size);
  }

  irq_unlock(key);
}

static int32_t get_next_id(tsqueue_t *queue) {
  int val = 1;
  if (queue->next_id < INT32_MAX) {
    val = queue->next_id;
    queue->next_id++;
  } else {
    queue->next_id = 2;
  }
  return val;
}

bool tsqueue_enqueue(tsqueue_t *queue, const uint8_t *data, uint16_t len,
                     int32_t *id) {
  irq_key_t key = irq_lock();

  if (queue->entries[queue->wix].used) {
    // Full queue
    irq_unlock(key);
    return false;
  }

  if (len > queue->size) {
    irq_unlock(key);
    return false;
  }

  memcpy(queue->entries[queue->wix].buffer, data, len);
  queue->entries[queue->wix].id = get_next_id(queue);
  queue->entries[queue->wix].len = len;
  queue->entries[queue->wix].used = true;

  if (id != NULL) {
    *id = queue->entries[queue->wix].id;
  }
  queue->wix = (queue->wix + 1) % queue->qlen;

  irq_unlock(key);
  return true;
}

static void tsqueue_discard_aborted(tsqueue_t *queue) {
  while (queue->entries[queue->rix].aborted) {
    tsqueue_entry_reset(&queue->entries[queue->rix], queue->size);
    queue->rix = (queue->rix + 1) % queue->qlen;
  }
}

bool tsqueue_dequeue(tsqueue_t *queue, uint8_t *data, uint16_t max_len,
                     uint16_t *len, int32_t *id) {
  irq_key_t key = irq_lock();

  tsqueue_discard_aborted(queue);

  if (!queue->entries[queue->rix].used) {
    irq_unlock(key);
    return false;
  }

  if (len != NULL) {
    *len = queue->entries[queue->rix].len;
  }

  if (id != NULL) {
    *id = queue->entries[queue->rix].id;
  }

  memcpy(data, queue->entries[queue->rix].buffer,
         MIN(queue->entries[queue->rix].len, max_len));

  tsqueue_entry_reset(queue->entries + queue->rix, queue->size);
  queue->rix = (queue->rix + 1) % queue->qlen;

  tsqueue_discard_aborted(queue);

  irq_unlock(key);
  return true;
}

// Check if the queue is full
bool tsqueue_full(tsqueue_t *queue) {
  irq_key_t key = irq_lock();

  tsqueue_discard_aborted(queue);

  bool full = queue->entries[queue->wix].used;
  irq_unlock(key);
  return full;
}

bool tsqueue_empty(tsqueue_t *queue) {
  irq_key_t key = irq_lock();

  tsqueue_discard_aborted(queue);

  bool empty = !queue->entries[queue->rix].used;

  irq_unlock(key);

  return empty;
}

bool tsqueue_abort(tsqueue_t *queue, int32_t id, uint8_t *data,
                   uint16_t max_len, uint16_t *len) {
  bool found = false;
  irq_key_t key = irq_lock();

  for (int i = 0; i < queue->qlen; i++) {
    if (queue->entries[i].used && queue->entries[i].id == id) {
      queue->entries[i].aborted = true;
      if (len != NULL) {
        *len = queue->entries[i].len;
      }

      if (data != NULL) {
        memcpy(data, queue->entries[i].buffer,
               MIN(queue->entries[i].len, max_len));
      }

      found = true;
    }
  }

  irq_unlock(key);
  return found;
}
