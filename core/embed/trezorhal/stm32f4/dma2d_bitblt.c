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

#include "dma2d_bitblt.h"
#include "gl_color.h"

static DMA2D_HandleTypeDef dma2d_handle = {
    .Instance = (DMA2D_TypeDef*)DMA2D_BASE,
};

bool dma2d_accessible(const void* ptr) {
#ifdef STM32F4
  const void* ccm_start = (const void*)0x10000000;
  const void* ccm_end = (const void*)0x1000FFFF;
  return !(ptr >= ccm_start && ptr <= ccm_end);
#else
  return true;
#endif
}

void dma2d_wait(void) {
  while (HAL_DMA2D_PollForTransfer(&dma2d_handle, 10) != HAL_OK)
    ;
}

void dma2d_rgb565_fill(const gl_bitblt_t* bb) {
  dma2d_wait();

  if (bb->src_alpha == 255) {
    dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
    dma2d_handle.Init.Mode = DMA2D_R2M;
    dma2d_handle.Init.OutputOffset =
        bb->dst_stride / sizeof(uint16_t) - bb->width;
    HAL_DMA2D_Init(&dma2d_handle);

    HAL_DMA2D_Start(&dma2d_handle, gl_color_to_color32(bb->src_fg),
                    (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t),
                    bb->width, bb->height);
    /*

        MODIFY_REG(dma2d_handle.Instance->CR, DMA2D_CR_MODE, DMA2D_R2M);
        MODIFY_REG(dma2d_handle.Instance->OPFCCR, DMA2D_OPFCCR_CM,
       DMA2D_OUTPUT_RGB565); MODIFY_REG(dma2d_handle.Instance->OOR,
       DMA2D_OOR_LO, bb->dst_stride / sizeof(uint16_t) - bb->width);
        MODIFY_REG(dma2d_handle.Instance->NLR, (DMA2D_NLR_NL|DMA2D_NLR_PL),
       (bb->height| (bb->width << 16))); WRITE_REG(dma2d_handle.Instance->OMAR,
       (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t));
        WRITE_REG(dma2d_handle.Instance->OCOLR,
       gl_color_to_color32(bb->src_fg));
         ((dma2d_handle).Instance->CR |= DMA2D_CR_START);
    */
  } else {
#ifdef STM32U5
    dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
    dma2d_handle.Init.Mode = DMA2D_M2M_BLEND_FG;
    dma2d_handle.Init.OutputOffset =
        bb->dst_stride / sizeof(uint16_t) - bb->width;
    HAL_DMA2D_Init(&dma2d_handle);

    dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_RGB565;
    dma2d_handle.LayerCfg[1].InputOffset = 0;
    dma2d_handle.LayerCfg[1].AlphaMode = DMA2D_REPLACE_ALPHA;
    dma2d_handle.LayerCfg[1].InputAlpha = bb->src_alpha;
    HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);

    dma2d_handle.LayerCfg[0].InputColorMode = DMA2D_INPUT_RGB565;
    dma2d_handle.LayerCfg[0].InputOffset =
        bb->dst_stride / sizeof(uint16_t) - bb->width;
    dma2d_handle.LayerCfg[0].AlphaMode = 0;
    dma2d_handle.LayerCfg[0].InputAlpha = 0;
    HAL_DMA2D_ConfigLayer(&dma2d_handle, 0);

    HAL_DMA2D_BlendingStart(
        &dma2d_handle, gl_color_to_color32(bb->src_fg),
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t),
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t), bb->width,
        bb->height);
#else
    // STM32F4 can not accelerate blending with the fixed color
    uint16_t* dst_ptr = (uint16_t*)bb->dst_row + bb->dst_x;
    uint16_t height = bb->height;
    uint8_t alpha = bb->src_alpha;
    while (height-- > 0) {
      for (int x = 0; x < bb->width; x++) {
        dst_ptr[x] = gl_color16_blend_a8(
            bb->src_fg, gl_color16_to_color(dst_ptr[x]), alpha);
      }
      dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    }
#endif
  }
}

