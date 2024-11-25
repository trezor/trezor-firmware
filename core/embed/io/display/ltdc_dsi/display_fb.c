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
#include <trezor_model.h>
#include <trezor_rtl.h>

#include <io/display.h>
#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/trustzone.h>

#include "display_internal.h"

#define ALIGNED_PHYSICAL_FRAME_BUFFER_SIZE \
  ALIGN_UP_CONST(PHYSICAL_FRAME_BUFFER_SIZE, PHYSICAL_FRAME_BUFFER_ALIGNMENT)

// Physical frame buffers in internal SRAM memory.
// Both frame buffers layers in the fixed addresses that
// are shared between bootloaders and the firmware.
__attribute__((section(".fb1"), aligned(PHYSICAL_FRAME_BUFFER_ALIGNMENT)))
uint8_t physical_frame_buffer_0[ALIGNED_PHYSICAL_FRAME_BUFFER_SIZE];

#if (FRAME_BUFFER_COUNT > 1)
__attribute__((section(".fb2"), aligned(PHYSICAL_FRAME_BUFFER_ALIGNMENT)))
uint8_t physical_frame_buffer_1[ALIGNED_PHYSICAL_FRAME_BUFFER_SIZE];
#endif

#ifdef USE_TRUSTZONE
void display_set_unpriv_access(bool unpriv) {
  // To allow unprivileged access both GFXMMU virtual buffers area and
  // underlying SRAM region must be configured as unprivileged.

  // Order of GFXMMU and SRAM unprivileged access configuration is important
  // to avoid the situation the virtual frame buffer has lower privileges
  // than underlying frame buffer in physical memory so LTDC could not
  // refresh the display properly.

#ifdef DISPLAY_GFXMMU
  if (!unpriv) {
    tz_set_gfxmmu_unpriv(unpriv);
  }
#endif

  tz_set_sram_unpriv((uint32_t)physical_frame_buffer_0,
                     PHYSICAL_FRAME_BUFFER_SIZE, unpriv);

  tz_set_sram_unpriv((uint32_t)physical_frame_buffer_1,
                     PHYSICAL_FRAME_BUFFER_SIZE, unpriv);

#ifdef DISPLAY_GFXMMU
  if (unpriv) {
    tz_set_gfxmmu_unpriv(unpriv);
  }
#endif

#ifdef USE_DMA2D
  tz_set_dma2d_unpriv(unpriv);
#endif
}
#endif  //  USE_TRUSTZONE

// Returns the pointer to the physical frame buffer (0.. FRAME_BUFFER_COUNT-1)
// Returns NULL if the framebuffer index is out of range.
static uint8_t *get_fb_ptr(int16_t index) {
#ifdef DISPLAY_GFXMMU
  if (index == 0) {
    return (uint8_t *)GFXMMU_VIRTUAL_BUFFER0_BASE_S;
#if (FRAME_BUFFER_COUNT > 1)
  } else if (index == 1) {
    return (uint8_t *)GFXMMU_VIRTUAL_BUFFER1_BASE_S;
#endif
#else
  if (index == 0) {
    return physical_frame_buffer_0;
#if (FRAME_BUFFER_COUNT > 1)
  } else if (index == 1) {
    return physical_frame_buffer_1;
#endif
#endif
  } else {
    return NULL;
  }
}

bool display_get_frame_buffer(display_fb_info_t *fb_dest) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return false;
  }

#if PANEL_LTDC_PIXEL_FORMAT == LTDC_PIXEL_FORMAT_ARGB8888
#define FB_PIXEL_SIZE 4
#elif PANEL_LTDC_PIXEL_FORMAT == LTDC_PIXEL_FORMAT_RGB565
#define FB_PIXEL_SIZE 2
#endif

  fb_queue_wait(&drv->empty_frames);
  int16_t fb_idx = fb_queue_peek(&drv->empty_frames);

  if (fb_idx < 0) {
    fb_dest->ptr = NULL;
    fb_dest->stride = 0;
    return false;
  }

  uintptr_t addr = (uintptr_t)get_fb_ptr(fb_idx);

  uint32_t fb_stride = FRAME_BUFFER_PIXELS_PER_LINE * FB_PIXEL_SIZE;

  // We may not utilize whole area of the display
  addr += (LCD_HEIGHT - DISPLAY_RESY) / 2 * FB_PIXEL_SIZE;
  addr += (LCD_WIDTH - DISPLAY_RESX) / 2 * fb_stride;

  display_fb_info_t fb = {
      .ptr = (void *)addr,
      .stride = fb_stride,
  };

  mpu_set_active_fb((void *)addr, VIRTUAL_FRAME_BUFFER_SIZE);

  memcpy(fb_dest, &fb, sizeof(display_fb_info_t));

  return true;
}

void display_refresh(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  if (!fb_queue_peeked(&drv->empty_frames)) {
    // No refresh needed as the frame buffer is not in
    // the state to be copied to the display
    return;
  }

  fb_queue_put(&drv->ready_frames, fb_queue_take(&drv->empty_frames));
}

void display_ensure_refreshed(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  if (!is_mode_exception()) {
    bool copy_pending;

    // Wait until all frame buffers are written to the display
    //  so we can be sure there's not scheduled or pending
    // background copying
    do {
      irq_key_t key = irq_lock();
      copy_pending =
          !fb_queue_empty(&drv->ready_frames) || drv->update_pending > 0;
      irq_unlock(key);
      __WFI();
    } while (copy_pending);
  }
}

void display_fb_clear(void) {
  mpu_set_active_fb(physical_frame_buffer_0, PHYSICAL_FRAME_BUFFER_SIZE);
  memset(physical_frame_buffer_0, 0, PHYSICAL_FRAME_BUFFER_SIZE);
  mpu_set_active_fb(physical_frame_buffer_1, PHYSICAL_FRAME_BUFFER_SIZE);
  memset(physical_frame_buffer_1, 0, PHYSICAL_FRAME_BUFFER_SIZE);
  mpu_set_active_fb(NULL, 0);
}

uint32_t display_fb_init(void) {
  display_fb_clear();

  fb_queue_reset(&g_display_driver.empty_frames);
  fb_queue_reset(&g_display_driver.ready_frames);

  fb_queue_put(&g_display_driver.empty_frames, 1);

  g_display_driver.active_frame = 0;

  return (uint32_t)get_fb_ptr(0);
}

void HAL_LTDC_LineEvenCallback(LTDC_HandleTypeDef *hltdc) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return;
  }

  if (drv->update_pending > 0) {
    drv->update_pending--;
  }

  int16_t fb_idx = fb_queue_take(&drv->ready_frames);
  if (fb_idx >= 0) {
    fb_queue_put(&drv->empty_frames, drv->active_frame);
    drv->active_frame = fb_idx;
    display_set_fb((uint32_t)get_fb_ptr(drv->active_frame));
    drv->update_pending = 3;
  }

  HAL_LTDC_ProgramLineEvent(&drv->hlcd_ltdc, LCD_HEIGHT);
}

#endif
