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

#include STM32_HAL_H

#include <stddef.h>
#include "dma2d.h"

#include "../gdc/gdc_color.h"

static DMA2D_HandleTypeDef dma2d_handle = {
    .Instance = (DMA2D_TypeDef*)DMA2D_BASE,
};

bool dma2d_accessible(const void* ptr) {
  // TODO:: valid only for STM32F42x
  const void* ccm_start = (const void*)0x10000000;
  const void* ccm_end = (const void*)0x1000FFFF;
  return !(ptr >= ccm_start && ptr <= ccm_end);
}

void dma2d_wait(void) {
  while (HAL_DMA2D_PollForTransfer(&dma2d_handle, 10) != HAL_OK)
    ;
}

bool dma2d_rgb565_fill(const dma2d_params_t* dp) {
  dma2d_wait();

  if (dp->src_alpha == 255) {
    dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
    dma2d_handle.Init.Mode = DMA2D_R2M;
    dma2d_handle.Init.OutputOffset =
        dp->dst_stride / sizeof(uint16_t) - dp->width;
    HAL_DMA2D_Init(&dma2d_handle);

    HAL_DMA2D_Start(&dma2d_handle, gdc_color_to_color32(dp->src_fg),
                    (uint32_t)dp->dst_row + dp->dst_x * sizeof(uint16_t),
                    dp->width, dp->height);
  } else {
    // STM32F4 can not accelerate blending with the fixed color
    uint16_t* dst_ptr = (uint16_t*)dp->dst_row + dp->dst_x;
    uint16_t height = dp->height;
    uint8_t alpha = dp->src_alpha;
    while (height-- > 0) {
      for (int x = 0; x < dp->width; x++) {
        dst_ptr[x] = gdc_color16_blend_a8(dp->src_fg, dst_ptr[x], alpha);
      }
      dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
    }
  }

  return true;
}

/*
static void dma2d_config_clut(uint32_t layer, gdc_color_t fg, gdc_color_t bg) {

  #define LAYER_COUNT 2
  #define GRADIENT_STEPS 16

  static struct {
    gdc_color32_t gradient[GRADIENT_STEPS];
  } cache[LAYER_COUNT] = { 0 };

  if (layer >= LAYER_COUNT) {
    return;
  }

  uint32_t c_fg = gdc_color_to_color32(fg);
  uint32_t c_bg = gdc_color_to_color32(bg);

  uint32_t* gradient = cache[layer].gradient;

  if (c_bg != gradient[0] || c_fg != gradient[GRADIENT_STEPS - 1]) {
     for (int step = 0; step < GRADIENT_STEPS; step++) {
       gradient[step] = gdc_color32_blend_a4(fg, bg, step);
     }

    DMA2D_CLUTCfgTypeDef clut;
    clut.CLUTColorMode = DMA2D_CCM_ARGB8888;
    clut.Size = GRADIENT_STEPS - 1;
    clut.pCLUT = gradient;

    HAL_DMA2D_ConfigCLUT(&dma2d_handle, clut, layer);

    while (HAL_DMA2D_PollForTransfer(&dma2d_handle, 10) != HAL_OK)
        ;
  }
}*/

static void dma2d_config_clut(uint32_t layer, gdc_color_t fg, gdc_color_t bg) {
#define LAYER_COUNT 2
#define GRADIENT_STEPS 16

  static struct {
    gdc_color_t c_fg;
    gdc_color_t c_bg;
  } cache[LAYER_COUNT] = {0};

  if (layer >= LAYER_COUNT) {
    return;
  }

  volatile uint32_t* clut =
      layer ? dma2d_handle.Instance->FGCLUT : dma2d_handle.Instance->BGCLUT;

  if (fg != cache[layer].c_fg || bg != cache[layer].c_bg) {
    cache[layer].c_fg = fg;
    cache[layer].c_bg = bg;

    for (int step = 0; step < GRADIENT_STEPS; step++) {
      clut[step] = gdc_color32_blend_a4(fg, bg, step);
    }

    DMA2D_CLUTCfgTypeDef clut;
    clut.CLUTColorMode = DMA2D_CCM_ARGB8888;
    clut.Size = GRADIENT_STEPS - 1;
    clut.pCLUT = 0;  // ???

    HAL_DMA2D_ConfigCLUT(&dma2d_handle, clut, layer);
  }
}

