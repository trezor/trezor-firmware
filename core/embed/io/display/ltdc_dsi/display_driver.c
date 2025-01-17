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

#ifdef KERNEL_MODE

#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/systick.h>

#ifdef USE_BACKLIGHT
#include "../backlight/backlight_pwm.h"
#endif

#include "display_internal.h"

display_driver_t g_display_driver = {
    .initialized = false,
};

static void display_pll_deinit(void) { __HAL_RCC_PLL3_DISABLE(); }

static bool display_pll_init(void) {
  RCC_PeriphCLKInitTypeDef PLL3InitPeriph = {0};

  /* Start and configure PLL3 */
  /* HSE = 16/32MHZ */
  /* 16/32/(M=8)   = 4MHz input (min) */
  /* 4*(N=125)  = 500MHz VCO (almost max) */
  /* 500/(P=8)  = 62.5 for DSI ie exactly the lane byte clock*/

  PLL3InitPeriph.PeriphClockSelection = RCC_PERIPHCLK_DSI | RCC_PERIPHCLK_LTDC;
  PLL3InitPeriph.DsiClockSelection = RCC_DSICLKSOURCE_PLL3;
  PLL3InitPeriph.LtdcClockSelection = RCC_LTDCCLKSOURCE_PLL3;
#if HSE_VALUE == 32000000
  PLL3InitPeriph.PLL3.PLL3M = 8;
#elif HSE_VALUE == 16000000
  PLL3InitPeriph.PLL3.PLL3M = 4;
#endif
  PLL3InitPeriph.PLL3.PLL3N = 125;
  PLL3InitPeriph.PLL3.PLL3P = 8;
  PLL3InitPeriph.PLL3.PLL3Q = 8;
  PLL3InitPeriph.PLL3.PLL3R = 24;
  PLL3InitPeriph.PLL3.PLL3FRACN = 0;
  PLL3InitPeriph.PLL3.PLL3RGE = RCC_PLLVCIRANGE_0;
  PLL3InitPeriph.PLL3.PLL3ClockOut = RCC_PLL3_DIVR | RCC_PLL3_DIVP;
  PLL3InitPeriph.PLL3.PLL3Source = RCC_PLLSOURCE_HSE;

  if (HAL_RCCEx_PeriphCLKConfig(&PLL3InitPeriph) != HAL_OK) {
    goto cleanup;
  }

  return true;

cleanup:
  display_pll_deinit();
  return false;
}

static void display_dsi_deinit(display_driver_t *drv) {
  __HAL_RCC_DSI_CLK_DISABLE();
  __HAL_RCC_DSI_FORCE_RESET();
  __HAL_RCC_DSI_RELEASE_RESET();
  memset(&drv->hlcd_dsi, 0, sizeof(drv->hlcd_dsi));
}

