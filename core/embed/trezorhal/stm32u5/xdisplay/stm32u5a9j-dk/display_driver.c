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

#include <stdint.h>
#include <string.h>

#include TREZOR_BOARD
#include STM32_HAL_H

#include "display_internal.h"
#include "mpu.h"
#include "xdisplay.h"

#if (DISPLAY_RESX != 240) || (DISPLAY_RESY != 240)
#error "Incompatible display resolution"
#endif

#ifdef KERNEL_MODE

// Display driver instance
display_driver_t g_display_driver = {
    .initialized = false,
};

void display_init(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (drv->initialized) {
    return;
  }

  if (mode == DISPLAY_RESET_CONTENT) {
    __HAL_RCC_DSI_FORCE_RESET();
    __HAL_RCC_LTDC_FORCE_RESET();
    __HAL_RCC_GFXMMU_FORCE_RESET();
    __HAL_RCC_DSI_RELEASE_RESET();
    __HAL_RCC_LTDC_RELEASE_RESET();
    __HAL_RCC_GFXMMU_RELEASE_RESET();

    RCC_PeriphCLKInitTypeDef PeriphClkInit = {0};

    // Initializes the common periph clock
    PeriphClkInit.PeriphClockSelection = RCC_PERIPHCLK_LTDC | RCC_PERIPHCLK_DSI;
    PeriphClkInit.DsiClockSelection = RCC_DSICLKSOURCE_PLL3;
    PeriphClkInit.LtdcClockSelection = RCC_LTDCCLKSOURCE_PLL3;
    PeriphClkInit.PLL3.PLL3Source = RCC_PLLSOURCE_HSE;
    PeriphClkInit.PLL3.PLL3M = 4;
    PeriphClkInit.PLL3.PLL3N = 125;
    PeriphClkInit.PLL3.PLL3P = 8;
    PeriphClkInit.PLL3.PLL3Q = 2;
    PeriphClkInit.PLL3.PLL3R = 24;
    PeriphClkInit.PLL3.PLL3RGE = RCC_PLLVCIRANGE_0;
    PeriphClkInit.PLL3.PLL3FRACN = 0;
    PeriphClkInit.PLL3.PLL3ClockOut = RCC_PLL3_DIVP | RCC_PLL3_DIVR;
    HAL_RCCEx_PeriphCLKConfig(&PeriphClkInit);

    // Clear framebuffers
    memset(physical_frame_buffer_0, 0x00, PHYSICAL_FRAME_BUFFER_SIZE);
    memset(physical_frame_buffer_1, 0x00, PHYSICAL_FRAME_BUFFER_SIZE);

    BSP_LCD_Init(0, LCD_ORIENTATION_PORTRAIT);
    BSP_LCD_SetBrightness(0, 100);
    BSP_LCD_DisplayOn(0);
  } else {
    // Retain display content
    BSP_LCD_Reinit(0);
    if (current_frame_buffer == 0) {
      BSP_LCD_SetFrameBuffer(0, GFXMMU_VIRTUAL_BUFFER1_BASE_S);
    } else {
      BSP_LCD_SetFrameBuffer(0, GFXMMU_VIRTUAL_BUFFER0_BASE_S);
    }
  }

  drv->initialized = true;
}

void display_deinit(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    if (mode == DISPLAY_RESET_CONTENT) {
      __HAL_RCC_DSI_FORCE_RESET();
      __HAL_RCC_LTDC_FORCE_RESET();
      __HAL_RCC_GFXMMU_FORCE_RESET();
      __HAL_RCC_DSI_RELEASE_RESET();
      __HAL_RCC_LTDC_RELEASE_RESET();
      __HAL_RCC_GFXMMU_RELEASE_RESET();
    }
    return;
  }

  if (mode == DISPLAY_RESET_CONTENT) {
    BSP_LCD_DisplayOff(0);
    BSP_LCD_SetBrightness(0, 0);
    BSP_LCD_DeInit(0);
  }

  mpu_set_unpriv_fb(NULL, 0);

  drv->initialized = false;
}

int display_set_backlight(int level) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  // Just emulation, not doing anything
  drv->backlight_level = level;
  return level;
}

int display_get_backlight(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->orientation_angle;
}

int display_set_orientation(int angle) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  if (angle == 0 || angle == 90 || angle == 180 || angle == 270) {
    // Just emulation, not doing anything
    drv->orientation_angle = angle;
  }

  return drv->orientation_angle;
}

int display_get_orientation(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

  return drv->orientation_angle;
}

void display_fill(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgba8888_fill(&bb_new);
}

void display_copy_rgb565(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgba8888_copy_rgb565(&bb_new);
}

void display_copy_mono1p(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgba8888_copy_mono1p(&bb_new);
}

void display_copy_mono4(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  if (!display_get_frame_buffer(&fb)) {
    return;
  }

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgba8888_copy_mono4(&bb_new);
}

#endif
