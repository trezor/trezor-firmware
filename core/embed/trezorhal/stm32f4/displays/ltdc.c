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
#include TREZOR_BOARD
#include "display_interface.h"
#include "memzero.h"
#include STM32_HAL_H

#include "ili9341_spi.h"
#include "sdram.h"

#define MAX_LAYER_NUMBER 2
#define LCD_FRAME_BUFFER ((uint32_t)SDRAM_DEVICE_ADDR)

LTDC_HandleTypeDef LtdcHandler;
static RCC_PeriphCLKInitTypeDef PeriphClkInitStruct;

/* Default LCD configuration with LCD Layer 1 */
uint32_t ActiveLayer = 0;
// static LCD_DrawPropTypeDef DrawProp[MAX_LAYER_NUMBER];
// LCD_DrvTypeDef  *LcdDrv;

static int DISPLAY_BACKLIGHT = -1;
static int DISPLAY_ORIENTATION = -1;

// this is just for compatibility with DMA2D using algorithms
uint8_t *const DISPLAY_DATA_ADDRESS = 0;

uint16_t cursor_x = 0;
uint16_t cursor_y = 0;
uint16_t window_x0 = 0;
uint16_t window_y0 = MAX_DISPLAY_RESX - 1;
uint16_t window_x1 = 0;
uint16_t window_y1 = MAX_DISPLAY_RESY - 1;

void display_pixeldata(uint16_t c) {
  ((uint16_t *)LCD_FRAME_BUFFER)[(cursor_y * MAX_DISPLAY_RESX) + cursor_x] = c;

  cursor_x++;

  if (cursor_x > window_x1) {
    cursor_x = window_x0;
    cursor_y++;

    if (cursor_y > window_y1) {
      cursor_y = window_y0;
    }
  }
}

void display_pixeldata_dirty(void) {}

void display_reset_state() {}

static void __attribute__((unused)) display_sleep(void) {}

static void display_unsleep(void) {}

/**
 * @brief  Initializes the LCD layers.
 * @param  LayerIndex: the layer foreground or background.
 * @param  FB_Address: the layer frame buffer.
 */
void BSP_LCD_LayerDefaultInit(uint16_t LayerIndex, uint32_t FB_Address) {
  LTDC_LayerCfgTypeDef Layercfg;

  /* Layer Init */
  Layercfg.WindowX0 = 0;
  Layercfg.WindowX1 = MAX_DISPLAY_RESX;
  Layercfg.WindowY0 = 0;
  Layercfg.WindowY1 = MAX_DISPLAY_RESY;
  Layercfg.PixelFormat = LTDC_PIXEL_FORMAT_RGB565;
  Layercfg.FBStartAdress = FB_Address;
  Layercfg.Alpha = 255;
  Layercfg.Alpha0 = 0;
  Layercfg.Backcolor.Blue = 0;
  Layercfg.Backcolor.Green = 0;
  Layercfg.Backcolor.Red = 0;
  Layercfg.BlendingFactor1 = LTDC_BLENDING_FACTOR1_PAxCA;
  Layercfg.BlendingFactor2 = LTDC_BLENDING_FACTOR2_PAxCA;
  Layercfg.ImageWidth = MAX_DISPLAY_RESX;
  Layercfg.ImageHeight = MAX_DISPLAY_RESY;

  HAL_LTDC_ConfigLayer(&LtdcHandler, &Layercfg, LayerIndex);

  //  DrawProp[LayerIndex].BackColor = LCD_COLOR_WHITE;
  //  DrawProp[LayerIndex].pFont     = &Font24;
  //  DrawProp[LayerIndex].TextColor = LCD_COLOR_BLACK;

  /* Dithering activation */
  HAL_LTDC_EnableDither(&LtdcHandler);
}

/**
 * @brief  Selects the LCD Layer.
 * @param  LayerIndex: the Layer foreground or background.
 */
void BSP_LCD_SelectLayer(uint32_t LayerIndex) { ActiveLayer = LayerIndex; }

/**
 * @brief  Sets a LCD Layer visible.
 * @param  LayerIndex: the visible Layer.
 * @param  state: new state of the specified layer.
 *    This parameter can be: ENABLE or DISABLE.
 */
