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

// Turning off the stack protector for this file improves
// the performance of drawing operations when called frequently.
#pragma GCC optimize("no-stack-protector")

#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <gfx/dma2d_bitblt.h>
#include <gfx/gfx_color.h>

// Number of DMA2D layers - background (0) and foreground (1)
#define DMA2D_LAYER_COUNT 2

typedef struct {
  // Set if the driver is initialized
  bool initialized;
  // ST DMA2D driver handle
  DMA2D_HandleTypeDef handle;
  // CLUT cache
  struct {
    gfx_color32_t c_fg;
    gfx_color32_t c_bg;
  } cache[DMA2D_LAYER_COUNT];

  // CLUT is configured according to the cache
  bool clut_valid;

} dma2d_driver_t;

static dma2d_driver_t g_dma2d_driver = {
    .initialized = false,
};

// Returns `true` if the specified address is accessible by DMA2D
// and can be used by any of the following functions
static inline bool dma2d_accessible(const void* ptr) {
#ifdef STM32F4
  const void* ccm_start = (const void*)0x10000000;
  const void* ccm_end = (const void*)0x1000FFFF;
  return !(ptr >= ccm_start && ptr <= ccm_end);
#else
  return true;
#endif
}

void dma2d_init(void) {
  dma2d_driver_t* drv = &g_dma2d_driver;
  if (drv->initialized) {
    return;
  }
  memset(drv, 0, sizeof(dma2d_driver_t));
  drv->handle.Instance = DMA2D;

#ifdef KERNEL_MODE
  __HAL_RCC_DMA2D_FORCE_RESET();
  __HAL_RCC_DMA2D_RELEASE_RESET();
  __HAL_RCC_DMA2D_CLK_ENABLE();
#endif
  drv->initialized = true;
}

void dma2d_deinit(void) {
  dma2d_driver_t* drv = &g_dma2d_driver;

#ifdef KERNEL_MODE
  __HAL_RCC_DMA2D_CLK_DISABLE();
  __HAL_RCC_DMA2D_FORCE_RESET();
  __HAL_RCC_DMA2D_RELEASE_RESET();
#endif
  memset(drv, 0, sizeof(dma2d_driver_t));
}

void dma2d_wait(void) {
  dma2d_driver_t* drv = &g_dma2d_driver;

  if (!drv->initialized) {
    return;
  }

  while (HAL_DMA2D_PollForTransfer(&drv->handle, 10) != HAL_OK)
    ;
}

bool dma2d_rgb565_fill(const gfx_bitblt_t* bb) {
  dma2d_driver_t* drv = &g_dma2d_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!gfx_bitblt_check_dst_x(bb, 16)) {
    return false;
  }

  dma2d_wait();

  if (!dma2d_accessible(bb->dst_row)) {
    return false;
  }

  if (bb->src_alpha == 255) {
    drv->handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
    drv->handle.Init.Mode = DMA2D_R2M;
    drv->handle.Init.OutputOffset =
        bb->dst_stride / sizeof(uint16_t) - bb->width;
    HAL_DMA2D_Init(&drv->handle);

    HAL_DMA2D_Start(&drv->handle, gfx_color_to_color32(bb->src_fg),
                    (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t),
                    bb->width, bb->height);
  } else {
#ifdef STM32U5
    drv->handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
    drv->handle.Init.Mode = DMA2D_M2M_BLEND_FG;
    drv->handle.Init.OutputOffset =
        bb->dst_stride / sizeof(uint16_t) - bb->width;
    HAL_DMA2D_Init(&drv->handle);

    drv->handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_RGB565;
    drv->handle.LayerCfg[1].InputOffset = 0;
    drv->handle.LayerCfg[1].AlphaMode = DMA2D_REPLACE_ALPHA;
    drv->handle.LayerCfg[1].InputAlpha = bb->src_alpha;
    HAL_DMA2D_ConfigLayer(&drv->handle, 1);

    drv->handle.LayerCfg[0].InputColorMode = DMA2D_INPUT_RGB565;
    drv->handle.LayerCfg[0].InputOffset =
        bb->dst_stride / sizeof(uint16_t) - bb->width;
    drv->handle.LayerCfg[0].AlphaMode = 0;
    drv->handle.LayerCfg[0].InputAlpha = 0;
    HAL_DMA2D_ConfigLayer(&drv->handle, 0);

    HAL_DMA2D_BlendingStart(
        &drv->handle, gfx_color_to_color32(bb->src_fg),
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t),
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t), bb->width,
        bb->height);
