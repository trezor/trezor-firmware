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

// TODO: Constants copied from LX200B4501CTP03's correction as a placeholder;
// this panel uses a different touch glass (FT6336U), so CORRECTION is not yet
// verified against real hardware measurements for this module.

#include "lx240d4508ctp05.h"

void lx240d4508ctp05_touch_correction(uint16_t x, uint16_t y, uint16_t *x_new,
                                      uint16_t *y_new) {
#define CENTER (DISPLAY_RESX / 2)
#define CORRECTION 30

  int x_corrected = CENTER + ((x - CENTER) * (CORRECTION + CENTER) / CENTER);

  if (x_corrected < 0) {
    *x_new = 0;
  } else if (x_corrected >= DISPLAY_RESX) {
    *x_new = DISPLAY_RESX - 1;
  } else {
    *x_new = (uint16_t)x_corrected;
  }

  *y_new = y;
}
