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
#include <io/backlight.h>
#endif

#include "display_internal.h"

#if REFRESH_RATE_SCALING_SUPPORTED
// VFP lookup table for different refresh rates
static const uint32_t vfp_lut[REFRESH_RATE_COUNT] = {
    [REFRESH_RATE_HI] = VFP_REFRESH_RATE_HI,
    [REFRESH_RATE_LO] = VFP_REFRESH_RATE_LO,
};
#endif

display_driver_t g_display_driver = {
    .initialized = false,
};

static void display_pll_deinit(void) { __HAL_RCC_PLL3_DISABLE(); }

static bool display_pll_init(void) {
  /* Start and configure PLL3 */
  __HAL_RCC_PLL3_DISABLE();

  while (__HAL_RCC_GET_FLAG(RCC_FLAG_PLL3RDY) != 0U)
    ;

  __HAL_RCC_PLL3_CONFIG(RCC_PLLSOURCE_HSE, PLL3_M, PLL3_N, PLL3_P, PLL3_Q,
                        PLL3_R);

  __HAL_RCC_PLL3_VCIRANGE(RCC_PLLVCIRANGE_0);

  __HAL_RCC_PLL3CLKOUT_ENABLE(RCC_PLL3_DIVR | RCC_PLL3_DIVP);

  __HAL_RCC_PLL3FRACN_DISABLE();

  __HAL_RCC_PLL3_ENABLE();

  /* Wait till PLL3 is ready */
  while (__HAL_RCC_GET_FLAG(RCC_FLAG_PLL3RDY) == 0U)
    ;

  __HAL_RCC_DSI_CONFIG(RCC_DSICLKSOURCE_PLL3);
  __HAL_RCC_LTDC_CONFIG(RCC_LTDCCLKSOURCE_PLL3);

  return true;
}

static void display_dsi_deinit(display_driver_t *drv) {
  __HAL_RCC_DSI_CLK_DISABLE();
  __HAL_RCC_DSI_FORCE_RESET();
  __HAL_RCC_DSI_RELEASE_RESET();
  memset(&drv->hlcd_dsi, 0, sizeof(drv->hlcd_dsi));
}

