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

#include "xdisplay_legacy.h"
#include "xdisplay.h"

// This code emulates the legacy display interface and will be
// removed after final cleanup of display drivers when the legacy code
// is removed.

int display_orientation(int angle) {
  if (angle >= 0) {
    return display_set_orientation(angle);
  } else {
    return display_get_orientation();
  }
}

int display_backlight(int level) {
  if (level >= 0) {
    return display_set_backlight(level);
  } else {
    return display_get_backlight();
  }
}

void display_sync(void) {
#ifndef XFRAMEBUFFER
  display_wait_for_sync();
#endif
}
