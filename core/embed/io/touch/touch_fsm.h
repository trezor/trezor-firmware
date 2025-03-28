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

// This module is a simple finite state machine for touch events.
//
// It is designed to be used in a polling loop, where the state of the touch
// is read periodically. The module keeps track of the state changes and
// provides a simple interface to get the events that happened since the last
// call to touch_fsm_get_event().
//
// The benefit of using this module is that it can properly handle situations
// when the touch panel is not read frequently enough or when some
// touch events are missed.
//
// The structure is designed to be used in a multi-threaded environment, where
// each thread has its own state machine. The state machines are stored in an
// array indexed by the task ID.

typedef struct {
  // Time (in ticks) when the tls was last updated
  uint32_t update_ticks;
  // Last reported touch state
  uint32_t state;
  // Set if the touch controller is currently touched
  // (respectively, that we detected a touch event)
  bool pressed;
  // Previously reported x-coordinate
  uint16_t last_x;
  // Previously reported y-coordinate
  uint16_t last_y;
} touch_fsm_t;

// Initializes button finite state machine
void touch_fsm_init(touch_fsm_t* fsm);

// Checks if touch_fsm_get_event() would return `true` on the next call
bool touch_fsm_event_ready(touch_fsm_t* fsm, uint32_t touch_state);

// Processes the new state of thetouch panel and fills the event structure.
//
// `touch_state` is the current state of the touch panel. The state has
// the same format as the return value of `touch_get_state()`.
//
// Returns `true` if the event structure was filled.
uint32_t touch_fsm_get_event(touch_fsm_t* fsm, uint32_t touch_state);
