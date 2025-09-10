
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

#include "lx250a2410a.h"

void lx250a2410a_touch_correction(uint16_t x, uint16_t y, uint16_t *x_new,
                                  uint16_t *y_new) {
  // This panel may report coordinates outside the display area
  *x_new = MIN(x, DISPLAY_RESX - 1);
  *y_new = MIN(y, DISPLAY_RESY - 1);
}
