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

#ifndef TREZORHAL_ST7789_PANEL_H
#define TREZORHAL_ST7789_PANEL_H

#include <stdbool.h>
#include <stdint.h>

// section "9.1.3 RDDID (04h): Read Display ID"
// of ST7789V datasheet
#define DISPLAY_ID_ST7789V 0x858552U
// section "6.2.1. Read display identification information (04h)"
// of GC9307 datasheet
#define DISPLAY_ID_GC9307 0x009307U
// section "8.3.23 Read ID4 (D3h)"
// of ILI9341V datasheet
#define DISPLAY_ID_ILI9341V 0x009341U

typedef struct {
  uint16_t x;
  uint16_t y;
} display_padding_t;

// Identifies the connected display panel and
// returns one of DISPLAY_ID_xxx constant
uint32_t display_panel_identify(void);
bool display_panel_is_inverted();

void display_panel_init(void);
// Due to inability to change display setting in boardlaoder,
// we need to reinitialize the display when bootloader or firmware runs
void display_panel_reinit(void);
void display_panel_set_little_endian(void);
void display_panel_set_big_endian(void);

void display_panel_sleep(void);
void display_panel_unsleep(void);
void display_panel_set_window(uint16_t x0, uint16_t y0, uint16_t x1,
                              uint16_t y1);
void display_panel_rotate(int angle);

#endif  // TREZORHAL_ST7789_PANEL_H
