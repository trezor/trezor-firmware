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

#include <sys/ipc.h>
#include <sys/sysevent.h>
#include <sys/systick.h>

#ifdef KERNEL_MODE

#include <rtl/sizedefs.h>
#include <sys/sysevent_source.h>
#include <sys/systask.h>

#include "ipc_memcpy.h"

typedef struct {
  uint8_t free;
  systask_id_t origin;
  uint16_t fn;
  size_t size;
  uint8_t data[];
} ipc_queue_item_t;

typedef struct {
  uint8_t *ptr;
  uint8_t *wptr;
  uint8_t *rptr;
  size_t size;
} ipc_queue_t;

typedef struct {
  bool initialized;
  // [target][origin]
  ipc_queue_t queue[SYSTASK_MAX_TASKS][SYSTASK_MAX_TASKS];
} ipc_driver_t;

static ipc_driver_t g_ipc_driver = {
    .initialized = false,
};

// forward declaration
static const syshandle_vmt_t g_ipc_handle_vmt;

bool ipc_init(void) {
  ipc_driver_t *drv = &g_ipc_driver;

  if (drv->initialized) {
    return true;
  }

  memset(drv, 0, sizeof(ipc_driver_t));

  if (!syshandle_register(SYSHANDLE_IPC, &g_ipc_handle_vmt, NULL)) {
    return false;
  }

  drv->initialized = true;
  return true;
}

ipc_queue_t *ipc_queue(systask_id_t target, systask_id_t origin) {
  ipc_driver_t *drv = &g_ipc_driver;

  if (!drv->initialized) {
    return NULL;
  }

  if (target >= SYSTASK_MAX_TASKS || origin >= SYSTASK_MAX_TASKS) {
    return NULL;
  }

  return &drv->queue[target][origin];
}

bool ipc_register(systask_id_t origin, void *buffer, size_t size) {
  systask_id_t target = systask_id(systask_active());
  ipc_queue_t *queue = ipc_queue(target, origin);
  if (queue == NULL) {
    return false;
  }
  queue->ptr = buffer;
  queue->size = size;
  queue->wptr = buffer;
  queue->rptr = buffer;
  return true;
}

void ipc_unregister(systask_id_t origin) {
  systask_id_t target = systask_id(systask_active());
  ipc_queue_t *queue = ipc_queue(target, origin);
  if (queue != NULL) {
    memset(queue, 0, sizeof(ipc_queue_t));
  }
}

bool ipc_try_receive(ipc_message_t *msg) {
  systask_id_t origin = systask_id(systask_active());

  ipc_queue_t *queue = ipc_queue(origin, msg->target);

  if (queue == NULL || queue->ptr == NULL) {
    // Invalid target or no queue registered
    return false;
  }

  if (queue->rptr >= queue->wptr) {
    // No messages available
    return false;
  }

  ipc_queue_item_t *item = (ipc_queue_item_t *)queue->rptr;

  if (item->size > queue->size ||
      queue->rptr + sizeof(ipc_queue_item_t) + item->size > queue->wptr) {
    // Invalid item size
    // !@# kill calling task
    return false;
  }

  msg->origin = item->origin;
  msg->target = origin;
  msg->fn = item->fn;
  msg->data = item->data;
  msg->size = item->size;

  // Move read pointer to the next item
  queue->rptr += sizeof(ipc_queue_item_t) + item->size;

  return true;
}

void ipc_message_free(ipc_message_t *msg) {
  systask_id_t origin = systask_id(systask_active());

  ipc_queue_t *queue = ipc_queue(msg->target, origin);

  if (queue == NULL || queue->ptr == NULL) {
    // Invalid target or no queue registered
    return;
  }

  ipc_queue_item_t *item = (ipc_queue_item_t *)queue->ptr;
  ipc_queue_item_t *new_wptr = item;

  while (item < (ipc_queue_item_t *)queue->wptr) {
    size_t remaining_size = (uint8_t *)queue->wptr - (uint8_t *)item;

    if (remaining_size < sizeof(ipc_queue_item_t) ||
        item->size > remaining_size - sizeof(ipc_queue_item_t)) {
      // Invalid item size => queue corruption
      // !@# kill task?
      return;
    }

    // Mark the item as free if it matches the data pointer
    if (item->data == msg->data) {
      item->free = true;
    }

    size_t item_size = ALIGN_UP(sizeof(ipc_queue_item_t) + item->size, 4);

    bool item_used = !item->free;

    // Next item
    item = (ipc_queue_item_t *)((uint8_t *)item + item_size);

    if (item_used) {
      new_wptr = item;
    }
  }

  queue->wptr = (uint8_t *)new_wptr;
}

bool ipc_send(const ipc_message_t *msg) {
  systask_id_t origin = systask_id(systask_active());

  ipc_queue_t *queue = ipc_queue(msg->target, origin);

  // !@# check if origin task can send to target task

  if (queue == NULL || queue->ptr == NULL) {
    // Invalid target or no queue registered
    return false;
  }

  if (msg->size > 0 && msg->data == NULL) {
    // Invalid message structure
    return false;
  }

  size_t item_size = ALIGN_UP(sizeof(ipc_queue_item_t) + msg->size, 4);
  size_t free_size = queue->size - (queue->wptr - queue->ptr);

  if (item_size > free_size) {
    // Item is too large
    return false;
  }

  ipc_queue_item_t item_hdr = {
      .free = false,
      .origin = origin,
      .fn = msg->fn,
      .size = msg->size,
  };

  ipc_queue_item_t *item = (ipc_queue_item_t *)queue->wptr;
  ipc_memcpy(item, &item_hdr, sizeof(item_hdr));

  if (msg->size > 0) {
    ipc_memcpy(item->data, msg->data, msg->size);
  }

  queue->wptr += item_size;

  return true;
}

static void on_task_created(void *context, systask_id_t task_id) {
  UNUSED(context);
  for (systask_id_t origin = 0; origin < SYSTASK_MAX_TASKS; origin++) {
    ipc_queue_t *queue = ipc_queue(task_id, origin);
    memset(queue, 0, sizeof(ipc_queue_t));
  }
}

static void on_event_poll(void *context, bool read_awaited,
                          bool write_awaited) {
  UNUSED(context);
  UNUSED(write_awaited);

  if (read_awaited) {
    // !@# optimize: only signal if there is a message available
    syshandle_signal_read_ready(SYSHANDLE_IPC, NULL);
  }
}

static bool on_check_read_ready(void *context, systask_id_t task_id,
                                void *param) {
  UNUSED(context);
  UNUSED(param);

  for (systask_id_t origin = 0; origin < SYSTASK_MAX_TASKS; origin++) {
    ipc_queue_t *queue = ipc_queue(task_id, origin);
    if (queue != NULL && queue->ptr != NULL && queue->rptr < queue->wptr) {
      return true;
    }
  }

  return false;
}

static const syshandle_vmt_t g_ipc_handle_vmt = {
    .task_created = on_task_created,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};

#endif  // KERNEL_MODE

bool ipc_call(ipc_message_t *req, ipc_message_t *rsp, uint32_t timeout) {
  // Send the request
  if (!ipc_send(req)) {
    // Failed to send the request
    return false;
  }

  // Wait for the response
  sysevents_t awaited = {.read_ready = 1 << SYSHANDLE_IPC};
  sysevents_t signalled = {0};
  sysevents_poll(&awaited, &signalled, ticks_timeout(timeout));

  if (signalled.read_ready & (1 << SYSHANDLE_IPC)) {
    // Message available
    return ipc_try_receive(rsp);
  }

  // Timeout
  return false;
}
