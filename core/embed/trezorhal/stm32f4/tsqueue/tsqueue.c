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

#include "irq.h"
#include "tsqueue.h"

// Initialize the queue
void tsqueue_init(tsqueue_t *queue, tsqueue_entry_t *entries,
                  uint8_t *buffer_mem, uint16_t size, int qlen) {
  irq_key_t key = irq_lock();
  queue->entries = entries;
  queue->rix = 0;
  queue->fix = 0;
  queue->pix = 0;
  queue->wix = 0;
  queue->qlen = qlen;
  queue->size = size;
  queue->overrun = false;
  queue->overrun_count = 0;
  queue->next_id = 1;

  for (int i = 0; i < qlen; i++) {
    if (buffer_mem != NULL) {
      queue->entries[i].buffer = buffer_mem + i * size;
      memset(queue->entries[i].buffer, 0, size);
    }
    queue->entries[i].state = TSQUEUE_ENTRY_EMPTY;
    queue->entries[i].len = 0;
  }

  irq_unlock(key);
}

static void tsqueue_entry_reset(tsqueue_entry_t *entry, uint32_t data_size) {
  entry->state = TSQUEUE_ENTRY_EMPTY;
  entry->len = 0;
  entry->aborted = false;
  entry->id = 0;
  memset(entry->buffer, 0, data_size);
}

void tsqueue_reset(tsqueue_t *queue) {
  irq_key_t key = irq_lock();
  queue->rix = 0;
  queue->fix = 0;
  queue->pix = 0;
  queue->wix = 0;
  queue->overrun = false;
  queue->overrun_count = 0;
  queue->next_id = 1;

  for (int i = 0; i < queue->qlen; i++) {
    tsqueue_entry_reset(&queue->entries[i], queue->size);
  }

  irq_unlock(key);
}

// Insert data into the queue
bool tsqueue_insert(tsqueue_t *queue, const uint8_t *data, uint16_t len,
                    uint32_t *id) {
  irq_key_t key = irq_lock();

  if (queue->entries[queue->wix].state != TSQUEUE_ENTRY_EMPTY) {
    irq_unlock(key);
    return false;
  }

  if (len > queue->size) {
    irq_unlock(key);
    return false;
  }

  if (queue->fix != queue->wix) {
    // Some item is already allocated, return false
    irq_unlock(key);
    return false;
  }

  memcpy(queue->entries[queue->wix].buffer, data, len);
  queue->entries[queue->wix].state = TSQUEUE_ENTRY_FULL;
  queue->entries[queue->wix].len = len;
  queue->entries[queue->wix].id = queue->next_id++;
  if (id != NULL) {
    *id = queue->entries[queue->wix].id;
  }
  queue->wix = (queue->wix + 1) % queue->qlen;
  queue->fix = queue->wix;

  irq_unlock(key);
  return true;
}

// Allocate an entry in the queue
uint8_t *tsqueue_allocate(tsqueue_t *queue, uint32_t *id) {
  irq_key_t key = irq_lock();

  if (queue->entries[queue->wix].state != TSQUEUE_ENTRY_EMPTY) {
    queue->overrun = true;
    queue->overrun_count++;
    irq_unlock(key);
    return NULL;
  }

  if (queue->fix != queue->wix) {
    // Some item is already allocated, return NULL
    irq_unlock(key);
    return NULL;
  }

  queue->entries[queue->wix].state = TSQUEUE_ENTRY_ALLOCATED;
  queue->entries[queue->wix].id = queue->next_id++;
  if (id != NULL) {
    *id = queue->entries[queue->wix].id;
  }
  uint8_t *buffer = queue->entries[queue->wix].buffer;
  queue->fix = queue->wix;
  queue->wix = (queue->wix + 1) % queue->qlen;

  irq_unlock(key);
  return buffer;
}

