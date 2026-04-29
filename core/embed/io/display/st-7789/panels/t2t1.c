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

// Using const volatile instead of #define results in binaries that change
// only in 1 byte when the flag changes.
// Using #define leads the compiler to over-optimize the code, resulting in
// larger differences in the binaries.

#include "t2t1.h"

#include "154a.h"
#include "lx154a2411.h"
#include "lx154a2422.h"
#include "tf15411a.h"

#ifdef BOARDLOADER
const volatile uint8_t DISPLAY_ST7789V_INVERT_COLORS2 = 1;
#else
volatile uint8_t DISPLAY_ST7789V_INVERT_COLORS2 = 0;

void t2t1_preserve_inversion(void) {
  DISPLAY_ST7789V_INVERT_COLORS2 = display_panel_is_inverted();
}
#endif

void t2t1_init_seq(void) {
  uint32_t id = display_panel_identify();
  if (id == DISPLAY_ID_GC9307) {
    tf15411a_init_seq();
  } else if (id == DISPLAY_ID_ST7789V) {
    if (DISPLAY_ST7789V_INVERT_COLORS2) {
      lx154a2422_init_seq();
    } else {
      lx154a2411_init_seq();
    }
  } else if (id == DISPLAY_ID_ILI9341V) {
    _154a_init_seq();
  }
}

void t2t1_reinit(void) {
  uint32_t id = display_panel_identify();
  if (id == DISPLAY_ID_ST7789V && display_panel_is_inverted()) {
    lx154a2422_gamma();
  } else if (id == DISPLAY_ID_ST7789V) {
    lx154a2411_gamma();
  }
}

void t2t1_rotate(int degrees, display_padding_t* padding) {
  uint32_t id = display_panel_identify();
  if (id == DISPLAY_ID_GC9307) {
    tf15411a_rotate(degrees, padding);
  } else {
    lx154a2422_rotate(degrees, padding);
  }
}