#else
    // STM32F4 can not accelerate blending with the fixed color
    return false;
#endif
  }

  return true;
}

static void dma2d_config_clut(uint32_t layer, gfx_color32_t fg,
                              gfx_color32_t bg) {
  dma2d_driver_t* drv = &g_dma2d_driver;

#define GRADIENT_STEPS 16

  if (layer >= ARRAY_LENGTH(drv->cache)) {
    return;
  }

  volatile uint32_t* clut =
      layer ? drv->handle.Instance->FGCLUT : drv->handle.Instance->BGCLUT;

  if (fg != drv->cache[layer].c_fg || bg != drv->cache[layer].c_bg ||
      !drv->clut_valid) {
    drv->cache[layer].c_fg = fg;
    drv->cache[layer].c_bg = bg;
    drv->clut_valid = true;

    for (int step = 0; step < GRADIENT_STEPS; step++) {
      clut[step] = gfx_color32_rgba(
          a4_lerp(gfx_color32_to_r(fg), gfx_color32_to_r(bg), step),
          a4_lerp(gfx_color32_to_g(fg), gfx_color32_to_g(bg), step),
          a4_lerp(gfx_color32_to_b(fg), gfx_color32_to_b(bg), step),
          a4_lerp(gfx_color32_to_a(fg), gfx_color32_to_a(bg), step));
    }

    DMA2D_CLUTCfgTypeDef clut_def = {0};
    clut_def.CLUTColorMode = DMA2D_CCM_ARGB8888;
    clut_def.Size = GRADIENT_STEPS - 1;
    clut_def.pCLUT = 0;  // ???

    HAL_DMA2D_ConfigCLUT(&drv->handle, clut_def, layer);
  }
}

static void dma2d_rgb565_copy_mono4_first_col(gfx_bitblt_t* bb,
                                              const gfx_color16_t* gradient) {
  uint16_t* dst_ptr = (uint16_t*)bb->dst_row + bb->dst_x;
  uint8_t* src_ptr = (uint8_t*)bb->src_row + bb->src_x / 2;

  int height = bb->height;

  while (height-- > 0) {
    uint8_t fg_lum = src_ptr[0] >> 4;
    dst_ptr[0] = gradient[fg_lum];
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_ptr += bb->src_stride / sizeof(*src_ptr);
  }
}

static void dma2d_rgb565_copy_mono4_last_col(gfx_bitblt_t* bb,
                                             const gfx_color16_t* gradient) {
  uint16_t* dst_ptr = (uint16_t*)bb->dst_row + (bb->dst_x + bb->width - 1);
  uint8_t* src_ptr = (uint8_t*)bb->src_row + (bb->src_x + bb->width - 1) / 2;

  int height = bb->height;

  while (height-- > 0) {
    uint8_t fg_lum = src_ptr[0] & 0x0F;
    dst_ptr[0] = gradient[fg_lum];
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_ptr += bb->src_stride / sizeof(*src_ptr);
  }
}

bool dma2d_rgb565_copy_mono4(const gfx_bitblt_t* params) {
  dma2d_driver_t* drv = &g_dma2d_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!gfx_bitblt_check_dst_x(params, 16) ||
      !gfx_bitblt_check_src_x(params, 4)) {
    return false;
  }

  const gfx_color16_t* src_gradient = NULL;

  gfx_bitblt_t bb_copy = *params;
  gfx_bitblt_t* bb = &bb_copy;

  dma2d_wait();

  if (!dma2d_accessible(bb->dst_row) || !dma2d_accessible(bb->src_row)) {
    return false;
  }

  if (bb->src_x & 1) {
    // First column of mono4 bitmap is odd
    // Use the CPU to draw the first column
    src_gradient = gfx_color16_gradient_a4(bb->src_fg, bb->src_bg);
    dma2d_rgb565_copy_mono4_first_col(bb, src_gradient);
    bb->dst_x += 1;
    bb->src_x += 1;
    bb->width -= 1;
  }

  if (bb->width > 0 && bb->width & 1) {
    // The width is odd
    // Use the CPU to draw the last column
    if (src_gradient == NULL) {
      src_gradient = gfx_color16_gradient_a4(bb->src_fg, bb->src_bg);
    }
    dma2d_rgb565_copy_mono4_last_col(bb, src_gradient);
    bb->width -= 1;
  }

  drv->handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
  drv->handle.Init.Mode = DMA2D_M2M_PFC;
  drv->handle.Init.OutputOffset = bb->dst_stride / sizeof(uint16_t) - bb->width;
  HAL_DMA2D_Init(&drv->handle);

  drv->handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_L4;
  drv->handle.LayerCfg[1].InputOffset = bb->src_stride * 2 - bb->width;
  drv->handle.LayerCfg[1].AlphaMode = 0;
  drv->handle.LayerCfg[1].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&drv->handle, 1);

  dma2d_config_clut(1, gfx_color_to_color32(bb->src_fg),
                    gfx_color_to_color32(bb->src_bg));

  HAL_DMA2D_Start(&drv->handle, (uint32_t)bb->src_row + bb->src_x / 2,
                  (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t),
                  bb->width, bb->height);
  return true;
}

