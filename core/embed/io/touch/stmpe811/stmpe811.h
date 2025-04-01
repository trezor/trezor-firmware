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

#include <io/i2c_bus.h>

typedef struct {
  uint16_t TouchDetected;
  uint16_t X;
  uint16_t Y;
  uint16_t Z;
} TS_StateTypeDef;

void BSP_TS_GetState(TS_StateTypeDef *TsState);

void stmpe811_Reset(i2c_bus_t *i2c_bus);

void touch_set_mode(void);

uint32_t touch_active(void);