static void dma2d_rgb565_copy_mono4_first_col(dma2d_params_t* dp,
                                              const gdc_color16_t* gradient) {
  uint16_t* dst_ptr = (uint16_t*)dp->dst_row + dp->dst_x;
  uint8_t* src_ptr = (uint8_t*)dp->src_row + dp->src_x / 2;

  int height = dp->height;

  while (height-- > 0) {
    uint8_t fg_lum = src_ptr[0] >> 4;
    dst_ptr[0] = gradient[fg_lum];
    dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
    src_ptr += dp->src_stride / sizeof(*src_ptr);
  }
}

static void dma2d_rgb565_copy_mono4_last_col(dma2d_params_t* dp,
                                             const gdc_color16_t* gradient) {
  uint16_t* dst_ptr = (uint16_t*)dp->dst_row + (dp->dst_x + dp->width - 1);
  uint8_t* src_ptr = (uint8_t*)dp->src_row + (dp->src_x + dp->width - 1) / 2;

  int height = dp->height;

  while (height-- > 0) {
    uint8_t fg_lum = src_ptr[0] & 0x0F;
    dst_ptr[0] = gradient[fg_lum];
    dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
    src_ptr += dp->src_stride / sizeof(*src_ptr);
  }
}

bool dma2d_rgb565_copy_mono4(const dma2d_params_t* params) {
  const gdc_color16_t* src_gradient = NULL;

  dma2d_params_t dp_copy = *params;
  dma2d_params_t* dp = &dp_copy;

  dma2d_wait();

  if (dp->src_x & 1) {
    // First column of mono4 bitmap is odd
    // Use the CPU to draw the first column
    src_gradient = gdc_color16_gradient_a4(dp->src_fg, dp->src_bg);
    dma2d_rgb565_copy_mono4_first_col(dp, src_gradient);
    dp->dst_x += 1;
    dp->src_x += 1;
    dp->width -= 1;
  }

  if (dp->width > 0 && dp->width & 1) {
    // The width is odd
    // Use the CPU to draw the last column
    if (src_gradient == NULL) {
      src_gradient = gdc_color16_gradient_a4(dp->src_fg, dp->src_bg);
    }
    dma2d_rgb565_copy_mono4_last_col(dp, src_gradient);
    dp->width -= 1;
  }

  dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
  dma2d_handle.Init.Mode = DMA2D_M2M_PFC;
  dma2d_handle.Init.OutputOffset =
      dp->dst_stride / sizeof(uint16_t) - dp->width;
  HAL_DMA2D_Init(&dma2d_handle);

  dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_L4;
  dma2d_handle.LayerCfg[1].InputOffset = dp->src_stride * 2 - dp->width;
  dma2d_handle.LayerCfg[1].AlphaMode = 0;
  dma2d_handle.LayerCfg[1].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);

  dma2d_config_clut(1, dp->src_fg, dp->src_bg);

  HAL_DMA2D_Start(&dma2d_handle, (uint32_t)dp->src_row + dp->src_x / 2,
                  (uint32_t)dp->dst_row + dp->dst_x * sizeof(uint16_t),
                  dp->width, dp->height);

  return true;
}

bool dma2d_rgb565_copy_rgb565(const dma2d_params_t* dp) {
  dma2d_wait();

  dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
  dma2d_handle.Init.Mode = DMA2D_M2M_PFC;
  dma2d_handle.Init.OutputOffset =
      dp->dst_stride / sizeof(uint16_t) - dp->width;
  HAL_DMA2D_Init(&dma2d_handle);

  dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_RGB565;
  dma2d_handle.LayerCfg[1].InputOffset =
      dp->src_stride / sizeof(uint16_t) - dp->width;
  dma2d_handle.LayerCfg[1].AlphaMode = 0;
  dma2d_handle.LayerCfg[1].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);

  HAL_DMA2D_Start(&dma2d_handle,
                  (uint32_t)dp->src_row + dp->src_x * sizeof(uint16_t),
                  (uint32_t)dp->dst_row + dp->dst_x * sizeof(uint16_t),
                  dp->width, dp->height);

  return true;
}