bool dma2d_rgb565_copy_rgb565(const gfx_bitblt_t* bb) {
  dma2d_driver_t* drv = &g_dma2d_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!gfx_bitblt_check_dst_x(bb, 16) || !gfx_bitblt_check_src_x(bb, 16)) {
    return false;
  }

  dma2d_wait();

  if (!dma2d_accessible(bb->dst_row) || !dma2d_accessible(bb->src_row)) {
    return false;
  }

  drv->handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
  drv->handle.Init.Mode = DMA2D_M2M_PFC;
  drv->handle.Init.OutputOffset = bb->dst_stride / sizeof(uint16_t) - bb->width;
  HAL_DMA2D_Init(&drv->handle);

  drv->handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_RGB565;
  drv->handle.LayerCfg[1].InputOffset =
      bb->src_stride / sizeof(uint16_t) - bb->width;
  drv->handle.LayerCfg[1].AlphaMode = 0;
  drv->handle.LayerCfg[1].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&drv->handle, 1);

  HAL_DMA2D_Start(&drv->handle,
                  (uint32_t)bb->src_row + bb->src_x * sizeof(uint16_t),
                  (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t),
                  bb->width, bb->height);
  return true;
}

static void dma2d_rgb565_blend_mono4_first_col(const gfx_bitblt_t* bb) {
  uint16_t* dst_ptr = (uint16_t*)bb->dst_row + bb->dst_x;
  uint8_t* src_ptr = (uint8_t*)bb->src_row + bb->src_x / 2;

  int height = bb->height;

  while (height-- > 0) {
    uint8_t fg_alpha = src_ptr[0] >> 4;
    fg_alpha = (fg_alpha * bb->src_alpha) / 15;
    dst_ptr[0] = gfx_color16_blend_a8(
        bb->src_fg, gfx_color16_to_color(dst_ptr[0]), fg_alpha);
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_ptr += bb->src_stride / sizeof(*src_ptr);
  }
}

static void dma2d_rgb565_blend_mono4_last_col(const gfx_bitblt_t* bb) {
  uint16_t* dst_ptr = (uint16_t*)bb->dst_row + (bb->dst_x + bb->width - 1);
  uint8_t* src_ptr = (uint8_t*)bb->src_row + (bb->src_x + bb->width - 1) / 2;

  int height = bb->height;

  while (height-- > 0) {
    uint8_t fg_alpha = src_ptr[0] & 0x0F;
    fg_alpha = (fg_alpha * bb->src_alpha) / 15;
    dst_ptr[0] = gfx_color16_blend_a8(
        bb->src_fg, gfx_color16_to_color(dst_ptr[0]), fg_alpha);
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_ptr += bb->src_stride / sizeof(*src_ptr);
  }
}