/*
static void dma2d_config_clut(uint32_t layer, gl_color_t fg, gl_color_t bg) {

  #define LAYER_COUNT 2
  #define GRADIENT_STEPS 16

  static struct {
    gl_color32_t gradient[GRADIENT_STEPS];
  } cache[LAYER_COUNT] = { 0 };

  if (layer >= LAYER_COUNT) {
    return;
  }

  uint32_t c_fg = gl_color_to_color32(fg);
  uint32_t c_bg = gl_color_to_color32(bg);

  uint32_t* gradient = cache[layer].gradient;

  if (c_bg != gradient[0] || c_fg != gradient[GRADIENT_STEPS - 1]) {
     for (int step = 0; step < GRADIENT_STEPS; step++) {
       gradient[step] = gl_color32_blend_a4(fg, bg, step);
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

static void dma2d_config_clut(uint32_t layer, gl_color_t fg, gl_color_t bg) {
#define LAYER_COUNT 2
#define GRADIENT_STEPS 16

  static struct {
    gl_color_t c_fg;
    gl_color_t c_bg;
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
      clut[step] = gl_color32_blend_a4(fg, bg, step);
    }

    DMA2D_CLUTCfgTypeDef clut;
    clut.CLUTColorMode = DMA2D_CCM_ARGB8888;
    clut.Size = GRADIENT_STEPS - 1;
    clut.pCLUT = 0;  // ???

    HAL_DMA2D_ConfigCLUT(&dma2d_handle, clut, layer);
  }
}

static void dma2d_rgb565_copy_mono4_first_col(gl_bitblt_t* bb,
                                              const gl_color16_t* gradient) {
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

static void dma2d_rgb565_copy_mono4_last_col(gl_bitblt_t* bb,
                                             const gl_color16_t* gradient) {
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

void dma2d_rgb565_copy_mono4(const gl_bitblt_t* params) {
  const gl_color16_t* src_gradient = NULL;

  gl_bitblt_t bb_copy = *params;
  gl_bitblt_t* bb = &bb_copy;

  dma2d_wait();

  if (bb->src_x & 1) {
    // First column of mono4 bitmap is odd
    // Use the CPU to draw the first column
    src_gradient = gl_color16_gradient_a4(bb->src_fg, bb->src_bg);
    dma2d_rgb565_copy_mono4_first_col(bb, src_gradient);
    bb->dst_x += 1;
    bb->src_x += 1;
    bb->width -= 1;
  }

  if (bb->width > 0 && bb->width & 1) {
    // The width is odd
    // Use the CPU to draw the last column
    if (src_gradient == NULL) {
      src_gradient = gl_color16_gradient_a4(bb->src_fg, bb->src_bg);
    }
    dma2d_rgb565_copy_mono4_last_col(bb, src_gradient);
    bb->width -= 1;
  }

  dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
  dma2d_handle.Init.Mode = DMA2D_M2M_PFC;
  dma2d_handle.Init.OutputOffset =
      bb->dst_stride / sizeof(uint16_t) - bb->width;
  HAL_DMA2D_Init(&dma2d_handle);

  dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_L4;
  dma2d_handle.LayerCfg[1].InputOffset = bb->src_stride * 2 - bb->width;
  dma2d_handle.LayerCfg[1].AlphaMode = 0;
  dma2d_handle.LayerCfg[1].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);

  dma2d_config_clut(1, bb->src_fg, bb->src_bg);

  HAL_DMA2D_Start(&dma2d_handle, (uint32_t)bb->src_row + bb->src_x / 2,
                  (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t),
                  bb->width, bb->height);
}

void dma2d_rgb565_copy_rgb565(const gl_bitblt_t* bb) {
  dma2d_wait();

  dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
  dma2d_handle.Init.Mode = DMA2D_M2M_PFC;
  dma2d_handle.Init.OutputOffset =
      bb->dst_stride / sizeof(uint16_t) - bb->width;
  HAL_DMA2D_Init(&dma2d_handle);

  dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_RGB565;
  dma2d_handle.LayerCfg[1].InputOffset =
      bb->src_stride / sizeof(uint16_t) - bb->width;
  dma2d_handle.LayerCfg[1].AlphaMode = 0;
  dma2d_handle.LayerCfg[1].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);

  HAL_DMA2D_Start(&dma2d_handle,
                  (uint32_t)bb->src_row + bb->src_x * sizeof(uint16_t),
                  (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t),
                  bb->width, bb->height);
}

static void dma2d_rgb565_blend_mono4_first_col(const gl_bitblt_t* bb) {
  uint16_t* dst_ptr = (uint16_t*)bb->dst_row + bb->dst_x;
  uint8_t* src_ptr = (uint8_t*)bb->src_row + bb->src_x / 2;

  int height = bb->height;

  while (height-- > 0) {
    uint8_t fg_alpha = src_ptr[0] >> 4;
    dst_ptr[0] = gl_color16_blend_a4(bb->src_fg,
                                     gl_color16_to_color(dst_ptr[0]), fg_alpha);
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_ptr += bb->src_stride / sizeof(*src_ptr);
  }
}

static void dma2d_rgb565_blend_mono4_last_col(const gl_bitblt_t* bb) {
  uint16_t* dst_ptr = (uint16_t*)bb->dst_row + (bb->dst_x + bb->width - 1);
  uint8_t* src_ptr = (uint8_t*)bb->src_row + (bb->src_x + bb->width - 1) / 2;

  int height = bb->height;

  while (height-- > 0) {
    uint8_t fg_alpha = src_ptr[0] & 0x0F;
    dst_ptr[0] = gl_color16_blend_a4(bb->src_fg,
                                     gl_color16_to_color(dst_ptr[0]), fg_alpha);
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_ptr += bb->src_stride / sizeof(*src_ptr);
  }
}

void dma2d_rgb565_blend_mono4(const gl_bitblt_t* params) {
  dma2d_wait();

  gl_bitblt_t bb_copy = *params;
  gl_bitblt_t* bb = &bb_copy;

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
    dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_RGB565;
    dma2d_handle.Init.Mode = DMA2D_M2M_BLEND;
    dma2d_handle.Init.OutputOffset =
        bb->dst_stride / sizeof(uint16_t) - bb->width;
    HAL_DMA2D_Init(&dma2d_handle);

    dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_A4;
    dma2d_handle.LayerCfg[1].InputOffset = bb->src_stride * 2 - bb->width;
    dma2d_handle.LayerCfg[1].AlphaMode = 0;
    dma2d_handle.LayerCfg[1].InputAlpha = gl_color_to_color32(bb->src_fg);
    HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);

    dma2d_handle.LayerCfg[0].InputColorMode = DMA2D_INPUT_RGB565;
    dma2d_handle.LayerCfg[0].InputOffset =
        bb->dst_stride / sizeof(uint16_t) - bb->width;
    dma2d_handle.LayerCfg[0].AlphaMode = 0;
    dma2d_handle.LayerCfg[0].InputAlpha = 0;
    HAL_DMA2D_ConfigLayer(&dma2d_handle, 0);

    HAL_DMA2D_BlendingStart(
        &dma2d_handle, (uint32_t)bb->src_row + bb->src_x / 2,
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t),
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint16_t), bb->width,
        bb->height);
  }
}

void dma2d_rgba8888_fill(const gl_bitblt_t* bb) {
  dma2d_wait();

  if (bb->src_alpha == 255) {
    dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
    dma2d_handle.Init.Mode = DMA2D_R2M;
    dma2d_handle.Init.OutputOffset =
        bb->dst_stride / sizeof(uint32_t) - bb->width;
    HAL_DMA2D_Init(&dma2d_handle);

    HAL_DMA2D_Start(&dma2d_handle, gl_color_to_color32(bb->src_fg),
                    (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
                    bb->width, bb->height);
  } else {
#ifdef STM32U5
    dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
    dma2d_handle.Init.Mode = DMA2D_M2M_BLEND_FG;
    dma2d_handle.Init.OutputOffset =
        bb->dst_stride / sizeof(uint32_t) - bb->width;
    HAL_DMA2D_Init(&dma2d_handle);

    dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_ARGB8888;
    dma2d_handle.LayerCfg[1].InputOffset = 0;
    dma2d_handle.LayerCfg[1].AlphaMode = DMA2D_REPLACE_ALPHA;
    dma2d_handle.LayerCfg[1].InputAlpha = bb->src_alpha;
    HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);

    dma2d_handle.LayerCfg[0].InputColorMode = DMA2D_INPUT_ARGB8888;
    dma2d_handle.LayerCfg[0].InputOffset =
        bb->dst_stride / sizeof(uint32_t) - bb->width;
    dma2d_handle.LayerCfg[0].AlphaMode = 0;
    dma2d_handle.LayerCfg[0].InputAlpha = 0;
    HAL_DMA2D_ConfigLayer(&dma2d_handle, 0);

    HAL_DMA2D_BlendingStart(
        &dma2d_handle, gl_color_to_color32(bb->src_fg),
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t), bb->width,
        bb->height);
#else
    // STM32F4 can not accelerate blending with the fixed color
    uint32_t* dst_ptr = (uint32_t*)bb->dst_row + bb->dst_x;
    uint16_t height = bb->height;
    uint8_t alpha = bb->src_alpha;
    while (height-- > 0) {
      for (int x = 0; x < bb->width; x++) {
        dst_ptr[x] = gl_color32_blend_a8(
            bb->src_fg, gl_color32_to_color(dst_ptr[x]), alpha);
      }
      dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    }
#endif
  }
}

static void dma2d_rgba8888_copy_mono4_first_col(gl_bitblt_t* bb,
                                                const gl_color32_t* gradient) {
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

static void dma2d_rgba8888_copy_mono4_last_col(gl_bitblt_t* bb,
                                               const gl_color32_t* gradient) {
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

void dma2d_rgba8888_copy_mono4(const gl_bitblt_t* params) {
  const gl_color32_t* src_gradient = NULL;

  gl_bitblt_t bb_copy = *params;
  gl_bitblt_t* bb = &bb_copy;

  dma2d_wait();

  if (bb->src_x & 1) {
    // First column of mono4 bitmap is odd
    // Use the CPU to draw the first column
    src_gradient = gl_color32_gradient_a4(bb->src_fg, bb->src_bg);
    dma2d_rgba8888_copy_mono4_first_col(bb, src_gradient);
    bb->dst_x += 1;
    bb->src_x += 1;
    bb->width -= 1;
  }

  if (bb->width > 0 && bb->width & 1) {
    // The width is odd
    // Use the CPU to draw the last column
    if (src_gradient == NULL) {
      src_gradient = gl_color32_gradient_a4(bb->src_fg, bb->src_bg);
    }
    dma2d_rgba8888_copy_mono4_last_col(bb, src_gradient);
    bb->width -= 1;
  }

  dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
  dma2d_handle.Init.Mode = DMA2D_M2M_PFC;
  dma2d_handle.Init.OutputOffset =
      bb->dst_stride / sizeof(uint32_t) - bb->width;
  HAL_DMA2D_Init(&dma2d_handle);

  dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_L4;
  dma2d_handle.LayerCfg[1].InputOffset = bb->src_stride * 2 - bb->width;
  dma2d_handle.LayerCfg[1].AlphaMode = 0;
  dma2d_handle.LayerCfg[1].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);

  dma2d_config_clut(1, bb->src_fg, bb->src_bg);

  HAL_DMA2D_Start(&dma2d_handle, (uint32_t)bb->src_row + bb->src_x / 2,
                  (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
                  bb->width, bb->height);
}

void dma2d_rgba8888_copy_rgb565(const gl_bitblt_t* bb) {
  dma2d_wait();

  dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
  dma2d_handle.Init.Mode = DMA2D_M2M_PFC;
  dma2d_handle.Init.OutputOffset =
      bb->dst_stride / sizeof(uint32_t) - bb->width;
  HAL_DMA2D_Init(&dma2d_handle);

  dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_RGB565;
  dma2d_handle.LayerCfg[1].InputOffset =
      bb->src_stride / sizeof(uint16_t) - bb->width;
  dma2d_handle.LayerCfg[1].AlphaMode = 0;
  dma2d_handle.LayerCfg[1].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);

  HAL_DMA2D_Start(&dma2d_handle,
                  (uint32_t)bb->src_row + bb->src_x * sizeof(uint16_t),
                  (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
                  bb->width, bb->height);
}

static void dma2d_rgba8888_blend_mono4_first_col(const gl_bitblt_t* bb) {
  uint32_t* dst_ptr = (uint32_t*)bb->dst_row + bb->dst_x;
  uint8_t* src_ptr = (uint8_t*)bb->src_row + bb->src_x / 2;

  int height = bb->height;

  while (height-- > 0) {
    uint8_t fg_alpha = src_ptr[0] >> 4;
    dst_ptr[0] = gl_color32_blend_a4(bb->src_fg,
                                     gl_color32_to_color(dst_ptr[0]), fg_alpha);
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_ptr += bb->src_stride / sizeof(*src_ptr);
  }
}

static void dma2d_rgba8888_blend_mono4_last_col(const gl_bitblt_t* bb) {
  uint32_t* dst_ptr = (uint32_t*)bb->dst_row + (bb->dst_x + bb->width - 1);
  uint8_t* src_ptr = (uint8_t*)bb->src_row + (bb->src_x + bb->width - 1) / 2;

  int height = bb->height;

  while (height-- > 0) {
    uint8_t fg_alpha = src_ptr[0] & 0x0F;
    dst_ptr[0] = gl_color32_blend_a4(bb->src_fg,
                                     gl_color32_to_color(dst_ptr[0]), fg_alpha);
    dst_ptr += bb->dst_stride / sizeof(*dst_ptr);
    src_ptr += bb->src_stride / sizeof(*src_ptr);
  }
}

void dma2d_rgba8888_blend_mono4(const gl_bitblt_t* params) {
  dma2d_wait();

  gl_bitblt_t bb_copy = *params;
  gl_bitblt_t* bb = &bb_copy;

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
    dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
    dma2d_handle.Init.Mode = DMA2D_M2M_BLEND;
    dma2d_handle.Init.OutputOffset =
        bb->dst_stride / sizeof(uint32_t) - bb->width;
    HAL_DMA2D_Init(&dma2d_handle);

    dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_A4;
    dma2d_handle.LayerCfg[1].InputOffset = bb->src_stride * 2 - bb->width;
    dma2d_handle.LayerCfg[1].AlphaMode = 0;
    dma2d_handle.LayerCfg[1].InputAlpha = gl_color_to_color32(bb->src_fg);
    HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);

    dma2d_handle.LayerCfg[0].InputColorMode = DMA2D_INPUT_ARGB8888;
    dma2d_handle.LayerCfg[0].InputOffset =
        bb->dst_stride / sizeof(uint32_t) - bb->width;
    dma2d_handle.LayerCfg[0].AlphaMode = 0;
    dma2d_handle.LayerCfg[0].InputAlpha = 0;
    HAL_DMA2D_ConfigLayer(&dma2d_handle, 0);

    HAL_DMA2D_BlendingStart(
        &dma2d_handle, (uint32_t)bb->src_row + bb->src_x / 2,
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
        (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t), bb->width,
        bb->height);
  }
}

void dma2d_rgba8888_copy_rgba8888(const gl_bitblt_t* bb) {
  dma2d_wait();

  dma2d_handle.Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
  dma2d_handle.Init.Mode = DMA2D_M2M_PFC;
  dma2d_handle.Init.OutputOffset =
      bb->dst_stride / sizeof(uint32_t) - bb->width;
  HAL_DMA2D_Init(&dma2d_handle);

  dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_ARGB8888;
  dma2d_handle.LayerCfg[1].InputOffset =
      bb->src_stride / sizeof(uint32_t) - bb->width;
  dma2d_handle.LayerCfg[1].AlphaMode = 0;
  dma2d_handle.LayerCfg[1].InputAlpha = 0;
  HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);

  HAL_DMA2D_Start(&dma2d_handle,
                  (uint32_t)bb->src_row + bb->src_x * sizeof(uint32_t),
                  (uint32_t)bb->dst_row + bb->dst_x * sizeof(uint32_t),
                  bb->width, bb->height);
}
