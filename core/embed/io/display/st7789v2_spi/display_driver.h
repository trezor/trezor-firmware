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

#ifndef ST7789V2_SPI_DISPLAY_DRIVER_H_
#define ST7789V2_SPI_DISPLAY_DRIVER_H_

#include <trezor_types.h>

// Opaque display driver context - fully defined in display_driver.c. Panel
// files (panels/*.c) never look inside it, they just pass the pointer
// through to the helpers below.
typedef struct display_driver display_driver_t;

// ST7789V2 command set (subset used by this driver family)
#define ST7789V2_SLPOUT 0x11
#define ST7789V2_INVON 0x21
#define ST7789V2_DISPON 0x29
#define ST7789V2_CASET 0x2A
#define ST7789V2_RASET 0x2B
#define ST7789V2_RAMWR 0x2C
#define ST7789V2_MADCTL 0x36
#define ST7789V2_COLMOD 0x3A
#define ST7789V2_RAMCTRL 0xB0
#define ST7789V2_PORCTRL 0xB2
#define ST7789V2_VCOMS 0xBB
#define ST7789V2_LCMCTRL 0xC0
#define ST7789V2_VDVVRHEN 0xC2
#define ST7789V2_VRHS 0xC3
#define ST7789V2_VDVS 0xC4
#define ST7789V2_FRCTRL2 0xC6
#define ST7789V2_PWCTRL1 0xD0
#define ST7789V2_PVGAMCTRL 0xE0
#define ST7789V2_NVGAMCTRL 0xE1

// MADCTL rotation bits (ST7789V2 manual, section 8.12)
#define MADCTL_MV (1 << 5)
#define MADCTL_MX (1 << 6)
#define MADCTL_MY (1 << 7)

// Sends a single command byte (DC low). Implemented in display_driver.c,
// used by panels/*.c to issue their register init sequence and orientation
// (MADCTL) writes.
void st7789v2_cmd(display_driver_t *drv, uint8_t cmd);

// Sends data bytes following a command (DC high)
void st7789v2_data(display_driver_t *drv, const uint8_t *data, size_t len);

// Sends a single data byte following a command (DC high)
void st7789v2_data1(display_driver_t *drv, uint8_t byte);

#endif  // ST7789V2_SPI_DISPLAY_DRIVER_H_