static bool display_dsi_init(display_driver_t *drv) {
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
  __HAL_RCC_DSI_CONFIG(RCC_DSICLKSOURCE_DSIPHY);

  /* Reset the TX escape clock division factor */
  drv->hlcd_dsi.Instance->CCR &= ~DSI_CCR_TXECKDIV;

  /* Disable the DSI PLL */
  __HAL_DSI_PLL_DISABLE(&drv->hlcd_dsi);

  /* Disable the DSI host */
  __HAL_DSI_DISABLE(&drv->hlcd_dsi);

  /* DSI initialization */
  drv->hlcd_dsi.Instance = DSI;
  // Erratum "DSI automatic clock lane control not functional" =>
  // it can't be enabled.
  drv->hlcd_dsi.Init.AutomaticClockLaneControl = DSI_AUTO_CLK_LANE_CTRL_DISABLE;
  drv->hlcd_dsi.Init.TXEscapeCkdiv = DSI_TX_ESCAPE_CLK_DIV;
  drv->hlcd_dsi.Init.NumberOfLanes = PANEL_DSI_LANES;
  drv->hlcd_dsi.Init.PHYFrequencyRange = DSI_DPHY_FRANGE;
  drv->hlcd_dsi.Init.PHYLowPowerOffset = PHY_LP_OFFSET;

  PLLInit.PLLIDF = PLL_DSI_IDF;
  PLLInit.PLLNDIV = PLL_DSI_NDIV;
  PLLInit.PLLODF = PLL_DSI_ODF;
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
  drv->DSIVidCfg.ColorCoding = PANEL_DSI_COLOR_CODING;
  drv->DSIVidCfg.Mode = PANEL_DSI_MODE;
  // In burst mode, the packet size must be greater or equal to the visible
  // width.
  drv->DSIVidCfg.PacketSize = HACT;
  drv->DSIVidCfg.NumberOfChunks = 0;  // No chunks in burst mode
  drv->DSIVidCfg.NullPacketSize = 0;  // No null packet in burst mode
  drv->DSIVidCfg.HorizontalSyncActive = HSYNC * LANE_BYTE_2_PIXEL_CLK_RATIO;
  drv->DSIVidCfg.HorizontalBackPorch = HBP * LANE_BYTE_2_PIXEL_CLK_RATIO;
  drv->DSIVidCfg.HorizontalLine =
      (HSYNC + HBP + HACT + HFP) * LANE_BYTE_2_PIXEL_CLK_RATIO;
  drv->DSIVidCfg.VerticalSyncActive = VSYNC;
  drv->DSIVidCfg.VerticalBackPorch = VBP;
  drv->DSIVidCfg.VerticalFrontPorch = VFP;
  drv->DSIVidCfg.VerticalActive = VACT;
  drv->DSIVidCfg.LPCommandEnable = DSI_LP_COMMAND_ENABLE;
  drv->DSIVidCfg.LPLargestPacketSize = 64;
  // Enable entering LP in all regions if timing constraints allow it.
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

  // RM0456 Table 445. HS2LP and LP2HS values vs. band frequency (MHz)
  PhyTimers.ClockLaneHS2LPTime = PHY_TIMER_CLK_HS2LP;
  PhyTimers.ClockLaneLP2HSTime = PHY_TIMER_CLK_LP2HS;
  PhyTimers.DataLaneHS2LPTime = PHY_TIMER_DATA_HS2LP;
  PhyTimers.DataLaneLP2HSTime = PHY_TIMER_DATA_LP2HS;
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
  drv->hlcd_ltdc.Init.AccumulatedActiveW = HSYNC + HBP + HACT - 1;
  drv->hlcd_ltdc.Init.TotalWidth = HSYNC + HBP + HACT + HFP - 1;
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
static bool display_init_ll(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

#ifdef DISPLAY_RESET_PIN
  // Toggle the RESET pin
  HAL_GPIO_WritePin(DISPLAY_RESET_PORT, DISPLAY_RESET_PIN, GPIO_PIN_RESET);
  systick_delay_ms(10);
  HAL_GPIO_WritePin(DISPLAY_RESET_PORT, DISPLAY_RESET_PIN, GPIO_PIN_SET);
  systick_delay_ms(120);
#endif  // DISPLAY_RESET_PIN

#ifdef USE_BACKLIGHT
  backlight_init(BACKLIGHT_RESET, GAMMA_EXP);
#endif

  uint32_t fb_addr = display_fb_init();

#ifdef DISPLAY_GFXMMU
  display_gfxmmu_init(drv);
#endif

  if (!display_pll_init()) {
    return false;
  }
  if (!display_dsi_init(drv)) {
    return false;
  }
  if (!display_ltdc_init(drv, fb_addr)) {
    return false;
  }

  /* Start DSI */
  if (HAL_DSI_Start(&drv->hlcd_dsi) != HAL_OK) {
    return false;
  }

  if (!panel_init(drv)) {
    return false;
  }

  if (HAL_LTDC_ProgramLineEvent(&drv->hlcd_ltdc, LINE_EVENT_GENERAL_LINE) !=
      HAL_OK) {
    return false;
  }

  /* Enable LTDC interrupt */
  NVIC_SetPriority(LTDC_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(LTDC_IRQn);

  NVIC_SetPriority(LTDC_ER_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(LTDC_ER_IRQn);

  __HAL_LTDC_ENABLE_IT(&drv->hlcd_ltdc, LTDC_IT_LI | LTDC_IT_FU | LTDC_IT_TE);

  gfx_bitblt_init();

  // Workaround to avoid a wrong image display for 1st refresh rate change.
  // It has been observed that the first change of the refresh rate after
  // initialization causes improper display update. Disabling and re-enabling
  // the LTDC and DSI seems to solve the issue.
  //
  // TODO: review the configuration sequence of the LTDC and DSI to avoid this.
  // See RM0456 44.14.1 Programing procedure overview
  __HAL_LTDC_DISABLE(&drv->hlcd_ltdc);
  __HAL_DSI_DISABLE(&drv->hlcd_dsi);

  __HAL_DSI_ENABLE(&drv->hlcd_dsi);
  __HAL_LTDC_ENABLE(&drv->hlcd_ltdc);
  // Workaround end.

#if REFRESH_RATE_SCALING_SUPPORTED
  // No need to lock IRQs here because the "drv->initialized" flag is not set
  // yet.
  drv->refresh_rate_state = REFRESH_RATE_IDLE;
  drv->refresh_rate = REFRESH_RATE_HI;
  // Set the timeout variable to return to the low refresh rate after the
  // "REFRESH_RATE_HI2LO_TIMEOUT_MS" time of inactivity.
  drv->refresh_rate_timeout_ms = ticks_timeout(REFRESH_RATE_HI2LO_TIMEOUT_MS);
  drv->refresh_rate_timeout_set = true;
#endif

  return true;
}

// This implementation does not support `mode` parameter, it
// behaves as if `mode` is always `DISPLAY_RESET_CONTENT`.
bool display_init(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  if (drv->initialized) {
    return true;
  }

#ifdef DISPLAY_PWREN_PIN
  {
    GPIO_InitTypeDef GPIO_InitStructure = {0};
    DISPLAY_PWREN_CLK_ENA();
    HAL_GPIO_WritePin(DISPLAY_PWREN_PORT, DISPLAY_PWREN_PIN, GPIO_PIN_RESET);
    GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStructure.Pull = GPIO_NOPULL;
    GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
    GPIO_InitStructure.Pin = DISPLAY_PWREN_PIN;
    HAL_GPIO_Init(DISPLAY_PWREN_PORT, &GPIO_InitStructure);
  }
#endif

#ifdef DISPLAY_RESET_PIN
  {
    GPIO_InitTypeDef GPIO_InitStructure = {0};
    DISPLAY_RESET_CLK_ENA();
    HAL_GPIO_WritePin(DISPLAY_RESET_PORT, DISPLAY_RESET_PIN, GPIO_PIN_RESET);
    GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStructure.Pull = GPIO_NOPULL;
    GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
    GPIO_InitStructure.Pin = DISPLAY_RESET_PIN;
    HAL_GPIO_Init(DISPLAY_RESET_PORT, &GPIO_InitStructure);
  }
#endif

  if (!display_init_ll(mode)) {
    goto cleanup;
  }

  drv->initialized = true;
  return true;

cleanup:
  display_deinit(DISPLAY_RESET_CONTENT);
  return false;
}

// This implementation does not support `mode` parameter, it
// behaves as if `mode` is always `DISPLAY_RESET_CONTENT`.
static void display_deinit_ll(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  gfx_bitblt_deinit();

  NVIC_DisableIRQ(LTDC_IRQn);
  NVIC_DisableIRQ(LTDC_ER_IRQn);

#ifdef BACKLIGHT_PIN_PIN
  HAL_GPIO_DeInit(BACKLIGHT_PIN_PORT, BACKLIGHT_PIN_PIN);
#endif

#ifdef USE_BACKLIGHT
  backlight_deinit(BACKLIGHT_RESET);
#endif

  display_dsi_deinit(drv);
  display_ltdc_deinit(drv);
#ifdef DISPLAY_GFXMMU
  display_gfxmmu_deinit(drv);
#endif
  display_pll_deinit();
}

// This implementation does not support `mode` parameter, it
// behaves as if `mode` is always `DISPLAY_RESET_CONTENT`.
void display_deinit(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  display_deinit_ll(mode);

#ifdef DISPLAY_RESET_PIN
  // Release the RESET pin
  HAL_GPIO_DeInit(DISPLAY_RESET_PORT, DISPLAY_RESET_PIN);
#endif

#ifdef DISPLAY_PWREN_PIN
  // Release PWREN pin and switch display power off
  HAL_GPIO_DeInit(DISPLAY_PWREN_PORT, DISPLAY_PWREN_PIN);
#endif

  memset(drv, 0, sizeof(display_driver_t));
}

#if REFRESH_RATE_SCALING_SUPPORTED
void display_refresh_rate_timeout_set(void) {
  display_driver_t *drv = &g_display_driver;
  irq_key_t key;

  if (!drv->initialized) {
    return;
  }

  key = irq_lock();

  // Set/refresh the timeout variable to return to the low refresh rate after
  // the "REFRESH_RATE_HI2LO_TIMEOUT_MS" time of inactivity.
  drv->refresh_rate_timeout_ms = ticks_timeout(REFRESH_RATE_HI2LO_TIMEOUT_MS);
  drv->refresh_rate_timeout_set = true;

  irq_unlock(key);
}

void display_refresh_rate_timeout_check(void) {
  display_driver_t *drv = &g_display_driver;
  irq_key_t key;

  if (!drv->initialized) {
    return;
  }

  // The function is called from an IRQ context. It might be possible to NOT
  // disable IRQs and make preemption (of higher prio IRQs) possible.
  // To be safe, we disable IRQs here.
  key = irq_lock();

  // Is timeout set and expired? Return to the low refresh rate.
  if (drv->refresh_rate_timeout_set &&
      ticks_expired(drv->refresh_rate_timeout_ms)) {
    // Change the display refresh rate to the low refresh rate.
    display_refresh_rate_set(REFRESH_RATE_LO);
    drv->refresh_rate_timeout_set = false;
  }

  irq_unlock(key);
}

static inline void display_refresh_rate_reg_config(display_driver_t *drv) {
  // LTDC && DSI disable.
  __HAL_LTDC_DISABLE(&drv->hlcd_ltdc);
  __HAL_DSI_DISABLE(&drv->hlcd_dsi);

  // Set the Vertical Front Porch (VFP).
  ATOMIC_MODIFY_REG(drv->hlcd_dsi.Instance->VVFPCR, DSI_VVFPCR_VFP_Msk,
                    drv->DSIVidCfg.VerticalFrontPorch);

  // Set Total Height.
  ATOMIC_MODIFY_REG(drv->hlcd_ltdc.Instance->TWCR, LTDC_TWCR_TOTALH_Msk,
                    drv->hlcd_ltdc.Init.TotalHeigh);

  // DSI && LTDC enable.
  __HAL_DSI_ENABLE(&drv->hlcd_dsi);
  __HAL_LTDC_ENABLE(&drv->hlcd_ltdc);
}

void display_refresh_rate_set(display_refresh_rate_t refresh_rate) {
  display_driver_t *drv = &g_display_driver;
  irq_key_t key;

  if (!drv->initialized) {
    return;
  }

  key = irq_lock();

  if (refresh_rate < REFRESH_RATE_COUNT && refresh_rate != drv->refresh_rate) {
    // Update the requested refresh rate. Do it in any state of the state
    // machine. The actual update will be performed in the IRQ context.
    // The respective VFP and Total Height values will be set there.
    drv->refresh_rate = refresh_rate;

    if (drv->refresh_rate_state == REFRESH_RATE_IDLE) {
      // Move the state machine forward to request the update in the "Line
      // Event" IRQ handler.
      drv->refresh_rate_state = REFRESH_RATE_REQUESTED;
    }
  }

  irq_unlock(key);
}

void display_refresh_rate_config(void) {
  display_driver_t *drv = &g_display_driver;
  irq_key_t key;

  if (!drv->initialized) {
    return;
  }

  // The function is called from an IRQ context. It might be possible to NOT
  // disable IRQs and make preemption (of higher prio IRQs) possible.
  // To be safe, we disable IRQs here.
  key = irq_lock();

  if (drv->refresh_rate_state == REFRESH_RATE_UPDATING) {
    // 30 us timeout, because the line takes max 29.75us at 18.518519MHz pixel
    // clock and 544 pixel line width (including porches and sync).
    uint64_t timeout_us = systick_us() + REFRESH_RATE_CFG_TIMEOUT_US;

    // Check if we are in the vertical sync period. If yes, we have no idea
    // where exactly we are in the VSYNC, so we can't safely update the
    // registers now. We postpone the update - moving back to the REQUESTED
    // state to try again later.
    if (READ_BIT(drv->hlcd_ltdc.Instance->CDSR, LTDC_CDSR_VSYNCS) == 0) {
      // Busy waiting for VSYNC with timeout. As soon as VSYNC starts (==1),
      // we can proceed with the update.
      while (READ_BIT(drv->hlcd_ltdc.Instance->CDSR, LTDC_CDSR_VSYNCS) == 0) {
        if (systick_us() > timeout_us) {
          // Failed to update, moving back to REQUESTED state to try again.
          drv->refresh_rate_state = REFRESH_RATE_REQUESTED;

          irq_unlock(key);
          return;
        }
      }

      // Prepare the structures for the update.
      drv->DSIVidCfg.VerticalFrontPorch = vfp_lut[drv->refresh_rate];
      drv->hlcd_ltdc.Init.TotalHeigh = drv->hlcd_ltdc.Init.AccumulatedActiveH +
                                       drv->DSIVidCfg.VerticalFrontPorch;

      // Perform the update of the registers.
      display_refresh_rate_reg_config(drv);

      // Updated: moving to the IDLE state.
      drv->refresh_rate_state = REFRESH_RATE_IDLE;
    } else {
      // Failed to update, moving back to REQUESTED state to try again.
      drv->refresh_rate_state = REFRESH_RATE_REQUESTED;
    }
  }

  irq_unlock(key);
}
#endif  // REFRESH_RATE_SCALING_SUPPORTED

#ifdef USE_SUSPEND
bool display_suspend(display_wakeup_params_t *wakeup_params) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized || NULL == wakeup_params) {
    // The driver isn't initialized, wrong control flow applied, return error OR
    // invalid parameter has been passed
    return false;
  }

  if (!drv->suspended) {
    drv->display.backlight_level = display_get_backlight();

    if (!panel_suspend(drv)) {
      return false;
    }

    display_deinit_ll(DISPLAY_RESET_CONTENT);

    drv->suspended = true;
  }

  memcpy(wakeup_params, &drv->display, sizeof(display_wakeup_params_t));

  return true;
}

bool display_resume(const display_wakeup_params_t *wakeup_params) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized || NULL == wakeup_params) {
    // The driver isn't initialized, wrong control flow applied, return error OR
    // invalid parameter has been passed
    return false;
  }

  if (!drv->suspended) {
    // The driver isn't suspended, nothing to resume
    return true;
  }

  if (!display_init_ll(DISPLAY_RESET_CONTENT)) {
    goto cleanup;
  }

  if (!display_set_backlight(wakeup_params->backlight_level)) {
    goto cleanup;
  }

  drv->suspended = false;

  return true;

cleanup:
  display_deinit(DISPLAY_RESET_CONTENT);
  return false;
}
#endif  // USE_SUSPEND

bool display_set_backlight(uint8_t level) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return false;
  }

#ifdef USE_BACKLIGHT
  if (level > 0 && backlight_get() == 0) {
    display_ensure_refreshed();
  }

  return backlight_set(level);
#else
  // Just emulation, not doing anything
  drv->backlight_level = level;
  return true;
#endif
}

uint8_t display_get_backlight(void) {
  display_driver_t *drv = &g_display_driver;

  if (!drv->initialized) {
    return 0;
  }
#ifdef USE_BACKLIGHT
  return backlight_get();
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
