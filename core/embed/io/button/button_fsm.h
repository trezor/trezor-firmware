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

#include <io/button.h>

// This module is a simple finite state machine for buttons.
//
// It is designed to be used in a polling loop, where the state of the buttons
// is read periodically. The module keeps track of the state changes and
// provides a simple interface to get the events that happened since the last
// call to button_fsm_get_event().
//
// The structure is designed to be used in a multi-threaded environment, where
// each thread has its own state machine. The state machines are stored in an
// array indexed by the task ID.

typedef struct {
  // Time of last update of pressed/released data
  uint64_t time;
  // Button presses that were detected since last get_event call
  uint32_t pressed;
  // Button releases that were detected since last get_event call
  uint32_t released;
  // State of buttons signalled to the poller
  uint32_t state;
} button_fsm_t;

// Initializes button finite state machine
void button_fsm_init(button_fsm_t* fsm);

// Checks if button_fsm_get_event() would return `true` on the next call
bool button_fsm_event_ready(button_fsm_t* fsm, uint32_t new_state);

// Processes the new_state of the button and fills the event structure.
//
// `new_state` is the current state of the buttons - each bit represents
// the state of one button (up to 32 buttons can be handled simultaneously).
//
// Returns `true` if the event structure was filled.
bool button_fsm_get_event(button_fsm_t* fsm, uint32_t new_state,
                          button_event_t* event);