void BSP_LCD_SetLayerVisible(uint32_t LayerIndex, FunctionalState state) {
  if (state == ENABLE) {
    __HAL_LTDC_LAYER_ENABLE(&LtdcHandler, LayerIndex);
  } else {
    __HAL_LTDC_LAYER_DISABLE(&LtdcHandler, LayerIndex);
  }
  __HAL_LTDC_RELOAD_CONFIG(&LtdcHandler);
}

/**
 * @brief  Sets an LCD Layer visible without reloading.
 * @param  LayerIndex: Visible Layer
 * @param  State: New state of the specified layer
 *          This parameter can be one of the following values:
 *            @arg  ENABLE
 *            @arg  DISABLE
 * @retval None
 */
void BSP_LCD_SetLayerVisible_NoReload(uint32_t LayerIndex,
                                      FunctionalState State) {
  if (State == ENABLE) {
    __HAL_LTDC_LAYER_ENABLE(&LtdcHandler, LayerIndex);
  } else {
    __HAL_LTDC_LAYER_DISABLE(&LtdcHandler, LayerIndex);
  }
  /* Do not Sets the Reload  */
}

/**
 * @brief  Configures the Transparency.
 * @param  LayerIndex: the Layer foreground or background.
 * @param  Transparency: the Transparency,
 *    This parameter must range from 0x00 to 0xFF.
 */
void BSP_LCD_SetTransparency(uint32_t LayerIndex, uint8_t Transparency) {
  HAL_LTDC_SetAlpha(&LtdcHandler, Transparency, LayerIndex);
}

/**
 * @brief  Configures the transparency without reloading.
 * @param  LayerIndex: Layer foreground or background.
 * @param  Transparency: Transparency
 *           This parameter must be a number between Min_Data = 0x00 and
 * Max_Data = 0xFF
 * @retval None
 */
void BSP_LCD_SetTransparency_NoReload(uint32_t LayerIndex,
                                      uint8_t Transparency) {
  HAL_LTDC_SetAlpha_NoReload(&LtdcHandler, Transparency, LayerIndex);
}

/**
 * @brief  Sets a LCD layer frame buffer address.
 * @param  LayerIndex: specifies the Layer foreground or background
 * @param  Address: new LCD frame buffer value
 */
void BSP_LCD_SetLayerAddress(uint32_t LayerIndex, uint32_t Address) {
  HAL_LTDC_SetAddress(&LtdcHandler, Address, LayerIndex);
}

/**
 * @brief  Sets an LCD layer frame buffer address without reloading.
 * @param  LayerIndex: Layer foreground or background
 * @param  Address: New LCD frame buffer value
 * @retval None
 */
void BSP_LCD_SetLayerAddress_NoReload(uint32_t LayerIndex, uint32_t Address) {
  HAL_LTDC_SetAddress_NoReload(&LtdcHandler, Address, LayerIndex);
}

// static struct { uint16_t x, y; } BUFFER_OFFSET;

void display_set_window(uint16_t x0, uint16_t y0, uint16_t x1, uint16_t y1) {
  window_x0 = x0;
  window_x1 = x1;
  window_y0 = y0;
  window_y1 = y1;
  cursor_x = x0;
  cursor_y = y0;

  //    /* Reconfigure the layer size */
  //    HAL_LTDC_SetWindowSize_NoReload(&LtdcHandler, x1-x0 + 1, y1-y0 + 1, 0);
  //
  //    /* Reconfigure the layer position */
  //    HAL_LTDC_SetWindowPosition_NoReload(&LtdcHandler, x0, y0, 0);
}

int display_orientation(int degrees) { return 0; }

int display_get_orientation(void) { return DISPLAY_ORIENTATION; }

int display_backlight(int val) {
  if (DISPLAY_BACKLIGHT != val && val >= 0 && val <= 255) {
    DISPLAY_BACKLIGHT = val;
    // TIM1->CCR1 = LED_PWM_TIM_PERIOD * val / 255;
  }
  return DISPLAY_BACKLIGHT;
}

void display_init_seq(void) { display_unsleep(); }