bool dma2d_rgb565_blend_mono4(const gfx_bitblt_t* params) {
  dma2d_driver_t* drv = &g_dma2d_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!gfx_bitblt_check_dst_x(params, 16) ||
      !gfx_bitblt_check_src_x(params, 4)) {
    return false;
  }

  dma2d_wait();

  gfx_bitblt_t bb_copy = *params;
  gfx_bitblt_t* bb = &bb_copy;

  if (!dma2d_accessible(bb->dst_row) || !dma2d_accessible(bb->src_row)) {
    return false;
  }

  if (bb->src_x & 1) {
    // First column of mono4 bitmap is odd
    // Use the CPU to draw the first column
    dma2d_rgb565_blend_mono4_first_col(bb);
    bb->dst_x += 1;
    bb->src_x += 1;
    bb->width -= 1;
  }

  if (bb->width > 0 && bb->width & 1) {
    // The width is odd
    // Use the CPU to draw the last column
    dma2d_rgb565_blend_mono4_last_col(bb);
    bb->width -= 1;
  }

  if (bb->width > 0) {
    drv->handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
    drv->handle.Init.Mode = DMA2D_M2M_BLEND;
    drv->handle.Init.OutputOffset =
        bb->dst_stride / sizeof(uint16_t) - bb->width;
    HAL_DMA2D_Init(&drv->handle);

    drv->handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_L4;
    drv->handle.LayerCfg[1].InputOffset = bb->src_stride * 2 - bb->width;
    drv->handle.LayerCfg[1].AlphaMode = DMA2D_COMBINE_ALPHA;
    drv->handle.LayerCfg[1].InputAlpha = bb->src_alpha;
    HAL_DMA2D_ConfigLayer(&drv->handle, 1);

    dma2d_config_clut(
        1, gfx_color_to_color32(bb->src_fg),
        gfx_color32_set_alpha(gfx_color_to_color32(bb->src_fg), 0));

    drv->handle.LayerCfg[0].InputColorMode = DMA2D_INPUT_RGB565;
    drv->handle.LayerCfg[0].InputOffset =
        bb->dst_stride / sizeof(uint16_t) - bb->width;
    drv->handle.LayerCfg[0].AlphaMode = 0;
    drv->handle.LayerCfg[0].InputAlpha = 0;
    HAL_DMA2D_ConfigLayer(&drv->handle, 0);

    HAL_DMA2D_BlendingStart(
        &drv->handle, (uint32_t)bb->src_row + bb->src_x / 2,
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t),
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t), bb->width,
        bb->height);
  }

  return true;
}

bool dma2d_rgb565_blend_mono8(const gfx_bitblt_t* bb) {
  dma2d_driver_t* drv = &g_dma2d_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!gfx_bitblt_check_dst_x(bb, 16) || !gfx_bitblt_check_src_x(bb, 8)) {
    return false;
  }

  dma2d_wait();

  if (!dma2d_accessible(bb->dst_row) || !dma2d_accessible(bb->src_row)) {
    return false;
  }

  drv->handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
  drv->handle.Init.Mode = DMA2D_M2M_BLEND;
  drv->handle.Init.OutputOffset = bb->dst_stride / sizeof(uint16_t) - bb->width;
  HAL_DMA2D_Init(&drv->handle);

  drv->handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_A8;
  drv->handle.LayerCfg[1].InputOffset = bb->src_stride - bb->width;
  drv->handle.LayerCfg[1].AlphaMode = 0;
  drv->handle.LayerCfg[1].InputAlpha = gfx_color_to_color32(bb->src_fg);
  HAL_DMA2D_ConfigLayer(&drv->handle, 1);

  drv->handle.LayerCfg[0].InputColorMode = DMA2D_INPUT_RGB565;
  drv->handle.LayerCfg[0].InputOffset =
      bb->dst_stride / sizeof(uint16_t) - bb->width;
  drv->handle.LayerCfg[0].AlphaMode = 0;
  drv->handle.LayerCfg[0].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&drv->handle, 0);

  HAL_DMA2D_BlendingStart(&drv->handle, (uint32_t)bb->src_row + bb->src_x,
                          (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t),
                          (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t),
                          bb->width, bb->height);

  return true;
}

