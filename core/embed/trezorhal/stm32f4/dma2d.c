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

#include "dma2d.h"
#include "colors.h"
#include STM32_HAL_H
#include "display_interface.h"

typedef enum {
  DMA2D_LAYER_FG = 1,
  DMA2D_LAYER_BG = 0,
} dma2d_layer_t;

static DMA2D_HandleTypeDef dma2d_handle = {0};
static uint16_t current_width = 0;
static uint16_t current_height = 0;

void dma2d_init(void) {
  __HAL_RCC_DMA2D_CLK_ENABLE();

  dma2d_handle.Instance = (DMA2D_TypeDef*)DMA2D_BASE;
  dma2d_handle.Init.ColorMode = DISPLAY_COLOR_MODE;
  dma2d_handle.Init.OutputOffset = 0;
}

static void dma2d_init_clut(uint16_t fg, uint16_t bg, dma2d_layer_t layer) {
  volatile uint32_t* table = NULL;
  if (layer == DMA2D_LAYER_BG) {
    table = dma2d_handle.Instance->BGCLUT;
  } else {
    table = dma2d_handle.Instance->FGCLUT;
  }

  uint32_t fg32 = rgb565_to_rgb888(fg);
  uint32_t bg32 = rgb565_to_rgb888(bg);

  for (uint8_t i = 0; i < 16; i++) {
    table[i] = interpolate_rgb888_color(fg32, bg32, i);
  }

  DMA2D_CLUTCfgTypeDef clut;
  clut.CLUTColorMode = DMA2D_CCM_ARGB8888;
  clut.Size = 0xf;
  clut.pCLUT = 0;  // loading directly

  HAL_DMA2D_ConfigCLUT(&dma2d_handle, clut, layer);
}

void dma2d_setup_const(void) {
  dma2d_handle.Init.Mode = DMA2D_R2M;
  dma2d_handle.Init.OutputOffset = display_get_window_offset();
  HAL_DMA2D_Init(&dma2d_handle);
}

void dma2d_setup_4bpp(uint16_t fg_color, uint16_t bg_color) {
  dma2d_handle.Init.Mode = DMA2D_M2M_PFC;
  dma2d_handle.Init.OutputOffset = display_get_window_offset();
  dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_L4;
  dma2d_handle.LayerCfg[1].InputOffset = 0;
  dma2d_handle.LayerCfg[1].AlphaMode = 0;
  dma2d_handle.LayerCfg[1].InputAlpha = 0;

  dma2d_init_clut(fg_color, bg_color, DMA2D_LAYER_FG);

  HAL_DMA2D_Init(&dma2d_handle);
  HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);
}

void dma2d_setup_16bpp(void) {
  dma2d_handle.Init.Mode = DMA2D_M2M_PFC;
  dma2d_handle.Init.OutputOffset = display_get_window_offset();
  dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_RGB565;
  dma2d_handle.LayerCfg[1].InputOffset = 0;
  dma2d_handle.LayerCfg[1].AlphaMode = 0;
  dma2d_handle.LayerCfg[1].InputAlpha = 0;

  HAL_DMA2D_Init(&dma2d_handle);
  HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);
}

void dma2d_setup_4bpp_over_16bpp(uint16_t overlay_color) {
  dma2d_handle.Init.Mode = DMA2D_M2M_BLEND;
  dma2d_handle.Init.OutputOffset = display_get_window_offset();
  dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_A4;
  dma2d_handle.LayerCfg[1].InputOffset = 0;
  dma2d_handle.LayerCfg[1].AlphaMode = 0;
  dma2d_handle.LayerCfg[1].InputAlpha =
      0xFF000000 | rgb565_to_rgb888(overlay_color);

  dma2d_handle.LayerCfg[0].InputColorMode = DMA2D_INPUT_RGB565;
  dma2d_handle.LayerCfg[0].InputOffset = 0;
  dma2d_handle.LayerCfg[0].AlphaMode = 0;
  dma2d_handle.LayerCfg[0].InputAlpha = 0;

  HAL_DMA2D_Init(&dma2d_handle);
  HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);
  HAL_DMA2D_ConfigLayer(&dma2d_handle, 0);
}

void dma2d_setup_4bpp_over_4bpp(uint16_t fg_color, uint16_t bg_color,
                                uint16_t overlay_color) {
  dma2d_handle.Init.Mode = DMA2D_M2M_BLEND;
  dma2d_handle.Init.OutputOffset = display_get_window_offset();
  dma2d_handle.LayerCfg[1].InputColorMode = DMA2D_INPUT_A4;
  dma2d_handle.LayerCfg[1].InputOffset = 0;
  dma2d_handle.LayerCfg[1].AlphaMode = 0;
  dma2d_handle.LayerCfg[1].InputAlpha = rgb565_to_rgb888(overlay_color);

  dma2d_handle.LayerCfg[0].InputColorMode = DMA2D_INPUT_L4;
  dma2d_handle.LayerCfg[0].InputOffset = 0;
  dma2d_handle.LayerCfg[0].AlphaMode = DMA2D_REPLACE_ALPHA;
  dma2d_handle.LayerCfg[0].InputAlpha = 0xFF;

  dma2d_init_clut(fg_color, bg_color, DMA2D_LAYER_BG);

  HAL_DMA2D_Init(&dma2d_handle);
  HAL_DMA2D_ConfigLayer(&dma2d_handle, 1);
  HAL_DMA2D_ConfigLayer(&dma2d_handle, 0);
}

void dma2d_start(uint8_t* in_addr, uint8_t* out_addr, int32_t pixels) {
  current_width = pixels;
  current_height = 1;
  HAL_DMA2D_Start(&dma2d_handle, (uint32_t)in_addr, (uint32_t)out_addr, pixels,
                  1);
}

void dma2d_start_const(uint16_t color, uint8_t* out_addr, int32_t pixels) {
  current_width = pixels;
  current_height = 1;
  HAL_DMA2D_Start(&dma2d_handle, rgb565_to_rgb888(color), (uint32_t)out_addr,
                  pixels, 1);
}

void dma2d_start_const_multiline(uint16_t color, uint8_t* out_addr,
                                 int32_t width, int32_t height) {
  current_width = width;
  current_height = height;
  HAL_DMA2D_Start(&dma2d_handle, rgb565_to_rgb888(color), (uint32_t)out_addr,
                  width, height);
}

void dma2d_start_blend(uint8_t* overlay_addr, uint8_t* bg_addr,
                       uint8_t* out_addr, int32_t pixels) {
  current_width = pixels;
  current_height = 1;
  HAL_DMA2D_BlendingStart(&dma2d_handle, (uint32_t)overlay_addr,
                          (uint32_t)bg_addr, (uint32_t)out_addr, pixels, 1);
}

void dma2d_wait_for_transfer(void) {
  while (HAL_DMA2D_PollForTransfer(&dma2d_handle, 10) != HAL_OK)
    ;
  display_shift_window(current_width * current_height);
  current_width = 0;
  current_height = 0;
}