void display_init(void) {
  GPIO_InitTypeDef GPIO_InitStructure;

  /* Enable the LTDC and DMA2D Clock */
  __HAL_RCC_LTDC_CLK_ENABLE();
  __HAL_RCC_DMA2D_CLK_ENABLE();

  /* Enable GPIOs clock */
  __HAL_RCC_GPIOA_CLK_ENABLE();
  __HAL_RCC_GPIOB_CLK_ENABLE();
  __HAL_RCC_GPIOC_CLK_ENABLE();
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOF_CLK_ENABLE();
  __HAL_RCC_GPIOG_CLK_ENABLE();

  /* GPIOs Configuration */
  /*
   +------------------------+-----------------------+----------------------------+
   +                       LCD pins assignment +
   +------------------------+-----------------------+----------------------------+
   |  LCD_TFT R2 <-> PC.10  |  LCD_TFT G2 <-> PA.06 |  LCD_TFT B2 <-> PD.06 | |
   LCD_TFT R3 <-> PB.00  |  LCD_TFT G3 <-> PG.10 |  LCD_TFT B3 <-> PG.11      |
   |  LCD_TFT R4 <-> PA.11  |  LCD_TFT G4 <-> PB.10 |  LCD_TFT B4 <-> PG.12 | |
   LCD_TFT R5 <-> PA.12  |  LCD_TFT G5 <-> PB.11 |  LCD_TFT B5 <-> PA.03      |
   |  LCD_TFT R6 <-> PB.01  |  LCD_TFT G6 <-> PC.07 |  LCD_TFT B6 <-> PB.08 | |
   LCD_TFT R7 <-> PG.06  |  LCD_TFT G7 <-> PD.03 |  LCD_TFT B7 <-> PB.09      |
   -------------------------------------------------------------------------------
            |  LCD_TFT HSYNC <-> PC.06  | LCDTFT VSYNC <->  PA.04 |
            |  LCD_TFT CLK   <-> PG.07  | LCD_TFT DE   <->  PF.10 |
             -----------------------------------------------------
  */

  /* GPIOA configuration */
  GPIO_InitStructure.Pin =
      GPIO_PIN_3 | GPIO_PIN_4 | GPIO_PIN_6 | GPIO_PIN_11 | GPIO_PIN_12;
  GPIO_InitStructure.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_FAST;
  GPIO_InitStructure.Alternate = GPIO_AF14_LTDC;
  HAL_GPIO_Init(GPIOA, &GPIO_InitStructure);

  /* GPIOB configuration */
  GPIO_InitStructure.Pin = GPIO_PIN_8 | GPIO_PIN_9 | GPIO_PIN_10 | GPIO_PIN_11;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);

  /* GPIOC configuration */
  GPIO_InitStructure.Pin = GPIO_PIN_6 | GPIO_PIN_7 | GPIO_PIN_10;
  HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);

  /* GPIOD configuration */
  GPIO_InitStructure.Pin = GPIO_PIN_3 | GPIO_PIN_6;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);

  /* GPIOF configuration */
  GPIO_InitStructure.Pin = GPIO_PIN_10;
  HAL_GPIO_Init(GPIOF, &GPIO_InitStructure);

  /* GPIOG configuration */
  GPIO_InitStructure.Pin = GPIO_PIN_6 | GPIO_PIN_7 | GPIO_PIN_11;
  HAL_GPIO_Init(GPIOG, &GPIO_InitStructure);

  /* GPIOB configuration */
  GPIO_InitStructure.Pin = GPIO_PIN_0 | GPIO_PIN_1;
  GPIO_InitStructure.Alternate = GPIO_AF9_LTDC;
  HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);

  /* GPIOG configuration */
  GPIO_InitStructure.Pin = GPIO_PIN_10 | GPIO_PIN_12;
  HAL_GPIO_Init(GPIOG, &GPIO_InitStructure);

  /* On STM32F429I-DISCO, it is not possible to read ILI9341 ID because */
  /* PIN EXTC is not connected to VDD and then LCD_READ_ID4 is not accessible.
   */
  /* In this case, ReadID function is bypassed.*/
  /*if(ili9341_drv.ReadID() == ILI9341_ID)*/

  /* LTDC Configuration ----------------------------------------------------*/
  LtdcHandler.Instance = LTDC;

  /* Timing configuration  (Typical configuration from ILI9341 datasheet)
        HSYNC=10 (9+1)
        HBP=20 (29-10+1)
        ActiveW=240 (269-20-10+1)
        HFP=10 (279-240-20-10+1)

        VSYNC=2 (1+1)
        VBP=2 (3-2+1)
        ActiveH=320 (323-2-2+1)
        VFP=4 (327-320-2-2+1)
    */

  /* Configure horizontal synchronization width */
  LtdcHandler.Init.HorizontalSync = ILI9341_HSYNC;
  /* Configure vertical synchronization height */
  LtdcHandler.Init.VerticalSync = ILI9341_VSYNC;
  /* Configure accumulated horizontal back porch */
  LtdcHandler.Init.AccumulatedHBP = ILI9341_HBP;
  /* Configure accumulated vertical back porch */
  LtdcHandler.Init.AccumulatedVBP = ILI9341_VBP;
  /* Configure accumulated active width */
  LtdcHandler.Init.AccumulatedActiveW = 269;
  /* Configure accumulated active height */
  LtdcHandler.Init.AccumulatedActiveH = 323;
  /* Configure total width */
  LtdcHandler.Init.TotalWidth = 279;
  /* Configure total height */
  LtdcHandler.Init.TotalHeigh = 327;

  /* Configure R,G,B component values for LCD background color */
  LtdcHandler.Init.Backcolor.Red = 0;
  LtdcHandler.Init.Backcolor.Blue = 0;
  LtdcHandler.Init.Backcolor.Green = 0;

  /* LCD clock configuration */
  /* PLLSAI_VCO Input = HSE_VALUE/PLL_M = 1 Mhz */
  /* PLLSAI_VCO Output = PLLSAI_VCO Input * PLLSAIN = 192 Mhz */
  /* PLLLCDCLK = PLLSAI_VCO Output/PLLSAIR = 192/4 = 48 Mhz */
  /* LTDC clock frequency = PLLLCDCLK / LTDC_PLLSAI_DIVR_8 = 48/4 = 6Mhz */
  PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_LTDC;
  PeriphClkInitStruct.PLLSAI.PLLSAIN = 192;
  PeriphClkInitStruct.PLLSAI.PLLSAIR = 4;
  PeriphClkInitStruct.PLLSAIDivR = RCC_PLLSAIDIVR_8;
  HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct);

  /* Polarity */
  LtdcHandler.Init.HSPolarity = LTDC_HSPOLARITY_AL;
  LtdcHandler.Init.VSPolarity = LTDC_VSPOLARITY_AL;
  LtdcHandler.Init.DEPolarity = LTDC_DEPOLARITY_AL;
  LtdcHandler.Init.PCPolarity = LTDC_PCPOLARITY_IPC;

  HAL_LTDC_Init(&LtdcHandler);

  /* Initialize the LCD Layers */
  BSP_LCD_LayerDefaultInit(1, LCD_FRAME_BUFFER);

  memzero((void *)LCD_FRAME_BUFFER, 153600);

  ili9341_init();

  display_init_seq();
}