bool dma2d_rgba8888_fill(const gfx_bitblt_t* bb) {
  dma2d_driver_t* drv = &g_dma2d_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!gfx_bitblt_check_dst_x(bb, 32)) {
    return false;
  }

  dma2d_wait();

  if (!dma2d_accessible(bb->dst_row)) {
    return false;
  }

  if (bb->src_alpha == 255) {
    drv->handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
    drv->handle.Init.Mode = DMA2D_R2M;
    drv->handle.Init.OutputOffset =
        bb->dst_stride / sizeof(uint32_t) - bb->width;
    HAL_DMA2D_Init(&drv->handle);

    HAL_DMA2D_Start(&drv->handle, gfx_color_to_color32(bb->src_fg),
                    (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
                    bb->width, bb->height);
  } else {
#ifdef STM32U5
    drv->handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
    drv->handle.Init.Mode = DMA2D_M2M_BLEND_FG;
    drv->handle.Init.OutputOffset =
        bb->dst_stride / sizeof(uint32_t) - bb->width;
    HAL_DMA2D_Init(&drv->handle);

    drv->handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_ARGB8888;
    drv->handle.LayerCfg[1].InputOffset = 0;
    drv->handle.LayerCfg[1].AlphaMode = DMA2D_REPLACE_ALPHA;
    drv->handle.LayerCfg[1].InputAlpha = bb->src_alpha;
    HAL_DMA2D_ConfigLayer(&drv->handle, 1);

    drv->handle.LayerCfg[0].InputColorMode = DMA2D_INPUT_ARGB8888;
    drv->handle.LayerCfg[0].InputOffset =
        bb->dst_stride / sizeof(uint32_t) - bb->width;
    drv->handle.LayerCfg[0].AlphaMode = 0;
    drv->handle.LayerCfg[0].InputAlpha = 0;
    HAL_DMA2D_ConfigLayer(&drv->handle, 0);

    HAL_DMA2D_BlendingStart(
        &drv->handle, gfx_color_to_color32(bb->src_fg),
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t), bb->width,
        bb->height);
#else
    // STM32F4 can not accelerate blending with the fixed color
    return false;
#endif
  }
  return true;
}

static void dma2d_rgba8888_copy_mono4_first_col(gfx_bitblt_t* bb,
                                                const gfx_color32_t* gradient) {
  uint32_t* dst_ptr = (uint32_t*)bb->dst_row + bb->dst_x;
  uint8_t* src_ptr = (uint8_t*)bb->src_row + bb->src_x / 2;

  int height = bb->height;

  while (height-- > 0) {
    uint8_t fg_lum = src_ptr[0] >> 4;
    dst_ptr[0] = gradient[fg_lum];
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_ptr += bb->src_stride / sizeof(*src_ptr);
  }
}

static void dma2d_rgba8888_copy_mono4_last_col(gfx_bitblt_t* bb,
                                               const gfx_color32_t* gradient) {
  uint32_t* dst_ptr = (uint32_t*)bb->dst_row + (bb->dst_x + bb->width - 1);
  uint8_t* src_ptr = (uint8_t*)bb->src_row + (bb->src_x + bb->width - 1) / 2;

  int height = bb->height;

  while (height-- > 0) {
    uint8_t fg_lum = src_ptr[0] & 0x0F;
    dst_ptr[0] = gradient[fg_lum];
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_ptr += bb->src_stride / sizeof(*src_ptr);
  }
}

bool dma2d_rgba8888_copy_mono4(const gfx_bitblt_t* params) {
  dma2d_driver_t* drv = &g_dma2d_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!gfx_bitblt_check_dst_x(params, 32) ||
      !gfx_bitblt_check_src_x(params, 4)) {
    return false;
  }

  dma2d_wait();

  const gfx_color32_t* src_gradient = NULL;
  gfx_bitblt_t bb_copy = *params;
  gfx_bitblt_t* bb = &bb_copy;

  dma2d_wait();

  if (!dma2d_accessible(bb->dst_row) || !dma2d_accessible(bb->src_row)) {
    return false;
  }

  if (bb->src_x & 1) {
    // First column of mono4 bitmap is odd
    // Use the CPU to draw the first column
    src_gradient = gfx_color32_gradient_a4(bb->src_fg, bb->src_bg);
    dma2d_rgba8888_copy_mono4_first_col(bb, src_gradient);
    bb->dst_x += 1;
    bb->src_x += 1;
    bb->width -= 1;
  }

  if (bb->width > 0 && bb->width & 1) {
    // The width is odd
    // Use the CPU to draw the last column
    if (src_gradient == NULL) {
      src_gradient = gfx_color32_gradient_a4(bb->src_fg, bb->src_bg);
    }
    dma2d_rgba8888_copy_mono4_last_col(bb, src_gradient);
    bb->width -= 1;
  }

  drv->handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
  drv->handle.Init.Mode = DMA2D_M2M_PFC;
  drv->handle.Init.OutputOffset = bb->dst_stride / sizeof(uint32_t) - bb->width;
  HAL_DMA2D_Init(&drv->handle);

  drv->handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_L4;
  drv->handle.LayerCfg[1].InputOffset = bb->src_stride * 2 - bb->width;
  drv->handle.LayerCfg[1].AlphaMode = 0;
  drv->handle.LayerCfg[1].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&drv->handle, 1);

  dma2d_config_clut(1, gfx_color_to_color32(bb->src_fg),
                    gfx_color_to_color32(bb->src_bg));

  HAL_DMA2D_Start(&drv->handle, (uint32_t)bb->src_row + bb->src_x / 2,
                  (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
                  bb->width, bb->height);
  return true;
}

