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

#ifndef TREZORHAL_DISPLAY_IO_H
#define TREZORHAL_DISPLAY_IO_H

#include <trezor_bsp.h>
#include <trezor_types.h>

void display_io_init_gpio(void);
void display_io_init_fmc(void);
void display_io_init_te_interrupt(void);

#ifndef FMC_BANK1
#define FMC_BANK1 0x60000000U
#endif

#define DISPLAY_MEMORY_BASE FMC_BANK1
#define DISPLAY_MEMORY_PIN 16

#ifdef DISPLAY_I8080_16BIT_DW
#define DISPLAY_ADDR_SHIFT 2
#define DISP_MEM_TYPE uint16_t
#elif DISPLAY_I8080_8BIT_DW
#define DISPLAY_ADDR_SHIFT 1
#define DISP_MEM_TYPE uint8_t
#else
#error "Unsupported display interface"
#endif

/*#define DISPLAY_CMD_ADDRESS ((__IO DISP_MEM_TYPE *)(DISPLAY_MEMORY_BASE))
#define DISPLAY_DATA_ADDRESS                    \
  ((__IO DISP_MEM_TYPE *)(DISPLAY_MEMORY_BASE | \
                          (DISPLAY_ADDR_SHIFT << DISPLAY_MEMORY_PIN)))
*/

extern __IO DISP_MEM_TYPE *const DISPLAY_CMD_ADDRESS;
extern __IO DISP_MEM_TYPE *const DISPLAY_DATA_ADDRESS;

#define ISSUE_CMD_BYTE(X) (*(DISPLAY_CMD_ADDRESS) = (X))
#define ISSUE_DATA_BYTE(X) (*(DISPLAY_DATA_ADDRESS) = (X))

#ifdef DISPLAY_I8080_16BIT_DW
#define ISSUE_PIXEL_DATA(X) ISSUE_DATA_BYTE(X)
#elif DISPLAY_I8080_8BIT_DW
#define ISSUE_PIXEL_DATA(X)    \
  ISSUE_DATA_BYTE((X) & 0xFF); \
  ISSUE_DATA_BYTE((X) >> 8)
#endif

#endif  // TREZORHAL_DISPLAY_IO_H
