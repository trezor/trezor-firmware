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

#include <trezor_rtl.h>

#include <sys/systick.h>

#include "button_fsm.h"

void button_fsm_init(button_fsm_t* fsm) {
  memset(fsm, 0, sizeof(button_fsm_t));
}

bool button_fsm_event_ready(button_fsm_t* fsm, uint32_t new_state) {
  // Remember state changes
  fsm->pressed |= new_state & ~fsm->state;
  fsm->released |= ~new_state & fsm->state;
  fsm->time = systick_us();
  // Return true if there are any state changes
  return (fsm->pressed | fsm->released) != 0;
}

bool button_fsm_get_event(button_fsm_t* fsm, uint32_t new_state,
                          button_event_t* event) {
  uint64_t now = systick_us();

  if ((now - fsm->time) > 100000) {
    // Reset the history if the button was not read for 100ms
    fsm->pressed = 0;
    fsm->released = 0;
  }

  // Remember state changes and the time of the last read
  fsm->pressed |= new_state & ~fsm->state;
  fsm->released |= ~new_state & fsm->state;

  // Bring the automaton out of invalid states,
  // in case it somehow ends up in one.
  fsm->released &= fsm->pressed | fsm->state;
  fsm->pressed &= fsm->released | ~fsm->state;

  uint8_t button_idx = 0;
  while (fsm->pressed | fsm->released) {
    uint32_t mask = 1 << button_idx;

    if ((fsm->pressed & mask) != 0 && (fsm->state & mask) == 0) {
      // Button press was not signalled yet
      fsm->pressed &= ~mask;
      fsm->state |= mask;
      event->button = (button_t)button_idx;
      event->event_type = BTN_EVENT_DOWN;
      return true;
    } else if ((fsm->released & mask) != 0 && (fsm->state & mask) != 0) {
      // Button release was not signalled yet
      fsm->released &= ~mask;
      fsm->state &= ~mask;
      event->button = (button_t)button_idx;
      event->event_type = BTN_EVENT_UP;
      return true;
    }

    ++button_idx;
  }

  return false;
}

#endif  // KERNEL_MODE
