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


bool touch_fsm_init(void);

void touch_fsm_deinit(void);