static void dma2d_rgb565_blend_mono4_first_col(const dma2d_params_t* dp) {
  uint16_t* dst_ptr = (uint16_t*)dp->dst_row + dp->dst_x;
  uint8_t* src_ptr = (uint8_t*)dp->src_row + dp->src_x / 2;

  int height = dp->height;

  while (height-- > 0) {
    uint8_t fg_alpha = src_ptr[0] >> 4;
    dst_ptr[0] = gdc_color16_blend_a4(
        dp->src_fg, gdc_color16_to_color(dst_ptr[0]), fg_alpha);
    dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
    src_ptr += dp->src_stride / sizeof(*src_ptr);
  }
}

static void dma2d_rgb565_blend_mono4_last_col(const dma2d_params_t* dp) {
  uint16_t* dst_ptr = (uint16_t*)dp->dst_row + (dp->dst_x + dp->width - 1);
  uint8_t* src_ptr = (uint8_t*)dp->src_row + (dp->src_x + dp->width - 1) / 2;

  int height = dp->height;

  while (height-- > 0) {
    uint8_t fg_alpha = src_ptr[0] & 0x0F;
    dst_ptr[0] = gdc_color16_blend_a4(
        dp->src_fg, gdc_color16_to_color(dst_ptr[0]), fg_alpha);
    dst_ptr += dp->dst_stride / sizeof(*dst_ptr);
    src_ptr += dp->src_stride / sizeof(*src_ptr);
  }
}

bool dma2d_rgb565_blend_mono4(const dma2d_params_t* params) {
  dma2d_wait();

  dma2d_params_t dp_copy = *params;
  dma2d_params_t* dp = &dp_copy;

  if (dp->src_x & 1) {
    // First column of mono4 bitmap is odd
    // Use the CPU to draw the first column
    dma2d_rgb565_blend_mono4_first_col(dp);
    dp->dst_x += 1;
    dp->src_x += 1;
    dp->width -= 1;
  }

  if (dp->width > 0 && dp->width & 1) {
    // The width is odd
    // Use the CPU to draw the last column
    dma2d_rgb565_blend_mono4_last_col(dp);
    dp->width -= 1;
  }

  if (dp->width > 0) {
    dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
    dma2d_handle.Init.Mode = DMA2D_M2M_BLEND;
    dma2d_handle.Init.OutputOffset =
        dp->dst_stride / sizeof(uint16_t) - dp->width;
    HAL_DMA2D_Init(&dma2d_handle);

    dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_A4;
    dma2d_handle.LayerCfg[1].InputOffset = dp->src_stride * 2 - dp->width;
    dma2d_handle.LayerCfg[1].AlphaMode = 0;
    dma2d_handle.LayerCfg[1].InputAlpha = gdc_color_to_color32(dp->src_fg);
    HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);

    dma2d_handle.LayerCfg[0].InputColorMode = DMA2D_INPUT_RGB565;
    dma2d_handle.LayerCfg[0].InputOffset =
        dp->dst_stride / sizeof(uint16_t) - dp->width;
    dma2d_handle.LayerCfg[0].AlphaMode = 0;
    dma2d_handle.LayerCfg[0].InputAlpha = 0;
    HAL_DMA2D_ConfigLayer(&dma2d_handle, 0);

    HAL_DMA2D_BlendingStart(
        &dma2d_handle, (uint32_t)dp->src_row + dp->src_x / 2,
        (uint32_t)dp->dst_row + dp->dst_x * sizeof(uint16_t),
        (uint32_t)dp->dst_row + dp->dst_x * sizeof(uint16_t), dp->width,
        dp->height);
  }

  return true;
}
