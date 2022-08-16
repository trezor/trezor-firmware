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

#ifndef _DISPLAY_INTERFACE_H
#define _DISPLAY_INTERFACE_H

#include <stdint.h>
#include "common.h"

#if !defined TREZOR_EMULATOR
#include STM32_HAL_H
#endif

#if (defined TREZOR_MODEL_T) && !(defined TREZOR_EMULATOR)

extern __IO uint8_t *const DISPLAY_CMD_ADDRESS;
extern __IO uint8_t *const DISPLAY_DATA_ADDRESS;

#define CMD(X) (*DISPLAY_CMD_ADDRESS = (X))
#define DATA(X) (*DISPLAY_DATA_ADDRESS = (X))
#define PIXELDATA(X) \
  DATA((X)&0xFF);    \
  DATA((X) >> 8)

#else
#define PIXELDATA(c) display_pixeldata(c)
#endif

#ifdef TREZOR_EMULATOR
extern uint8_t *const DISPLAY_DATA_ADDRESS;
#endif

void display_pixeldata(uint16_t c);

#if (defined TREZOR_MODEL_1) && !(defined TREZOR_EMULATOR)
void PIXELDATA_DIRTY();
#else
// noop
#define PIXELDATA_DIRTY()
#endif

void display_reset_state();

void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1);
int display_orientation(int degrees);
int display_get_orientation(void);
int display_backlight(int val);

void display_init(void);
void display_refresh(void);
const char *display_save(const char *prefix);
void display_clear_save(void);

#ifdef TREZOR_MODEL_T
void display_set_little_endian(void);
void display_set_big_endian(void);
#endif

#endif  //_DISPLAY_INTERFACE_H
