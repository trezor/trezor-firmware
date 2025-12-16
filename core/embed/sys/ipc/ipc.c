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

// Alignment for IPC data within the queue
#define IPC_DATA_ALIGNMENT (sizeof(size_t))

typedef struct {
  uint8_t free;
  systask_id_t remote;
  uint32_t fn;
  size_t size;
  uint8_t __attribute__((aligned(IPC_DATA_ALIGNMENT))) data[];
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

  for (systask_id_t task_id = 0; task_id < SYSTASK_MAX_TASKS; task_id++) {
    syshandle_t handle = SYSHANDLE_IPC0 + task_id;
    void *context = (void *)(uintptr_t)task_id;
    if (!syshandle_register(handle, &g_ipc_handle_vmt, context)) {
      return false;
    }
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

bool ipc_register(systask_id_t remote, void *buffer, size_t size) {
  systask_id_t target = systask_id(systask_active());
  ipc_queue_t *queue = ipc_queue(target, remote);

  if (queue == NULL) {
    return false;
  }

  if (!IS_ALIGNED((uintptr_t)buffer, IPC_DATA_ALIGNMENT)) {
    // Buffer is not properly aligned
    return false;
  }

  queue->ptr = buffer;
  queue->size = size;
  queue->wptr = buffer;
  queue->rptr = buffer;
  return true;
}

void ipc_unregister(systask_id_t remote) {
  systask_id_t target = systask_id(systask_active());
  ipc_queue_t *queue = ipc_queue(target, remote);
  if (queue != NULL) {
    memset(queue, 0, sizeof(ipc_queue_t));
  }
}

bool ipc_try_receive(ipc_message_t *msg) {
  systask_id_t target = systask_id(systask_active());

  ipc_queue_t *queue = ipc_queue(target, msg->remote);

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
    return false;
  }

  msg->fn = item->fn;
  msg->data = item->data;
  msg->size = item->size;

  // Move read pointer to the next item
  queue->rptr +=
      sizeof(ipc_queue_item_t) + ALIGN_UP(item->size, IPC_DATA_ALIGNMENT);

  return true;
}

void ipc_message_free(ipc_message_t *msg) {
  systask_id_t target = systask_id(systask_active());

  ipc_queue_t *queue = ipc_queue(target, msg->remote);

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
      return;
    }

    // Mark the item as free if it matches the data pointer
    if (item->data == msg->data) {
      item->free = true;
    }

    bool advance_wptr = !item->free;

    // Move to next item
    size_t item_size =
        ALIGN_UP(sizeof(ipc_queue_item_t) + item->size, IPC_DATA_ALIGNMENT);
    item = (ipc_queue_item_t *)((uint8_t *)item + item_size);

    if (advance_wptr) {
      new_wptr = item;
    }
  }

  queue->wptr = (uint8_t *)new_wptr;

  if (queue->wptr < queue->rptr) {
    queue->rptr = queue->wptr;
  }
}

bool ipc_send(systask_id_t remote, uint32_t fn, const void *data,
              size_t data_size) {
  systask_id_t origin = systask_id(systask_active());

  ipc_queue_t *queue = ipc_queue(remote, origin);

  if (queue == NULL || queue->ptr == NULL) {
    // Invalid target or no queue registered
    return false;
  }

  if (data_size > 0 && data == NULL) {
    // Invalid message structure
    return false;
  }

  size_t item_size =
      ALIGN_UP(sizeof(ipc_queue_item_t) + data_size, IPC_DATA_ALIGNMENT);
  size_t free_size = queue->size - (queue->wptr - queue->ptr);

  if (item_size > free_size) {
    // Item is too large
    return false;
  }

  ipc_queue_item_t item_hdr = {
      .free = false,
      .remote = origin,
      .fn = fn,
      .size = data_size,
  };

  ipc_queue_item_t *item = (ipc_queue_item_t *)queue->wptr;
  ipc_memcpy(item, &item_hdr, sizeof(item_hdr));

  if (data_size > 0) {
    ipc_memcpy(item->data, data, data_size);
  }

  queue->wptr += item_size;

  return true;
}

static void on_task_created(void *context, systask_id_t task_id) {
  systask_id_t origin = (systask_id_t)(uintptr_t)context;
  ipc_queue_t *queue = ipc_queue(task_id, origin);
  memset(queue, 0, sizeof(ipc_queue_t));
}

static void on_event_poll(void *context, bool read_awaited,
                          bool write_awaited) {
  systask_id_t origin = (systask_id_t)(uintptr_t)context;

  UNUSED(write_awaited);

  if (read_awaited) {
    syshandle_t handle = SYSHANDLE_IPC0 + origin;
    syshandle_signal_read_ready(handle, NULL);
  }
}

static bool on_check_read_ready(void *context, systask_id_t task_id,
                                void *param) {
  systask_id_t origin = (systask_id_t)(uintptr_t)context;

  UNUSED(param);

  ipc_queue_t *queue = ipc_queue(task_id, origin);
  return (queue != NULL && queue->rptr < queue->wptr);
}

static const syshandle_vmt_t g_ipc_handle_vmt = {
    .task_created = on_task_created,
    .task_killed = NULL,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};

#endif  // KERNEL_MODE