static bool display_dsi_init(display_driver_t *drv) {
  RCC_PeriphCLKInitTypeDef DSIPHYInitPeriph = {0};
  DSI_PLLInitTypeDef PLLInit = {0};
  DSI_PHY_TimerTypeDef PhyTimers = {0};
  DSI_HOST_TimeoutTypeDef HostTimeouts = {0};

  __HAL_RCC_DSI_FORCE_RESET();
  __HAL_RCC_DSI_RELEASE_RESET();

  /* Enable DSI clock */
  __HAL_RCC_DSI_CLK_ENABLE();

  /* Switch to D-PHY source clock */
  /* Enable the DSI host */
  drv->hlcd_dsi.Instance = DSI;

  __HAL_DSI_ENABLE(&drv->hlcd_dsi);

  /* Enable the DSI PLL */
  __HAL_DSI_PLL_ENABLE(&drv->hlcd_dsi);

  HAL_Delay(1);

  /* Enable the clock lane and the digital section of the D-PHY   */
  drv->hlcd_dsi.Instance->PCTLR |= (DSI_PCTLR_CKE | DSI_PCTLR_DEN);

  /* Set the TX escape clock division factor */
  drv->hlcd_dsi.Instance->CCR = 4;

  HAL_Delay(1);

  /* Config DSI Clock to DSI PHY */
  DSIPHYInitPeriph.PeriphClockSelection = RCC_PERIPHCLK_DSI;
  DSIPHYInitPeriph.DsiClockSelection = RCC_DSICLKSOURCE_DSIPHY;

  if (HAL_RCCEx_PeriphCLKConfig(&DSIPHYInitPeriph) != HAL_OK) {
    goto cleanup;
  }

  /* Reset the TX escape clock division factor */
  drv->hlcd_dsi.Instance->CCR &= ~DSI_CCR_TXECKDIV;

  /* Disable the DSI PLL */
  __HAL_DSI_PLL_DISABLE(&drv->hlcd_dsi);

  /* Disable the DSI host */
  __HAL_DSI_DISABLE(&drv->hlcd_dsi);

  /* DSI initialization */
  drv->hlcd_dsi.Instance = DSI;
  drv->hlcd_dsi.Init.AutomaticClockLaneControl = DSI_AUTO_CLK_LANE_CTRL_DISABLE;
  /* We have 1 data lane at 500Mbps => lane byte clock at 500/8 = 62,5 MHZ */
  /* We want TX escape clock at around 20MHz and under 20MHz so clock division
   * is set to 4 */
  drv->hlcd_dsi.Init.TXEscapeCkdiv = 4;
  drv->hlcd_dsi.Init.NumberOfLanes = PANEL_DSI_LANES;
  drv->hlcd_dsi.Init.PHYFrequencyRange = DSI_DPHY_FRANGE_450MHZ_510MHZ;
  drv->hlcd_dsi.Init.PHYLowPowerOffset = 0;

#if HSE_VALUE == 32000000
  PLLInit.PLLNDIV = 62;
#elif HSE_VALUE == 16000000
  PLLInit.PLLNDIV = 125;
#endif
  PLLInit.PLLIDF = 4;
  PLLInit.PLLODF = 2;
  PLLInit.PLLVCORange = DSI_DPHY_VCO_FRANGE_800MHZ_1GHZ;
  PLLInit.PLLChargePump = DSI_PLL_CHARGE_PUMP_2000HZ_4400HZ;
  PLLInit.PLLTuning = DSI_PLL_LOOP_FILTER_2000HZ_4400HZ;

  if (HAL_DSI_Init(&drv->hlcd_dsi, &PLLInit) != HAL_OK) {
    goto cleanup;
  }
  if (HAL_DSI_SetGenericVCID(&drv->hlcd_dsi, 0) != HAL_OK) {
    goto cleanup;
  }

  /* Configure the DSI for Video mode */
  drv->DSIVidCfg.VirtualChannelID = 0;
  drv->DSIVidCfg.HSPolarity = DSI_HSYNC_ACTIVE_HIGH;
  drv->DSIVidCfg.VSPolarity = DSI_VSYNC_ACTIVE_HIGH;
  drv->DSIVidCfg.DEPolarity = DSI_DATA_ENABLE_ACTIVE_HIGH;
  drv->DSIVidCfg.ColorCoding = DSI_RGB888;
  drv->DSIVidCfg.Mode = PANEL_DSI_MODE;
  drv->DSIVidCfg.PacketSize = LCD_WIDTH;
  drv->DSIVidCfg.NullPacketSize = 0xFFFU;
  drv->DSIVidCfg.HorizontalSyncActive = HSYNC * 3;
  drv->DSIVidCfg.HorizontalBackPorch = HBP * 3;
  drv->DSIVidCfg.HorizontalLine = (HACT + HSYNC + HBP + HFP) * 3;
  drv->DSIVidCfg.VerticalSyncActive = VSYNC;
  drv->DSIVidCfg.VerticalBackPorch = VBP;
  drv->DSIVidCfg.VerticalFrontPorch = VFP;
  drv->DSIVidCfg.VerticalActive = VACT;
  drv->DSIVidCfg.LPCommandEnable = DSI_LP_COMMAND_ENABLE;
  drv->DSIVidCfg.LPLargestPacketSize = 64;
  /* Specify for each region of the video frame, if the transmission of command
   * in LP mode is allowed in this region */
  /* while streaming is active in video mode */
  drv->DSIVidCfg.LPHorizontalFrontPorchEnable = DSI_LP_HFP_ENABLE;
  drv->DSIVidCfg.LPHorizontalBackPorchEnable = DSI_LP_HBP_ENABLE;
  drv->DSIVidCfg.LPVerticalActiveEnable = DSI_LP_VACT_ENABLE;
  drv->DSIVidCfg.LPVerticalFrontPorchEnable = DSI_LP_VFP_ENABLE;
  drv->DSIVidCfg.LPVerticalBackPorchEnable = DSI_LP_VBP_ENABLE;
  drv->DSIVidCfg.LPVerticalSyncActiveEnable = DSI_LP_VSYNC_ENABLE;
  drv->DSIVidCfg.FrameBTAAcknowledgeEnable = DSI_FBTAA_ENABLE;
  drv->DSIVidCfg.LooselyPacked = DSI_LOOSELY_PACKED_DISABLE;

  /* Drive the display */
  if (HAL_DSI_ConfigVideoMode(&drv->hlcd_dsi, &drv->DSIVidCfg) != HAL_OK) {
    goto cleanup;
  }

  /*********************/
  /* LCD configuration */
  /*********************/
  PhyTimers.ClockLaneHS2LPTime = 11;
  PhyTimers.ClockLaneLP2HSTime = 40;
  PhyTimers.DataLaneHS2LPTime = 12;
  PhyTimers.DataLaneLP2HSTime = 23;
  PhyTimers.DataLaneMaxReadTime = 0;
  PhyTimers.StopWaitTime = 7;

  if (HAL_DSI_ConfigPhyTimer(&drv->hlcd_dsi, &PhyTimers)) {
    goto cleanup;
  }

  HostTimeouts.TimeoutCkdiv = 1;
  HostTimeouts.HighSpeedTransmissionTimeout = 0;
  HostTimeouts.LowPowerReceptionTimeout = 0;
  HostTimeouts.HighSpeedReadTimeout = 0;
  HostTimeouts.LowPowerReadTimeout = 0;
  HostTimeouts.HighSpeedWriteTimeout = 0;
  HostTimeouts.HighSpeedWritePrespMode = 0;
  HostTimeouts.LowPowerWriteTimeout = 0;
  HostTimeouts.BTATimeout = 0;

  if (HAL_DSI_ConfigHostTimeouts(&drv->hlcd_dsi, &HostTimeouts) != HAL_OK) {
    goto cleanup;
  }

  if (HAL_DSI_ConfigFlowControl(&drv->hlcd_dsi, DSI_FLOW_CONTROL_BTA) !=
      HAL_OK) {
    goto cleanup;
  }

  // The LTDC clock must be disabled before enabling the DSI host.
  // If the LTDC clock remains enabled, the display colors may appear
  // incorrectly or randomly swapped.
  __HAL_RCC_LTDC_CLK_DISABLE();

  /* Enable the DSI host */
  __HAL_DSI_ENABLE(&drv->hlcd_dsi);

  return true;

cleanup:
  display_dsi_deinit(drv);
  return false;
}