bool dma2d_rgba8888_copy_rgb565(const gfx_bitblt_t* bb) {
  dma2d_driver_t* drv = &g_dma2d_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!gfx_bitblt_check_dst_x(bb, 32) || !gfx_bitblt_check_src_x(bb, 16)) {
    return false;
  }

  dma2d_wait();

  if (!dma2d_accessible(bb->dst_row) || !dma2d_accessible(bb->src_row)) {
    return false;
  }

  drv->handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
  drv->handle.Init.Mode = DMA2D_M2M_PFC;
  drv->handle.Init.OutputOffset = bb->dst_stride / sizeof(uint32_t) - bb->width;
  HAL_DMA2D_Init(&drv->handle);

  drv->handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_RGB565;
  drv->handle.LayerCfg[1].InputOffset =
      bb->src_stride / sizeof(uint16_t) - bb->width;
  drv->handle.LayerCfg[1].AlphaMode = 0;
  drv->handle.LayerCfg[1].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&drv->handle, 1);

  HAL_DMA2D_Start(&drv->handle,
                  (uint32_t)bb->src_row + bb->src_x * sizeof(uint16_t),
                  (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
                  bb->width, bb->height);
  return true;
}

static void dma2d_rgba8888_blend_mono4_first_col(const gfx_bitblt_t* bb) {
  uint32_t* dst_ptr = (uint32_t*)bb->dst_row + bb->dst_x;
  uint8_t* src_ptr = (uint8_t*)bb->src_row + bb->src_x / 2;

  int height = bb->height;

  while (height-- > 0) {
    uint8_t fg_alpha = src_ptr[0] >> 4;
    fg_alpha = (fg_alpha * bb->src_alpha) / 15;
    dst_ptr[0] = gfx_color32_blend_a8(
        bb->src_fg, gfx_color32_to_color(dst_ptr[0]), fg_alpha);
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_ptr += bb->src_stride / sizeof(*src_ptr);
  }
}

static void dma2d_rgba8888_blend_mono4_last_col(const gfx_bitblt_t* bb) {
  uint32_t* dst_ptr = (uint32_t*)bb->dst_row + (bb->dst_x + bb->width - 1);
  uint8_t* src_ptr = (uint8_t*)bb->src_row + (bb->src_x + bb->width - 1) / 2;

  int height = bb->height;

  while (height-- > 0) {
    uint8_t fg_alpha = src_ptr[0] & 0x0F;
    fg_alpha = (fg_alpha * bb->src_alpha) / 15;
    dst_ptr[0] = gfx_color32_blend_a8(
        bb->src_fg, gfx_color32_to_color(dst_ptr[0]), fg_alpha);
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_ptr += bb->src_stride / sizeof(*src_ptr);
  }
}

