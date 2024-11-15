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

#include <trezor_bsp.h>
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/display.h>
#include <sys/mpu.h>

#include "display_internal.h"

#ifdef USE_TRUSTZONE
#include <sys/trustzone.h>
#endif

#ifdef KERNEL_MODE

// Physical frame buffers in internal SRAM memory
__attribute__((section(".fb1"), aligned(PHYSICAL_FRAME_BUFFER_ALIGNMENT)))
uint8_t physical_frame_buffer_0[PHYSICAL_FRAME_BUFFER_SIZE];

__attribute__((section(".fb2"), aligned(PHYSICAL_FRAME_BUFFER_ALIGNMENT)))
uint8_t physical_frame_buffer_1[PHYSICAL_FRAME_BUFFER_SIZE];

#ifdef USE_TRUSTZONE
void display_set_unpriv_access(bool unpriv) {
  // To allow unprivileged access both GFXMMU virtual buffers area and
  // underlying SRAM region must be configured as unprivileged.

  // Order of GFXMMU and SRAM unprivileged access configuration is important
  // to avoid the situation the virtual frame buffer has lower privileges
  // than underlying frame buffer in physical memory so LTDC could not
  // refresh the display properly.

  if (!unpriv) {
    tz_set_gfxmmu_unpriv(unpriv);
  }

  tz_set_sram_unpriv((uint32_t)physical_frame_buffer_0,
                     PHYSICAL_FRAME_BUFFER_SIZE, unpriv);

  tz_set_sram_unpriv((uint32_t)physical_frame_buffer_1,
                     PHYSICAL_FRAME_BUFFER_SIZE, unpriv);

  if (unpriv) {
    tz_set_gfxmmu_unpriv(unpriv);
  }

#ifdef USE_DMA2D
  tz_set_dma2d_unpriv(unpriv);
#endif
}
#endif  //  USE_TRUSTZONE

bool display_get_frame_buffer(display_fb_info_t *fb) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    fb->ptr = NULL;
    fb->stride = 0;
    return false;
  }

  uintptr_t addr;

  if (drv->current_frame_buffer == 0) {
    addr = GFXMMU_VIRTUAL_BUFFER1_BASE_S;
  } else {
    addr = GFXMMU_VIRTUAL_BUFFER0_BASE_S;
  }

  uint32_t fb_stride = FRAME_BUFFER_PIXELS_PER_LINE * sizeof(uint32_t);

  // We do not utilize whole area of the display
  // (discovery kit display is 480x480 and we need just 240x240)
  addr += (480 - DISPLAY_RESY) / 2 * sizeof(uint32_t);
  addr += (480 - DISPLAY_RESX) / 2 * fb_stride;

  fb->ptr = (void *)addr;
  fb->stride = fb_stride;

  // Enable access to the frame buffer from the unprivileged code
  mpu_set_active_fb(fb->ptr, VIRTUAL_FRAME_BUFFER_SIZE);

  return true;
}

void display_refresh(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  // Disable access to the frame buffer from the unprivileged code
  mpu_set_active_fb(NULL, 0);

  if (drv->current_frame_buffer == 0) {
    drv->current_frame_buffer = 1;
    BSP_LCD_SetFrameBuffer(0, GFXMMU_VIRTUAL_BUFFER1_BASE_S);
  } else {
    drv->current_frame_buffer = 0;
    BSP_LCD_SetFrameBuffer(0, GFXMMU_VIRTUAL_BUFFER0_BASE_S);
  }
}

#endif
