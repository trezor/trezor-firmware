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

#include "SDL.h"

#include <sys/sysevent_source.h>
#include <sys/systask.h>
#include <sys/systick.h>

typedef struct {
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
  // Polling task
  sysevent_poller_t poller;
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
  sysevent_dispatcher_t *dispatcher = &g_sysevent_dispatcher;
  const sysevent_source_t *source =
      handle < SYSHANDLE_COUNT ? &dispatcher->sources[handle] : NULL;

  sysevent_poller_t *poller = &dispatcher->poller;
  syshandle_mask_t handle_mask = 1 << handle;
  if ((poller->awaited->read_ready & handle_mask) != 0) {
    if (source->vmt->check_read_ready != NULL) {
      if (source->vmt->check_read_ready(source->context, 0, param)) {
        poller->signalled->read_ready |= handle_mask;
      } else {
        poller->signalled->read_ready &= ~handle_mask;
      }
    }
  }
}

void syshandle_signal_write_ready(syshandle_t handle, void *param) {
  sysevent_dispatcher_t *dispatcher = &g_sysevent_dispatcher;
  const sysevent_source_t *source =
      handle < SYSHANDLE_COUNT ? &dispatcher->sources[handle] : NULL;

  sysevent_poller_t *poller = &dispatcher->poller;
  syshandle_mask_t handle_mask = 1 << handle;
  if ((poller->awaited->write_ready & handle_mask) != 0) {
    if (source->vmt->check_write_ready != NULL) {
      if (source->vmt->check_write_ready(source->context, 0, param)) {
        poller->signalled->write_ready |= handle_mask;
      } else {
        poller->signalled->write_ready &= ~handle_mask;
      }
    }
  }
}

void sysevents_poll(const sysevents_t *awaited, sysevents_t *signalled,
                    uint32_t timeout) {
  sysevent_dispatcher_t *dispatcher = &g_sysevent_dispatcher;

  // Ensures that SDL events are processed even if the ifaces list
  // contains only USB interfaces. This prevents the emulator from
  // freezing when the user interacts with the window.
  SDL_PumpEvents();

  memset(signalled, 0, sizeof(*signalled));

  sysevent_poller_t *poller = &dispatcher->poller;
  poller->awaited = awaited;
  poller->signalled = signalled;
  poller->deadline = ticks_timeout(timeout);

  for (;;) {
    // Poll sources we are waiting for
    for (size_t handle = 0; handle < SYSHANDLE_COUNT; handle++) {
      const sysevent_source_t *source = &dispatcher->sources[handle];
      if (source->vmt != NULL) {
        const sysevents_t *awaited = poller->awaited;
        bool read_awaited = (awaited->read_ready & (1 << handle)) != 0;
        bool write_awaited = (awaited->write_ready & (1 << handle)) != 0;
        if (read_awaited || write_awaited) {
          source->vmt->poll(source->context, read_awaited, write_awaited);
        }
      }
    }

    if ((poller->signalled->read_ready | poller->signalled->write_ready) != 0) {
      break;
    }

    if (ticks_expired(poller->deadline)) {
      break;
    }

    systick_delay_ms(1);
  }
}
