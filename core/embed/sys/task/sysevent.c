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

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sys/sysevent_source.h>
#include <sys/systask.h>
#include <sys/systick.h>

#ifdef TREZOR_EMULATOR
#include <sys/unix/sdl_event.h>
#endif

typedef struct {
  // Waiting task
  systask_t *task;
  // Deadline for the task to be woken up
  uint32_t deadline;
  // Bitmask of events the task is waiting for
  const sysevents_t *awaited;
  // Bitmask of events that were signaled
  sysevents_t *signalled;
} sysevent_poller_t;

typedef struct {
  const syshandle_vmt_t *vmt;
  void *context;
} sysevent_source_t;

typedef struct {
  // Registered event sources
  sysevent_source_t sources[SYSHANDLE_COUNT];
  // Priority queue of tasks waiting for events
  // (zero index is reserved for the kernel task)
  sysevent_poller_t pollers[SYSTASK_MAX_TASKS];
  // Number of pollers in the list
  size_t pollers_count;

} sysevent_dispatcher_t;

sysevent_dispatcher_t g_sysevent_dispatcher = {0};

bool syshandle_register(syshandle_t handle, const syshandle_vmt_t *vmt,
                        void *context) {
  sysevent_dispatcher_t *dispatcher = &g_sysevent_dispatcher;

  if (handle >= SYSHANDLE_COUNT || dispatcher->sources[handle].vmt != NULL) {
    return false;
  }

  dispatcher->sources[handle].vmt = vmt;
  dispatcher->sources[handle].context = context;
  return true;
}

void syshandle_unregister(syshandle_t handle) {
  sysevent_dispatcher_t *dispatcher = &g_sysevent_dispatcher;

  if (handle < SYSHANDLE_COUNT) {
    dispatcher->sources[handle].vmt = NULL;
    dispatcher->sources[handle].context = NULL;
  }
}

void syshandle_signal_read_ready(syshandle_t handle, void *param) {
  if (handle >= SYSHANDLE_COUNT) {
    return;
  }

  sysevent_dispatcher_t *dispatcher = &g_sysevent_dispatcher;
  const sysevent_source_t *source = &dispatcher->sources[handle];

  // For each polling task, call `check_read_ready` callback
  for (size_t i = 0; i < dispatcher->pollers_count; i++) {
    sysevent_poller_t *poller = &dispatcher->pollers[i];
    syshandle_mask_t handle_mask = 1 << handle;
    if ((poller->awaited->read_ready & handle_mask) != 0) {
      if (source->vmt->check_read_ready != NULL) {
        if (source->vmt->check_read_ready(source->context,
                                          systask_id(poller->task), param)) {
          poller->signalled->read_ready |= handle_mask;
        } else {
          poller->signalled->read_ready &= ~handle_mask;
        }
      }
    }
  }
}

void syshandle_signal_write_ready(syshandle_t handle, void *param) {
  if (handle >= SYSHANDLE_COUNT) {
    return;
  }

  sysevent_dispatcher_t *dispatcher = &g_sysevent_dispatcher;
  const sysevent_source_t *source = &dispatcher->sources[handle];

  // For each polling task, call `check_write_ready` callback
  for (size_t i = 0; i < dispatcher->pollers_count; i++) {
    sysevent_poller_t *poller = &dispatcher->pollers[i];
    syshandle_mask_t handle_mask = 1 << handle;
    if ((poller->awaited->write_ready & handle_mask) != 0) {
      if (source->vmt->check_write_ready != NULL) {
        if (source->vmt->check_write_ready(source->context,
                                           systask_id(poller->task), param)) {
          poller->signalled->write_ready |= handle_mask;
        } else {
          poller->signalled->write_ready &= ~handle_mask;
        }
      }
    }
  }
}

static inline void remove_poller(sysevent_dispatcher_t *dispatcher,
                                 size_t idx) {
  for (size_t j = idx; j < dispatcher->pollers_count - 1; j++) {
    dispatcher->pollers[j] = dispatcher->pollers[j + 1];
  }
  --dispatcher->pollers_count;
}

static inline void insert_poller(sysevent_dispatcher_t *dispatcher,
                                 size_t idx) {
  if (dispatcher->pollers_count >= SYSTASK_MAX_TASKS) {
    // This should never happen since the number of pollers
    // is limited by the number of tasks. But just in case...
    error_shutdown("Too many pollers");
  }

  ++dispatcher->pollers_count;
  if (idx < dispatcher->pollers_count - 1) {
    // Move all pollers with lower priority to the right
    for (size_t j = dispatcher->pollers_count - 1; j > idx; j--) {
      dispatcher->pollers[j] = dispatcher->pollers[j - 1];
    }
  }
}

