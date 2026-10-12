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

// Rounded-corner geometry of the LX250A2401A panel.
//
// The panel is described as runs of lines sharing the same first visible
// pixel (1-based, mirrored on the right edge). The GFXMMU maps only the
// 4-pixel blocks covering the visible range of each line; reads of the rest
// return zero. The table is shared by the GFXMMU lookup table setup and by
// the screen recorder, which masks the emulator's frames the same way so
// that recorded screens match hardware captures.

typedef struct {
  uint16_t lines;
  uint8_t px;
} panel_corner_run_t;

#define PANEL_CORNER_RUNS                                                      \
  {                                                                            \
      {1, 13}, {1, 11}, {1, 9},   {1, 8},  {1, 6},  {2, 5},  {1, 4},  {2, 3},  \
      {2, 2},  {4, 1},  {411, 1}, {12, 1}, {7, 2},  {6, 3},  {5, 4},  {4, 5},  \
      {4, 6},  {3, 7},  {4, 8},   {2, 9},  {4, 10}, {2, 11}, {3, 12}, {2, 13}, \
      {3, 14}, {2, 15}, {2, 16},  {2, 17}, {3, 18}, {1, 19}, {3, 20}, {1, 21}, \
      {2, 22}, {2, 23}, {2, 24},  {1, 25}, {2, 26}, {2, 27}, {1, 28}, {2, 29}, \
      {1, 30}, {1, 32}, {1, 33},  {1, 36},                                     \
  }

// Returns the visible pixel range [first, last] of line `y`, rounded out to
// the 4-pixel blocks the GFXMMU maps.
static inline void panel_visible_range(uint32_t y, uint32_t *first,
                                       uint32_t *last) {
  static const panel_corner_run_t runs[] = PANEL_CORNER_RUNS;
  uint32_t line = 0;
  for (size_t i = 0; i < sizeof(runs) / sizeof(runs[0]); i++) {
    if (y < line + runs[i].lines) {
      uint32_t pixel_cut = runs[i].px - 1;
      *first = (pixel_cut >> 2) * 4;
      *last = ((DISPLAY_RESX - 1 - pixel_cut) >> 2) * 4 + 3;
      return;
    }
    line += runs[i].lines;
  }
  *first = 0;
  *last = DISPLAY_RESX - 1;
}
