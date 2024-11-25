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

#ifndef TREZOR_HAL_DISPLAY_INTERNAL_H
#define TREZOR_HAL_DISPLAY_INTERNAL_H

#include <trezor_bsp.h>
#include <trezor_types.h>

#include "../fb_queue/fb_queue.h"

#ifdef DISPLAY_PANEL_LX200D2406A
#include "panels/lx200d2406a/lx200d2406a.h"
#elif defined DISPLAY_PANEL_STM32U5A9J_DK
#include "panels/stm32u5a9j-dk/stm32u5a9j-dk.h"
#endif

// Hardware requires physical frame buffer alignment
#ifdef USE_TRUSTZONE
#define PHYSICAL_FRAME_BUFFER_ALIGNMENT TZ_SRAM_ALIGNMENT
#else
#define PHYSICAL_FRAME_BUFFER_ALIGNMENT 32
#endif

typedef struct {
  bool initialized;
  uint16_t update_pending;

  fb_queue_t empty_frames;
  fb_queue_t ready_frames;

  int16_t active_frame;

  // Current display orientation (0, 90, 180, 270)
  int orientation_angle;
  // Current backlight level ranging from 0 to 255
  int backlight_level;
  // The current frame buffer selector

  DSI_HandleTypeDef hlcd_dsi;
  LTDC_HandleTypeDef hlcd_ltdc;
  DSI_VidCfgTypeDef DSIVidCfg;
#ifdef DISPLAY_GFXMMU
  GFXMMU_HandleTypeDef hlcd_gfxmmu;
#endif

} display_driver_t;

extern display_driver_t g_display_driver;

bool display_set_fb(uint32_t fb_addr);

void display_fb_clear(void);

uint32_t display_fb_init(void);

static inline uint32_t is_mode_exception(void) {
  uint32_t isr_number = __get_IPSR() & IPSR_ISR_Msk;
  // Check if the ISR number is not 0 (thread mode) or 11 (SVCall)
  return (isr_number != 0) && (isr_number != 11);
}

void display_ensure_refreshed(void);

bool panel_init(display_driver_t *drv);

#ifdef DISPLAY_GFXMMU
bool display_gfxmmu_init(display_driver_t *drv);
#endif

#endif  // TREZOR_HAL_DISPLAY_INTERNAL_H
