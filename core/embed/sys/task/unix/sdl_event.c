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

#include <sys/sysevent.h>
#include <sys/systask.h>
#include <sys/systick.h>

#include <sys/unix/sdl_event.h>

typedef struct {
  sdl_event_filter_cb_t callback;
  void* context;
} sdl_event_filter_t;

typedef struct {
  // Registered event filters
  sdl_event_filter_t filter[4];
} sdl_event_dispatcher_t;

static sdl_event_dispatcher_t g_sdl_event_dispatcher = {0};

bool sdl_events_register(sdl_event_filter_cb_t callback, void* context) {
  sdl_event_dispatcher_t* dispatcher = &g_sdl_event_dispatcher;

  for (int index = 0; index < ARRAY_LENGTH(dispatcher->filter); index++) {
    sdl_event_filter_t* filter = &dispatcher->filter[index];
    if (filter->callback == NULL) {
      filter->callback = callback;
      filter->context = context;
      return true;
    }
  }

  return false;
}

void sdl_events_unregister(sdl_event_filter_cb_t callback, void* context) {
  sdl_event_dispatcher_t* dispatcher = &g_sdl_event_dispatcher;

  for (int index = 0; index < ARRAY_LENGTH(dispatcher->filter); index++) {
    sdl_event_filter_t* filter = &dispatcher->filter[index];
    if (filter->callback == callback && filter->context == context) {
      filter->callback = NULL;
      filter->context = NULL;
    }
  }
}

void sdl_events_poll(void) {
  // SDL functions are not thread-safe, so we process events
  // only in the kernel task context. In other tasks, we just yield
  // use the sysevents_poll() that will poll events in the kernel task.
  if (systask_active() == systask_kernel()) {
    sdl_event_dispatcher_t* dispatcher = &g_sdl_event_dispatcher;
    SDL_Event sdl_event;

    // Process all pending events
    while (SDL_PollEvent(&sdl_event) > 0) {
      for (int index = 0; index < ARRAY_LENGTH(dispatcher->filter); index++) {
        sdl_event_filter_t* filter = &dispatcher->filter[index];
        if (filter->callback != NULL) {
          filter->callback(filter->context, &sdl_event);
        }
      }
    }
  } else {
    sysevents_t awaited = {0};
    sysevents_t signalled = {0};
    sysevents_poll(&awaited, &signalled, ticks_timeout(0));
  }
}