bool dma2d_rgba8888_blend_mono4(const gfx_bitblt_t* params) {
  dma2d_driver_t* drv = &g_dma2d_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!gfx_bitblt_check_dst_x(params, 32) ||
      !gfx_bitblt_check_src_x(params, 4)) {
    return false;
  }

  dma2d_wait();

  gfx_bitblt_t bb_copy = *params;
  gfx_bitblt_t* bb = &bb_copy;

  if (!dma2d_accessible(bb->dst_row) || !dma2d_accessible(bb->src_row)) {
    return false;
  }

  if (bb->src_x & 1) {
    // First column of mono4 bitmap is odd
    // Use the CPU to draw the first column
    dma2d_rgba8888_blend_mono4_first_col(bb);
    bb->dst_x += 1;
    bb->src_x += 1;
    bb->width -= 1;
  }

  if (bb->width > 0 && bb->width & 1) {
    // The width is odd
    // Use the CPU to draw the last column
    dma2d_rgba8888_blend_mono4_last_col(bb);
    bb->width -= 1;
  }

  if (bb->width > 0) {
    drv->handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
    drv->handle.Init.Mode = DMA2D_M2M_BLEND;
    drv->handle.Init.OutputOffset =
        bb->dst_stride / sizeof(uint32_t) - bb->width;
    HAL_DMA2D_Init(&drv->handle);

    drv->handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_L4;
    drv->handle.LayerCfg[1].InputOffset = bb->src_stride * 2 - bb->width;
    drv->handle.LayerCfg[1].AlphaMode = DMA2D_COMBINE_ALPHA;
    drv->handle.LayerCfg[1].InputAlpha = bb->src_alpha;
    HAL_DMA2D_ConfigLayer(&drv->handle, 1);

    dma2d_config_clut(
        1, gfx_color_to_color32(bb->src_fg),
        gfx_color32_set_alpha(gfx_color_to_color32(bb->src_fg), 0));

    drv->handle.LayerCfg[0].InputColorMode = DMA2D_INPUT_ARGB8888;
    drv->handle.LayerCfg[0].InputOffset =
        bb->dst_stride / sizeof(uint32_t) - bb->width;
    drv->handle.LayerCfg[0].AlphaMode = 0;
    drv->handle.LayerCfg[0].InputAlpha = 0;
    HAL_DMA2D_ConfigLayer(&drv->handle, 0);

    HAL_DMA2D_BlendingStart(
        &drv->handle, (uint32_t)bb->src_row + bb->src_x / 2,
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t), bb->width,
        bb->height);
  }

  return true;
}

bool dma2d_rgba8888_blend_mono8(const gfx_bitblt_t* bb) {
  dma2d_driver_t* drv = &g_dma2d_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!gfx_bitblt_check_dst_x(bb, 32) || !gfx_bitblt_check_src_x(bb, 8)) {
    return false;
  }

  dma2d_wait();

  if (!dma2d_accessible(bb->dst_row) || !dma2d_accessible(bb->src_row)) {
    return false;
  }

  uint32_t src_fg =
      gfx_color32_replace_a(gfx_color_to_color32(bb->src_fg), bb->src_alpha);

  drv->handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
  drv->handle.Init.Mode = DMA2D_M2M_BLEND;
  drv->handle.Init.OutputOffset = bb->dst_stride / sizeof(uint32_t) - bb->width;
  HAL_DMA2D_Init(&drv->handle);

  drv->handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_A8;
  drv->handle.LayerCfg[1].InputOffset = bb->src_stride - bb->width;
  drv->handle.LayerCfg[1].AlphaMode = DMA2D_COMBINE_ALPHA;
  drv->handle.LayerCfg[1].InputAlpha = src_fg;
  HAL_DMA2D_ConfigLayer(&drv->handle, 1);

  drv->handle.LayerCfg[0].InputColorMode = DMA2D_INPUT_ARGB8888;
  drv->handle.LayerCfg[0].InputOffset =
      bb->dst_stride / sizeof(uint32_t) - bb->width;
  drv->handle.LayerCfg[0].AlphaMode = 0;
  drv->handle.LayerCfg[0].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&drv->handle, 0);

  HAL_DMA2D_BlendingStart(&drv->handle, (uint32_t)bb->src_row + bb->src_x,
                          (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
                          (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
                          bb->width, bb->height);

  return true;
}

bool dma2d_rgba8888_copy_mono8(const gfx_bitblt_t* bb) {
  dma2d_driver_t* drv = &g_dma2d_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!gfx_bitblt_check_dst_x(bb, 32) || !gfx_bitblt_check_src_x(bb, 8)) {
    return false;
  }

  dma2d_wait();

  if (!dma2d_accessible(bb->dst_row) || !dma2d_accessible(bb->src_row)) {
    return false;
  }

  drv->handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
  drv->handle.Init.Mode = DMA2D_M2M_PFC;
  drv->handle.Init.OutputOffset = bb->dst_stride / sizeof(uint32_t) - bb->width;
  HAL_DMA2D_Init(&drv->handle);

  drv->handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_A8;
  drv->handle.LayerCfg[1].InputOffset = bb->src_stride - bb->width;
  drv->handle.LayerCfg[1].AlphaMode = 0;
  drv->handle.LayerCfg[1].InputAlpha = gfx_color_to_color32(bb->src_fg);
  HAL_DMA2D_ConfigLayer(&drv->handle, 1);

  HAL_DMA2D_Start(&drv->handle, (uint32_t)bb->src_row + bb->src_x,
                  (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
                  bb->width, bb->height);

  return true;
}

bool dma2d_rgba8888_copy_rgba8888(const gfx_bitblt_t* bb) {
  dma2d_driver_t* drv = &g_dma2d_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!gfx_bitblt_check_dst_x(bb, 32) || !gfx_bitblt_check_src_x(bb, 32)) {
    return false;
  }

  dma2d_wait();

  if (!dma2d_accessible(bb->dst_row) || !dma2d_accessible(bb->src_row)) {
    return false;
  }

  if (bb->src_downscale > 0) {
    return false;
  }

  drv->handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
  drv->handle.Init.Mode = DMA2D_M2M_PFC;
  drv->handle.Init.OutputOffset = bb->dst_stride / sizeof(uint32_t) - bb->width;
  HAL_DMA2D_Init(&drv->handle);

  drv->handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_ARGB8888;
  drv->handle.LayerCfg[1].InputOffset =
      bb->src_stride / sizeof(uint32_t) - bb->width;
  drv->handle.LayerCfg[1].AlphaMode = 0;
  drv->handle.LayerCfg[1].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&drv->handle, 1);

  HAL_DMA2D_Start(&drv->handle,
                  (uint32_t)bb->src_row + bb->src_x * sizeof(uint32_t),
                  (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
                  bb->width, bb->height);
  return true;
}