static bool display_ltdc_config_layer(LTDC_HandleTypeDef *hltdc,
                                      uint32_t fb_addr) {
  LTDC_LayerCfgTypeDef LayerCfg = {0};

  /* LTDC layer configuration */
  LayerCfg.WindowX0 = LCD_X_OFFSET;
  LayerCfg.WindowX1 = DISPLAY_RESX + LCD_X_OFFSET;
  LayerCfg.WindowY0 = LCD_Y_OFFSET;
  LayerCfg.WindowY1 = DISPLAY_RESY + LCD_Y_OFFSET;
  LayerCfg.PixelFormat = PANEL_LTDC_PIXEL_FORMAT;
  LayerCfg.Alpha = 0xFF; /* NU default value */
  LayerCfg.Alpha0 = 0;   /* NU default value */
  LayerCfg.BlendingFactor1 =
      LTDC_BLENDING_FACTOR1_PAxCA; /* Not Used: default value */
  LayerCfg.BlendingFactor2 =
      LTDC_BLENDING_FACTOR2_PAxCA; /* Not Used: default value */
  LayerCfg.FBStartAdress = fb_addr;
  LayerCfg.ImageWidth =
      FRAME_BUFFER_PIXELS_PER_LINE; /* Number of pixels per line in virtual
                                       frame buffer */
  LayerCfg.ImageHeight = LCD_HEIGHT;
  LayerCfg.Backcolor.Red = 0;   /* Not Used: default value */
  LayerCfg.Backcolor.Green = 0; /* Not Used: default value */
  LayerCfg.Backcolor.Blue = 0;  /* Not Used: default value */
  LayerCfg.Backcolor.Reserved = 0xFF;
  return HAL_LTDC_ConfigLayer(hltdc, &LayerCfg, LTDC_LAYER_1) == HAL_OK;
}

void display_ltdc_deinit(display_driver_t *drv) {
  __HAL_RCC_LTDC_CLK_DISABLE();
  __HAL_RCC_LTDC_FORCE_RESET();
  __HAL_RCC_LTDC_RELEASE_RESET();
}

