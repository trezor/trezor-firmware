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

#include <io/touch.h>
#include <sys/systick.h>

#include "touch_fsm.h"

void touch_fsm_init(touch_fsm_t* fsm) {
  memset(fsm, 0, sizeof(touch_fsm_t));
  fsm->update_ticks = systick_ms();
}

bool touch_fsm_event_ready(touch_fsm_t* fsm, uint32_t touch_state) {
  return fsm->state != touch_state;
}

uint32_t touch_fsm_get_event(touch_fsm_t* fsm, uint32_t touch_state) {
  uint32_t ticks = hal_ticks_ms();

  // Test if the touch_get_event() is starving (not called frequently enough)
  bool starving = (int32_t)(ticks - fsm->update_ticks) > 300 /* ms */;
  fsm->update_ticks = ticks;

  uint16_t x = touch_unpack_x(touch_state);
  uint16_t y = touch_unpack_y(touch_state);

  uint32_t event = 0;
  uint32_t xy = touch_pack_xy(x, y);

  if (touch_state & TOUCH_START) {
    if (!fsm->pressed) {
      // Finger was just pressed down
      event = TOUCH_START | xy;
    } else {
      if ((x != fsm->last_x) || (y != fsm->last_y)) {
        // It looks like we have missed the lift up event
        // We should send the TOUCH_END event here with old coordinates
        event = TOUCH_END | touch_pack_xy(fsm->last_x, fsm->last_y);
      } else {
        // We have received the same coordinates as before,
        // probably this is the same start event, or a quick bounce,
        // we should ignore it.
      }
    }
  } else if (touch_state & TOUCH_MOVE) {
    if (fsm->pressed) {
      if ((fsm->state & TOUCH_START) || (x != fsm->last_x) ||
          (y != fsm->last_y)) {
        // Report the move event only if the coordinates
        // have changed or previous event was TOUCH_START
        event = TOUCH_MOVE | xy;
      }
    } else {
      // We have missed the press down event, we have to simulate it.
      event = TOUCH_START | xy;
    }
  } else if (touch_state & TOUCH_END) {
    if (fsm->pressed) {
      // Finger was just lifted up
      event = TOUCH_END | xy;
    } else {
      if (!starving && ((x != fsm->last_x) || (y != fsm->last_y))) {
        // We have missed the PRESS_DOWN event.
        // Report the start event only if the coordinates
        // have changed and driver is not starving.
        // This suggests that the previous touch was very short,
        // or/and the driver is not called very frequently.
        event = TOUCH_START | xy;
      } else {
        // Either the driver is starving or the coordinates
        // have not changed, which would suggest that the TOUCH_END
        // is repeated, so no event is needed -this should not happen
        // since two consecutive LIFT_UPs are not possible due to
        // testing the interrupt line before reading the registers.
      }
    }
  }

  // remember the last state
  if ((event & TOUCH_START) || (event & TOUCH_MOVE)) {
    fsm->pressed = true;
  } else if (event & TOUCH_END) {
    fsm->pressed = false;
  }

  fsm->last_x = x;
  fsm->last_y = y;
  fsm->state = touch_state;

  return event;
}

#endif  // KERNEL_MODE
