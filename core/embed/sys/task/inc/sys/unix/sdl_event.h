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

#pragma once

#include <trezor_types.h>

#include "SDL.h"

// This module provides a modular approach to processing SDL events.
//
// SDL events are collected from a single source using the `sdl_event_poll()`
// function, which is called from the main event loop. `sdl_event_poll()` then
// dispatches these events to all registered event filters.

// SDL event filter callback
//
// The callback is invoked for each SDL event.
typedef void (*sdl_event_filter_cb_t)(void* context, SDL_Event* sdl_event);

// Register an SDL event filter
//
// Returns `true` if the filter was successfully registered
bool sdl_events_register(sdl_event_filter_cb_t filter, void* context);

// Unregister an SDL event filter
void sdl_events_unregister(sdl_event_filter_cb_t filter, void* context);

// Process all pending SDL events
//
// Invokes all registered event filters for each event
void sdl_events_poll(void);