void sysevents_poll(const sysevents_t *awaited, sysevents_t *signalled,
                    uint32_t deadline) {
  sysevent_dispatcher_t *dispatcher = &g_sysevent_dispatcher;

  memset(signalled, 0, sizeof(*signalled));

  systask_t *kernel_task = systask_kernel();
  systask_t *active_task = systask_active();

  // Determine task priority
  // - Kernel task has the highest priority so it is always first in the list
  // - Unprivileged task use round-robin scheduling
  uint32_t prio = (active_task == kernel_task) ? 0 : dispatcher->pollers_count;

  insert_poller(dispatcher, prio);

  // Add task to the polling list
  // Kernel task has the highest priority so it is always first in the list
  dispatcher->pollers[prio].task = systask_active();
  dispatcher->pollers[prio].awaited = awaited;
  dispatcher->pollers[prio].signalled = signalled;
  dispatcher->pollers[prio].deadline = deadline;

  if (active_task != kernel_task) {
    systask_yield_to(kernel_task);
    return;
  }

  for (;;) {
#ifdef TREZOR_EMULATOR
    // Poll SDL events and dispatch them
    sdl_events_poll();
#endif

    syshandle_mask_t handles_to_read = 0;
    syshandle_mask_t handles_to_write = 0;

    // Gather sources to poll
    for (size_t i = 0; i < dispatcher->pollers_count; i++) {
      sysevent_poller_t *poller = &dispatcher->pollers[i];
      handles_to_read |= poller->awaited->read_ready;
      handles_to_write |= poller->awaited->write_ready;
    }

    // Poll sources we are waiting for
    for (size_t handle = 0; handle < SYSHANDLE_COUNT; handle++) {
      const sysevent_source_t *source = &dispatcher->sources[handle];
      if (source->vmt != NULL) {
        bool read_awaited = (handles_to_read & (1 << handle)) != 0;
        bool write_awaited = (handles_to_write & (1 << handle)) != 0;
        if (read_awaited || write_awaited) {
          source->vmt->poll(source->context, read_awaited, write_awaited);
        }
      }
    }

    uint32_t now = systick_ms();

    // Choose the next task to run
    for (size_t prio = 0; prio < dispatcher->pollers_count; prio++) {
      sysevent_poller_t *poller = &dispatcher->pollers[prio];
      bool timed_out = ((int32_t)(poller->deadline - now)) <= 0;
      bool ready = (poller->signalled->read_ready != 0) ||
                   (poller->signalled->write_ready != 0);
      if (ready || timed_out) {
        systask_t *task = poller->task;
        remove_poller(dispatcher, prio);
        if (task == kernel_task) {
          return;
        } else {
          systask_yield_to(task);
          break;
        }
      }
    }

#ifdef TREZOR_EMULATOR
    // Wait a bit to not consume 100% CPU
    systick_delay_ms(1);
#else
    // Wait for the next event
    __WFI();
#endif
  }
}

void sysevents_notify_task_created(systask_t *task) {
  sysevent_dispatcher_t *dispatcher = &g_sysevent_dispatcher;
  // Notify sources about the task being created
  systask_id_t task_id = systask_id(task);
  for (size_t i = 0; i < SYSHANDLE_COUNT; i++) {
    const sysevent_source_t *source = &dispatcher->sources[i];
    if (source->vmt != NULL && source->vmt->task_created != NULL) {
      source->vmt->task_created(source->context, task_id);
    }
  }
}

// This routine may be called from the fault handler!!!
void sysevents_notify_task_killed(systask_t *task) {
  sysevent_dispatcher_t *dispatcher = &g_sysevent_dispatcher;
  // Remove task from poller list
  // (kernel task is not included)
  for (size_t i = 0; i < dispatcher->pollers_count; i++) {
    if (dispatcher->pollers[i].task == task) {
      remove_poller(dispatcher, i);
      break;
    }
  }

  // Notify sources about the task being killed
  systask_id_t task_id = systask_id(task);
  for (size_t i = 0; i < SYSHANDLE_COUNT; i++) {
    const sysevent_source_t *source = &dispatcher->sources[i];
    if (source->vmt != NULL && source->vmt->task_killed != NULL) {
      source->vmt->task_killed(source->context, task_id);
    }
  }
}

#endif  // KERNEL_MODE