static bool display_ltdc_init(display_driver_t *drv, uint32_t fb_addr) {
  __HAL_RCC_LTDC_FORCE_RESET();
  __HAL_RCC_LTDC_RELEASE_RESET();

  __HAL_RCC_LTDC_CLK_ENABLE();

  /* LTDC initialization */
  drv->hlcd_ltdc.Instance = LTDC;
  drv->hlcd_ltdc.Init.HSPolarity = LTDC_HSPOLARITY_AL;
  drv->hlcd_ltdc.Init.VSPolarity = LTDC_VSPOLARITY_AL;
  drv->hlcd_ltdc.Init.DEPolarity = LTDC_DEPOLARITY_AL;
  drv->hlcd_ltdc.Init.PCPolarity = LTDC_PCPOLARITY_IPC;
  drv->hlcd_ltdc.Init.HorizontalSync = HSYNC - 1;
  drv->hlcd_ltdc.Init.AccumulatedHBP = HSYNC + HBP - 1;
  drv->hlcd_ltdc.Init.AccumulatedActiveW = HACT + HBP + HSYNC - 1;
  drv->hlcd_ltdc.Init.TotalWidth = HACT + HBP + HFP + HSYNC - 1;
  drv->hlcd_ltdc.Init.Backcolor.Red = 0;   /* Not used default value */
  drv->hlcd_ltdc.Init.Backcolor.Green = 0; /* Not used default value */
  drv->hlcd_ltdc.Init.Backcolor.Blue = 0;  /* Not used default value */
  drv->hlcd_ltdc.Init.Backcolor.Reserved = 0xFF;

  if (HAL_LTDCEx_StructInitFromVideoConfig(&drv->hlcd_ltdc, &drv->DSIVidCfg) !=
      HAL_OK) {
    goto cleanup;
  }

  if (HAL_LTDC_Init(&drv->hlcd_ltdc) != HAL_OK) {
    goto cleanup;
  }

  if (!display_ltdc_config_layer(&drv->hlcd_ltdc, fb_addr)) {
    goto cleanup;
  }

  return true;

cleanup:
  display_ltdc_deinit(drv);
  return false;
}

bool display_set_fb(uint32_t fb_addr) {
  display_driver_t *drv = &g_display_driver;
  return display_ltdc_config_layer(&drv->hlcd_ltdc, fb_addr);
}

