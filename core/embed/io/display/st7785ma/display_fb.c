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
#ifdef KERNEL_MODE
#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/display.h>
#include <sys/mpu.h>
#include <sys/trustzone.h>

#include "display_internal.h"

// Physical frame buffers in internal SRAM memory
__attribute__((section(".fb1")))
ALIGN_32BYTES(uint8_t physical_frame_buffer_0[PHYSICAL_FRAME_BUFFER_SIZE]);

__attribute__((section(".fb2")))
ALIGN_32BYTES(uint8_t physical_frame_buffer_1[PHYSICAL_FRAME_BUFFER_SIZE]);

#ifdef USE_TRUSTZONE
void display_set_unpriv_access(bool unpriv) {
  tz_set_sram_unpriv((uint32_t)physical_frame_buffer_0,
                     PHYSICAL_FRAME_BUFFER_SIZE, unpriv);

  tz_set_sram_unpriv((uint32_t)physical_frame_buffer_1,
                     PHYSICAL_FRAME_BUFFER_SIZE, unpriv);

#ifdef USE_DMA2D
  tz_set_dma2d_unpriv(unpriv);
#endif
}
#endif  //  USE_TRUSTZONE

bool display_get_frame_buffer(display_fb_info_t *fb_dest) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return false;
  }

  uint32_t addr;

  if (drv->current_frame_buffer == 0) {
    addr = (uint32_t)&physical_frame_buffer_1;
  } else {
    addr = (uint32_t)&physical_frame_buffer_0;
  }

  uint32_t fb_stride = FRAME_BUFFER_PIXELS_PER_LINE * sizeof(uint16_t);

  display_fb_info_t fb = {
      .ptr = (void *)addr,
      .stride = fb_stride,
  };

  mpu_set_active_fb((void *)addr, PHYSICAL_FRAME_BUFFER_SIZE);

  memcpy(fb_dest, &fb, sizeof(display_fb_info_t));

  return true;
}

void display_refresh(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  while (!drv->blanking) {
    __WFI();
  }
  if (drv->current_frame_buffer == 0) {
    drv->current_frame_buffer = 1;
    display_set_fb((uint32_t)physical_frame_buffer_1);
  } else {
    drv->current_frame_buffer = 0;
    display_set_fb((uint32_t)physical_frame_buffer_0);
  }
}

void display_fb_clear(void) {
  mpu_set_active_fb(physical_frame_buffer_0, PHYSICAL_FRAME_BUFFER_SIZE);
  memset(physical_frame_buffer_0, 0, PHYSICAL_FRAME_BUFFER_SIZE);
  mpu_set_active_fb(physical_frame_buffer_1, PHYSICAL_FRAME_BUFFER_SIZE);
  memset(physical_frame_buffer_1, 0, PHYSICAL_FRAME_BUFFER_SIZE);
  mpu_set_active_fb(NULL, 0);
}

uint32_t display_fb_get_initial_addr(void) {
  return (uint32_t)physical_frame_buffer_0;
}

void HAL_LTDC_ReloadEventCallback(LTDC_HandleTypeDef *hltdc) {
  // reload_pending = false;
}

void HAL_LTDC_LineEvenCallback(LTDC_HandleTypeDef *hltdc) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  if (drv->blanking) {
    drv->blanking = false;
    // todo use proper constant
    HAL_LTDC_ProgramLineEvent(&drv->hlcd_ltdc, 320);

  } else {
    drv->blanking = true;
    HAL_LTDC_ProgramLineEvent(&drv->hlcd_ltdc, 0);
  }
}

#endif