// Finalize an allocated entry
bool tsqueue_finalize(tsqueue_t *queue, const uint8_t *buffer, uint16_t len) {
  irq_key_t key = irq_lock();

  if (queue->entries[queue->fix].state != TSQUEUE_ENTRY_ALLOCATED) {
    irq_unlock(key);
    return false;
  }
  if (queue->entries[queue->fix].buffer != buffer) {
    irq_unlock(key);
    return false;
  }

  queue->entries[queue->fix].len = len;
  queue->entries[queue->fix].state = TSQUEUE_ENTRY_FULL;
  queue->fix = (queue->fix + 1) % queue->qlen;

  irq_unlock(key);
  return true;
}

static void tsqueue_discard_aborted(tsqueue_t *queue) {
  while (queue->entries[queue->rix].aborted) {
    tsqueue_entry_reset(&queue->entries[queue->rix], queue->size);
    queue->rix = (queue->rix + 1) % queue->qlen;
    queue->pix = queue->rix;
  }
}

// Read data from the queue
bool tsqueue_read(tsqueue_t *queue, uint8_t *data, uint16_t max_len,
                  uint16_t *len) {
  irq_key_t key = irq_lock();

  tsqueue_discard_aborted(queue);

  if (queue->entries[queue->rix].state != TSQUEUE_ENTRY_FULL) {
    irq_unlock(key);
    return false;
  }

  if (queue->rix != queue->pix) {
    // Some item is being processed, return false
    irq_unlock(key);
    return false;
  }

  if (len != NULL) {
    *len = queue->entries[queue->rix].len;
  }

  memcpy(data, queue->entries[queue->rix].buffer,
         MIN(queue->entries[queue->rix].len, max_len));
  tsqueue_entry_reset(queue->entries + queue->rix, queue->size);
  queue->rix = (queue->rix + 1) % queue->qlen;
  queue->pix = queue->rix;

  tsqueue_discard_aborted(queue);

  irq_unlock(key);
  return true;
}

// Process an entry in the queue
uint8_t *tsqueue_process(tsqueue_t *queue, uint16_t *len) {
  irq_key_t key = irq_lock();

  tsqueue_discard_aborted(queue);

  if (queue->entries[queue->rix].state == TSQUEUE_ENTRY_FULL) {
    queue->entries[queue->rix].state = TSQUEUE_ENTRY_PROCESSING;
  } else {
    irq_unlock(key);
    return NULL;
  }

  if (queue->pix != queue->rix) {
    // Some item is already being processed, return NULL
    irq_unlock(key);
    return NULL;
  }

  queue->pix = queue->rix;
  queue->rix = (queue->rix + 1) % queue->qlen;
  if (len != NULL) {
    *len = queue->entries[queue->pix].len;
  }

  irq_unlock(key);
  return queue->entries[queue->pix].buffer;
}

// Mark processing as done
bool tsqueue_process_done(tsqueue_t *queue, uint8_t *data, uint16_t max_len,
                          uint16_t *len, bool *aborted) {
  irq_key_t key = irq_lock();

  if (queue->entries[queue->pix].state != TSQUEUE_ENTRY_PROCESSING) {
    irq_unlock(key);
    return false;
  }

  if (len != NULL) {
    *len = queue->entries[queue->pix].len;
  }

  if (aborted != NULL) {
    *aborted = queue->entries[queue->pix].aborted;
  }

  memcpy(data, queue->entries[queue->pix].buffer,
         MIN(queue->entries[queue->pix].len, max_len));

  tsqueue_entry_reset(queue->entries + queue->pix, queue->size);

  queue->pix = (queue->pix + 1) % queue->qlen;

  tsqueue_discard_aborted(queue);

  irq_unlock(key);

  return true;
}

// Check if the queue is full
bool tsqueue_full(tsqueue_t *queue) {
  irq_key_t key = irq_lock();

  tsqueue_discard_aborted(queue);

  bool full = queue->entries[queue->wix].state != TSQUEUE_ENTRY_EMPTY;
  irq_unlock(key);
  return full;
}

bool tsqueue_abort(tsqueue_t *queue, uint32_t id, uint8_t *data,
                   uint16_t max_len, uint16_t *len) {
  bool found = false;
  irq_key_t key = irq_lock();

  for (int i = 0; i < queue->qlen; i++) {
    if (queue->entries[i].state != TSQUEUE_ENTRY_EMPTY &&
        queue->entries[i].id == id) {
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