// This implementation does not support `mode` parameter, it
// behaves as if `mode` is always `DISPLAY_RESET_CONTENT`.
bool display_init(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (drv->initialized) {
    return true;
  }

  GPIO_InitTypeDef GPIO_InitStructure = {0};

#ifdef DISPLAY_PWREN_PIN
  DISPLAY_PWREN_CLK_ENA();
  HAL_GPIO_WritePin(DISPLAY_PWREN_PORT, DISPLAY_PWREN_PIN, GPIO_PIN_RESET);
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
  GPIO_InitStructure.Pin = DISPLAY_PWREN_PIN;
  HAL_GPIO_Init(DISPLAY_PWREN_PORT, &GPIO_InitStructure);
#endif

#ifdef DISPLAY_RESET_PIN
  DISPLAY_RESET_CLK_ENA();
  HAL_GPIO_WritePin(GPIOE, DISPLAY_RESET_PIN, GPIO_PIN_RESET);
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
  GPIO_InitStructure.Pin = DISPLAY_RESET_PIN;
  HAL_GPIO_Init(DISPLAY_RESET_PORT, &GPIO_InitStructure);

  systick_delay_ms(10);
  HAL_GPIO_WritePin(DISPLAY_RESET_PORT, DISPLAY_RESET_PIN, GPIO_PIN_SET);
  systick_delay_ms(120);
#endif

#ifdef DISPLAY_BACKLIGHT_PIN
  DISPLAY_BACKLIGHT_CLK_ENABLE();
  /* Configure LCD Backlight Pin */
  GPIO_InitStructure.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure.Pull = GPIO_PULLUP;
  GPIO_InitStructure.Pin = DISPLAY_BACKLIGHT_PIN;
  GPIO_InitStructure.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(DISPLAY_BACKLIGHT_PORT, &GPIO_InitStructure);
#endif

#ifdef USE_BACKLIGHT
  backlight_pwm_init(BACKLIGHT_RESET);
#endif

  uint32_t fb_addr = display_fb_init();

#ifdef DISPLAY_GFXMMU
  display_gfxmmu_init(drv);
#endif

  if (!display_pll_init()) {
    goto cleanup;
  }
  if (!display_dsi_init(drv)) {
    goto cleanup;
  }
  if (!display_ltdc_init(drv, fb_addr)) {
    goto cleanup;
  }

  /* Start DSI */
  if (HAL_DSI_Start(&drv->hlcd_dsi) != HAL_OK) {
    goto cleanup;
  }

  if (!panel_init(drv)) {
    goto cleanup;
  }

  if (HAL_LTDC_ProgramLineEvent(&drv->hlcd_ltdc, LCD_HEIGHT) != HAL_OK) {
    goto cleanup;
  }

  /* Enable LTDC interrupt */
  NVIC_SetPriority(LTDC_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(LTDC_IRQn);

  NVIC_SetPriority(LTDC_ER_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(LTDC_ER_IRQn);

  __HAL_LTDC_ENABLE_IT(&drv->hlcd_ltdc, LTDC_IT_LI | LTDC_IT_FU | LTDC_IT_TE);

  gfx_bitblt_init();

  drv->initialized = true;
  return true;

cleanup:
  display_deinit(DISPLAY_RESET_CONTENT);
  return false;
}

// This implementation does not support `mode` parameter, it
// behaves as if `mode` is always `DISPLAY_RESET_CONTENT`.
void display_deinit(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (mode == DISPLAY_RETAIN_CONTENT) {
    // This is a temporary workaround for T3W1 to avoid clearing
    // the display after drawing RSOD screen in `secure_shutdown()`
    // function. The workaround should be removed once we have
    // proper replacement for `secure_shutdown()` that resets the
    // device instead of waiting for manual power off.
    return;
  }

  GPIO_InitTypeDef GPIO_InitStructure = {0};

  gfx_bitblt_deinit();

  NVIC_DisableIRQ(LTDC_IRQn);
  NVIC_DisableIRQ(LTDC_ER_IRQn);

#ifdef DISPLAY_BACKLIGHT_PIN
  GPIO_InitStructure.Mode = GPIO_MODE_ANALOG;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
  GPIO_InitStructure.Pin = DISPLAY_BACKLIGHT_PIN;
  HAL_GPIO_Init(DISPLAY_BACKLIGHT_PORT, &GPIO_InitStructure);
#endif

#ifdef USE_BACKLIGHT
  backlight_pwm_deinit(BACKLIGHT_RESET);
#endif

  display_dsi_deinit(drv);
  display_ltdc_deinit(drv);
#ifdef DISPLAY_GFXMMU
  display_gfxmmu_deinit(drv);
#endif
  display_pll_deinit();

#ifdef DISPLAY_PWREN_PIN
  // Release PWREN pin and switch display power off
  GPIO_InitStructure.Mode = GPIO_MODE_ANALOG;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
  GPIO_InitStructure.Pin = DISPLAY_PWREN_PIN;
  HAL_GPIO_Init(DISPLAY_PWREN_PORT, &GPIO_InitStructure);
#endif

#ifdef DISPLAY_RESET_PIN
  // Release the RESET pin
  GPIO_InitStructure.Mode = GPIO_MODE_ANALOG;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
  GPIO_InitStructure.Pin = DISPLAY_RESET_PIN;
  HAL_GPIO_Init(DISPLAY_RESET_PORT, &GPIO_InitStructure);
#endif

  memset(drv, 0, sizeof(display_driver_t));
}

int display_set_backlight(int level) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }

#ifdef USE_BACKLIGHT
  if (level > backlight_pwm_get()) {
    display_ensure_refreshed();
  }

  return backlight_pwm_set(level);
#else
  // Just emulation, not doing anything
  drv->backlight_level = level;
  return level;
#endif
}

int display_get_backlight(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }
#ifdef USE_BACKLIGHT
  return backlight_pwm_get();
#else
  return drv->backlight_level;
#endif
}

int display_set_orientation(int angle) { return angle; }

int display_get_orientation(void) { return 0; }

void LTDC_IRQHandler(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mode = mpu_reconfig(MPU_MODE_DEFAULT);

  display_driver_t *drv = &g_display_driver;

  if (drv->hlcd_ltdc.State != HAL_LTDC_STATE_RESET) {
    HAL_LTDC_IRQHandler(&drv->hlcd_ltdc);
  } else {
    LTDC->ICR = 0x3F;
  }

  mpu_restore(mode);
  IRQ_LOG_EXIT();
}

void LTDC_ER_IRQHandler(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mode = mpu_reconfig(MPU_MODE_DEFAULT);

  display_driver_t *drv = &g_display_driver;

  if (drv->hlcd_ltdc.State != HAL_LTDC_STATE_RESET) {
    HAL_LTDC_IRQHandler(&drv->hlcd_ltdc);
  } else {
    LTDC->ICR = 0x3F;
  }

  mpu_restore(mode);
  IRQ_LOG_EXIT();
}

#endif