#ifdef USE_HW_JPEG_DECODER
static bool dma2d_rgba8888_copy_ycbcr(const gfx_bitblt_t* bb, uint32_t css) {
  dma2d_driver_t* drv = &g_dma2d_driver;

  if (!drv->initialized) {
    return false;
  }

  if (!gfx_bitblt_check_dst_x(bb, 32)) {
    return false;
  }

  dma2d_wait();

  if (!dma2d_accessible(bb->dst_row) || !dma2d_accessible(bb->src_row)) {
    return false;
  }

  drv->handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
  drv->handle.Init.Mode = DMA2D_M2M_PFC;
  drv->handle.Init.OutputOffset = bb->dst_stride / sizeof(uint32_t) - bb->width;
  HAL_DMA2D_Init(&drv->handle);

  drv->handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_YCBCR;
  drv->handle.LayerCfg[1].InputOffset = 0;
  drv->handle.LayerCfg[1].ChromaSubSampling = css;
  drv->handle.LayerCfg[1].AlphaMode = 0;
  drv->handle.LayerCfg[1].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&drv->handle, 1);

  HAL_DMA2D_Start(&drv->handle, (uint32_t)bb->src_row,
                  (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
                  bb->width, bb->height);

  // DMA2D overwrites CLUT during YCbCr conversion
  // (seems to be a bug or an undocumented feature)
  drv->clut_valid = false;

  return true;
}

bool dma2d_rgba8888_copy_ycbcr420(const gfx_bitblt_t* bb) {
  return dma2d_rgba8888_copy_ycbcr(bb, DMA2D_CSS_420);
}

bool dma2d_rgba8888_copy_ycbcr422(const gfx_bitblt_t* bb) {
  return dma2d_rgba8888_copy_ycbcr(bb, DMA2D_CSS_422);
}

bool dma2d_rgba8888_copy_ycbcr444(const gfx_bitblt_t* bb) {
  return dma2d_rgba8888_copy_ycbcr(bb, DMA2D_NO_CSS);
}

bool dma2d_rgba8888_copy_y(const gfx_bitblt_t* bb) {
  gfx_bitblt_t bb_copy = *bb;

  if (bb->height % 8 != 0 || bb->width % 8 != 0) {
    return false;
  }

  // src cotains only Y channel organized in 8x8 blocks

  bb_copy.height = 8;
  bb_copy.width = 8;
  bb_copy.src_stride = 8;
  bb_copy.src_fg = gfx_color_rgb(255, 255, 255);

  for (uint16_t y = 0; y < bb->height; y += 8) {
    bb_copy.dst_x = 0;
    for (uint16_t x = 0; x < bb->width; x += 8) {
      if (!dma2d_rgba8888_copy_mono8(&bb_copy)) {
        return false;
      }
      bb_copy.dst_x += 8;
      bb_copy.src_row = (uint8_t*)bb_copy.src_row + 64;
    }
    bb_copy.dst_y += 8;
  }
  return true;
}

#endif  // USE_HW_JPEG_DECODER

#endif  // KERNEL_MODE