void display_reinit(void) {}

void display_refresh(void) {}

void display_sync(void) {}

const char *display_save(const char *prefix) { return NULL; }

void display_clear_save(void) {}

void display_efficient_clear(void) {
  memzero((void *)LCD_FRAME_BUFFER, 153600);
}

uint8_t *display_get_wr_addr(void) {
  uint32_t address = LCD_FRAME_BUFFER;
  /* Get the rectangle start address */
  address = (address + (2 * ((cursor_y)*MAX_DISPLAY_RESX + (cursor_x))));

  return (uint8_t *)address;
}

uint32_t *display_get_fb_addr(void) { return (uint32_t *)LCD_FRAME_BUFFER; }

uint16_t display_get_window_width(void) { return window_x1 - window_x0 + 1; }

uint16_t display_get_window_height(void) { return window_y1 - window_y0 + 1; }

void display_shift_window(uint16_t pixels) {
  uint16_t w = display_get_window_width();
  uint16_t h = display_get_window_height();

  uint16_t line_rem = w - (cursor_x - window_x0);

  if (pixels < line_rem) {
    cursor_x += pixels;
    return;
  }

  // start of next line
  pixels = pixels - line_rem;
  cursor_x = window_x0;
  cursor_y++;

  // add the rest of pixels
  cursor_y = window_y0 + (((cursor_y - window_y0) + (pixels / w)) % h);
  cursor_x += pixels % w;
}

uint16_t display_get_window_offset(void) {
  return MAX_DISPLAY_RESX - display_get_window_width();
}
