
#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <gfx/gfx_bitblt.h>
#include <io/display.h>

#ifdef KERNEL_MODE

#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/systick.h>

#include "../backlight/backlight_pwm.h"
#include "display_internal.h"

display_driver_t g_display_driver = {
    .initialized = false,
    .blanking = false,
    .current_frame_buffer = 0,
};

#define VSYNC 4
#define VBP 4
#define VFP 8
#define VACT 320
#define HSYNC 30
#define HBP 60
#define HFP 60
#define HACT 240
#define LCD_WIDTH 240
#define LCD_HEIGHT 320

/**
 * @brief  Initialize DSI MSP.
 * @param  hdsi DSI handle
 * @retval None
 */
static void DSI_MspInit(DSI_HandleTypeDef *hdsi) {
  display_driver_t *drv = &g_display_driver;

  RCC_PeriphCLKInitTypeDef PLL3InitPeriph = {0};
  RCC_PeriphCLKInitTypeDef DSIPHYInitPeriph = {0};
  // GPIO_InitTypeDef GPIO_InitStruct = {0};

  UNUSED(hdsi);

  /* Enable DSI clock */
  __HAL_RCC_DSI_CLK_ENABLE();

  /** ################ Set DSI clock to D-PHY source clock ##################
   * **/

  /* Start and configurre PLL3 */
  /* HSE = 32MHZ */
  /* 32/(M=8)   = 4MHz input (min) */
  /* 4*(N=125)  = 500MHz VCO (almost max) */
  /* 500/(P=8)  = 62.5 for DSI ie exactly the lane byte clock*/

  PLL3InitPeriph.PeriphClockSelection = RCC_PERIPHCLK_DSI | RCC_PERIPHCLK_LTDC;
  PLL3InitPeriph.DsiClockSelection = RCC_DSICLKSOURCE_PLL3;
  PLL3InitPeriph.LtdcClockSelection = RCC_LTDCCLKSOURCE_PLL3;
  PLL3InitPeriph.PLL3.PLL3M = 8;
  PLL3InitPeriph.PLL3.PLL3N = 125;
  PLL3InitPeriph.PLL3.PLL3P = 8;
  PLL3InitPeriph.PLL3.PLL3Q = 8;
  PLL3InitPeriph.PLL3.PLL3R = 24;
  PLL3InitPeriph.PLL3.PLL3FRACN = 0;
  PLL3InitPeriph.PLL3.PLL3RGE = RCC_PLLVCIRANGE_0;
  PLL3InitPeriph.PLL3.PLL3ClockOut = RCC_PLL3_DIVR | RCC_PLL3_DIVP;
  PLL3InitPeriph.PLL3.PLL3Source = RCC_PLLSOURCE_HSE;
  (void)HAL_RCCEx_PeriphCLKConfig(&PLL3InitPeriph);

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

  (void)HAL_RCCEx_PeriphCLKConfig(&DSIPHYInitPeriph);

  /* Reset the TX escape clock division factor */
  drv->hlcd_dsi.Instance->CCR &= ~DSI_CCR_TXECKDIV;

  /* Disable the DSI PLL */
  __HAL_DSI_PLL_DISABLE(&drv->hlcd_dsi);

  /* Disable the DSI host */
  __HAL_DSI_DISABLE(&drv->hlcd_dsi);

  /** #########################################################################
   * **/

  /* Enable DSI NVIC interrupt */
  HAL_NVIC_SetPriority(DSI_IRQn, IRQ_PRI_NORMAL, 0);
  HAL_NVIC_EnableIRQ(DSI_IRQn);
}

/**
 * @brief  MX DSI initialization.
 * @param  hdsi DSI handle.
 * @retval HAL status.
 */
__weak HAL_StatusTypeDef MX_DSI_Init(DSI_HandleTypeDef *hdsi) {
  display_driver_t *drv = &g_display_driver;

  DSI_PLLInitTypeDef PLLInit = {0};

  /* DSI initialization */
  hdsi->Instance = DSI;
  hdsi->Init.AutomaticClockLaneControl = DSI_AUTO_CLK_LANE_CTRL_DISABLE;
  /* We have 1 data lane at 500Mbps => lane byte clock at 500/8 = 62,5 MHZ */
  /* We want TX escape clock at around 20MHz and under 20MHz so clock division
   * is set to 4 */
  hdsi->Init.TXEscapeCkdiv = 4;
  hdsi->Init.NumberOfLanes = DSI_ONE_DATA_LANE;
  hdsi->Init.PHYFrequencyRange = DSI_DPHY_FRANGE_450MHZ_510MHZ;
  hdsi->Init.PHYLowPowerOffset = 0;

  PLLInit.PLLNDIV = 62;
  PLLInit.PLLIDF = 4;
  PLLInit.PLLODF = 2;
  PLLInit.PLLVCORange = DSI_DPHY_VCO_FRANGE_800MHZ_1GHZ;
  PLLInit.PLLChargePump = DSI_PLL_CHARGE_PUMP_2000HZ_4400HZ;
  PLLInit.PLLTuning = DSI_PLL_LOOP_FILTER_2000HZ_4400HZ;

  if (HAL_DSI_Init(hdsi, &PLLInit) != HAL_OK) {
    return HAL_ERROR;
  }

  if (HAL_DSI_SetGenericVCID(&drv->hlcd_dsi, 0) != HAL_OK) {
    return HAL_ERROR;
  }

  /* Configure the DSI for Video mode */
  drv->DSIVidCfg.VirtualChannelID = 0;
  drv->DSIVidCfg.HSPolarity = DSI_HSYNC_ACTIVE_HIGH;
  drv->DSIVidCfg.VSPolarity = DSI_VSYNC_ACTIVE_HIGH;
  drv->DSIVidCfg.DEPolarity = DSI_DATA_ENABLE_ACTIVE_HIGH;
  drv->DSIVidCfg.ColorCoding = DSI_RGB888;
  drv->DSIVidCfg.Mode = DSI_VID_MODE_NB_PULSES;
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
    return HAL_ERROR;
  }

  return HAL_OK;
}

/**
 * @brief  Initialize LTDC MSP.
 * @param  hltdc LTDC handle
 * @retval None
 */
static void LTDC_MspInit(LTDC_HandleTypeDef *hltdc) {
  /* Prevent unused argument(s) compilation warning */
  UNUSED(hltdc);

  /* Enable LCD clock */
  __HAL_RCC_LTDC_CLK_ENABLE();

  /* Enable LTDC interrupt */
  HAL_NVIC_SetPriority(LTDC_IRQn, IRQ_PRI_NORMAL, 0);
  HAL_NVIC_EnableIRQ(LTDC_IRQn);

  HAL_NVIC_SetPriority(LTDC_ER_IRQn, IRQ_PRI_NORMAL, 0);
  HAL_NVIC_EnableIRQ(LTDC_ER_IRQn);
}

/**
 * @brief  MX LTDC initialization.
 * @param  hltdc LTDC handle.
 * @retval HAL status.
 */
__weak HAL_StatusTypeDef MX_LTDC_Init(LTDC_HandleTypeDef *hltdc) {
  display_driver_t *drv = &g_display_driver;

  /* LTDC initialization */
  hltdc->Instance = LTDC;
  hltdc->Init.HSPolarity = LTDC_HSPOLARITY_AL;
  hltdc->Init.VSPolarity = LTDC_VSPOLARITY_AL;
  hltdc->Init.DEPolarity = LTDC_DEPOLARITY_AL;
  hltdc->Init.PCPolarity = LTDC_PCPOLARITY_IPC;
  hltdc->Init.HorizontalSync = HSYNC - 1;
  hltdc->Init.AccumulatedHBP = HSYNC + HBP - 1;
  hltdc->Init.AccumulatedActiveW = HACT + HBP + HSYNC - 1;
  hltdc->Init.TotalWidth = HACT + HBP + HFP + HSYNC - 1;
  hltdc->Init.Backcolor.Red = 0;   /* Not used default value */
  hltdc->Init.Backcolor.Green = 0; /* Not used default value */
  hltdc->Init.Backcolor.Blue = 0;  /* Not used default value */
  hltdc->Init.Backcolor.Reserved = 0xFF;

  HAL_LTDCEx_StructInitFromVideoConfig(hltdc, &drv->DSIVidCfg);

  return HAL_LTDC_Init(hltdc);
}

/**
 * @brief  MX LTDC layer configuration.
 * @param  hltdc LTDC handle.
 * @param  LayerIndex LTDC layer index.
 * @retval HAL status.
 */
__weak HAL_StatusTypeDef MX_LTDC_ConfigLayer(LTDC_HandleTypeDef *hltdc,
                                             uint32_t LayerIndex,
                                             uint32_t fb_addr) {
  LTDC_LayerCfgTypeDef LayerCfg = {0};

  /* LTDC layer configuration */
  LayerCfg.WindowX0 = 0;
  LayerCfg.WindowX1 = LCD_WIDTH;
  LayerCfg.WindowY0 = 0;
  LayerCfg.WindowY1 = LCD_HEIGHT;
  LayerCfg.PixelFormat = LTDC_PIXEL_FORMAT_RGB565;
  LayerCfg.Alpha = 0xFF; /* NU default value */
  LayerCfg.Alpha0 = 0;   /* NU default value */
  LayerCfg.BlendingFactor1 =
      LTDC_BLENDING_FACTOR1_PAxCA; /* Not Used: default value */
  LayerCfg.BlendingFactor2 =
      LTDC_BLENDING_FACTOR2_PAxCA; /* Not Used: default value */
  LayerCfg.FBStartAdress = fb_addr;
  LayerCfg.ImageWidth = LCD_WIDTH; /* Number of pixels per line in virtual
                                                         frame buffer */
  LayerCfg.ImageHeight = LCD_HEIGHT;
  LayerCfg.Backcolor.Red = 0;   /* Not Used: default value */
  LayerCfg.Backcolor.Green = 0; /* Not Used: default value */
  LayerCfg.Backcolor.Blue = 0;  /* Not Used: default value */
  LayerCfg.Backcolor.Reserved = 0xFF;
  return HAL_LTDC_ConfigLayer(hltdc, &LayerCfg, LayerIndex);
}

/**
 * @brief  Initialize LCD.
 * @retval BSP status.
 */
static int32_t LCD_Init(void) {
  display_driver_t *drv = &g_display_driver;

  // uint32_t ErrorNumber = 0;
  DSI_PHY_TimerTypeDef PhyTimers = {0};
  DSI_HOST_TimeoutTypeDef HostTimeouts = {0};

  /************/
  /* DSI init */
  /************/
  DSI_MspInit(&drv->hlcd_dsi);

  /* DSI peripheral initialization */
  MX_DSI_Init(&drv->hlcd_dsi);

  /*********************/
  /* LCD configuration */
  /*********************/
  PhyTimers.ClockLaneHS2LPTime = 11;
  PhyTimers.ClockLaneLP2HSTime = 40;
  PhyTimers.DataLaneHS2LPTime = 12;
  PhyTimers.DataLaneLP2HSTime = 23;
  PhyTimers.DataLaneMaxReadTime = 0;
  PhyTimers.StopWaitTime = 7;

  if (HAL_DSI_ConfigPhyTimer(&drv->hlcd_dsi, &PhyTimers) != HAL_OK) {
    return 6;
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
    return 7;
  }

  if (HAL_DSI_ConfigFlowControl(&drv->hlcd_dsi, DSI_FLOW_CONTROL_BTA) !=
      HAL_OK) {
    return 7;
  }

  /* Enable the DSI host */
  __HAL_DSI_ENABLE(&drv->hlcd_dsi);

  /*************/
  /* LTDC init */
  /*************/
  // MX_LTDC_ClockConfig(&hlcd_ltdc);

  LTDC_MspInit(&drv->hlcd_ltdc);

  /* LTDC peripheral initialization */
  MX_LTDC_Init(&drv->hlcd_ltdc);

  MX_LTDC_ConfigLayer(&drv->hlcd_ltdc, LTDC_LAYER_1,
                      display_fb_get_initial_addr());

  /* Start DSI */
  if (HAL_DSI_Start(&drv->hlcd_dsi) != HAL_OK) {
    return 8;
  }

  HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x11, 0);

  systick_delay_ms(120);

  HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0x36, 0x00);
  HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0x3A, 0x06);

  // mipi video mode
  HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xB0, 0x10);

  // Write(Command , 0xB2);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0C);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0C);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x33);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x33);
  HAL_DSI_LongWrite(
      &drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 10, 0xB2,
      (uint8_t[]){0x00, 0x0c, 0x00, 0x0C, 0x00, 0x00, 0x00, 0x33, 0x00, 0x33});

  // Write(Command , 0xB7);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x06);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xB7,
                    (uint8_t[]){0x00, 0x06});

  // Write(Command , 0xBB);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x1E);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xBB,
                    (uint8_t[]){0x00, 0x1E});

  //   Write(Command , 0xC0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x2C);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xC0,
                    (uint8_t[]){0x00, 0x2C});

  //   Write(Command , 0xC2);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x01);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xC2,
                    (uint8_t[]){0x00, 0x01});

  // Write(Command , 0xC3);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0F);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xC3,
                    (uint8_t[]){0x00, 0x0F});

  // Write(Command , 0xC6);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0F);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xC6,
                    (uint8_t[]){0x00, 0x0F});

  // Write(Command , 0xD0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xA7);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xD0,
                    (uint8_t[]){0x00, 0xA7});

  // Write(Command , 0xD0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xA4);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xA1);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 4, 0xD0,
                    (uint8_t[]){0x00, 0xA4, 0x00, 0xA1});

  // Write(Command , 0xD6);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xA1);
  HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 2, 0xD6,
                    (uint8_t[]){0x00, 0xA1});

  // Write(Command , 0xE0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xF0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x06);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x11);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x09);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0A);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x28);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x37);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x44);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x4E);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x39);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x14);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x15);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x34);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x3A);
  // HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE,  28, 0xE0,
  // (uint8_t[]){0x00, 0xF0, 0x00, 0x06, 0x00, 0x11, 0x00, 0x09, 0x00, 0x0A,
  // 0x00, 0x28, 0x00, 0x37, 0x00, 0x44, 0x00, 0x4E, 0x00, 0x39, 0x00, 0x14,
  // 0x00, 0x15, 0x00, 0x34, 0x00, 0x3A});

  // Write(Command , 0xE1);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0xF0);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0E);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0F);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x0A);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x08);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x04);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x37);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x43);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x4D);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x35);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x12);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x13);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x32);
  // Write(Parameter , 0x00);
  // Write(Parameter , 0x39);
  // HAL_DSI_LongWrite(&drv->hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE,  28, 0xE1,
  // (uint8_t[]){0x00, 0xF0, 0x00, 0x0E, 0x00, 0x0F, 0x00, 0x0A, 0x00, 0x08,
  // 0x00, 0x04, 0x00, 0x37, 0x00, 0x43, 0x00, 0x4D, 0x00, 0x35, 0x00, 0x12,
  // 0x00, 0x13, 0x00, 0x32, 0x00, 0x39});

  HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x21, 0);
  HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x29, 0);
  HAL_DSI_ShortWrite(&drv->hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x2C, 0);

  HAL_Delay(120);

  HAL_LTDC_ProgramLineEvent(&drv->hlcd_ltdc, 320);

  /* Enable LTDC interrupt */
  HAL_NVIC_SetPriority(LTDC_IRQn, IRQ_PRI_NORMAL, 0);
  HAL_NVIC_EnableIRQ(LTDC_IRQn);

  HAL_NVIC_SetPriority(LTDC_ER_IRQn, IRQ_PRI_NORMAL, 0);
  HAL_NVIC_EnableIRQ(LTDC_ER_IRQn);

  __HAL_LTDC_ENABLE_IT(&drv->hlcd_ltdc, LTDC_IT_LI | LTDC_IT_FU | LTDC_IT_TE);

  return 0;
}

void display_set_fb(uint32_t fb_addr) {
  display_driver_t *drv = &g_display_driver;
  MX_LTDC_ConfigLayer(&drv->hlcd_ltdc, 0, fb_addr);
}

// Fully initializes the display controller.
void display_init(display_content_mode_t mode) {
  display_driver_t *drv = &g_display_driver;

  GPIO_InitTypeDef GPIO_InitStructure = {0};

  __HAL_RCC_DSI_FORCE_RESET();
  __HAL_RCC_LTDC_FORCE_RESET();
  __HAL_RCC_GPIOE_CLK_ENABLE();
  // pwr en
  HAL_GPIO_WritePin(GPIOE, GPIO_PIN_0, GPIO_PIN_RESET);
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
  GPIO_InitStructure.Pin = GPIO_PIN_0;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStructure);

  // reset
  HAL_GPIO_WritePin(GPIOE, GPIO_PIN_2, GPIO_PIN_RESET);
  GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStructure.Pull = GPIO_NOPULL;
  GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
  GPIO_InitStructure.Pin = GPIO_PIN_2;
  HAL_GPIO_Init(GPIOE, &GPIO_InitStructure);

  systick_delay_ms(120);
  HAL_GPIO_WritePin(GPIOE, GPIO_PIN_2, GPIO_PIN_SET);

  backlight_pwm_init(BACKLIGHT_RESET);

  display_fb_clear();

  __HAL_RCC_LTDC_RELEASE_RESET();
  __HAL_RCC_DSI_RELEASE_RESET();

  LCD_Init();

  drv->initialized = true;
}

int display_set_backlight(int level) { return backlight_pwm_set(level); }

int display_get_backlight(void) { return backlight_pwm_get(); }

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

void display_deinit(display_content_mode_t mode) {}

void display_copy_rgb565(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  display_get_frame_buffer(&fb);

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgb565_copy_rgb565(&bb_new);
}

void display_fill(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  display_get_frame_buffer(&fb);

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgb565_fill(&bb_new);
}

#endif

void display_copy_mono1p(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;
  display_get_frame_buffer(&fb);

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgb565_copy_mono1p(&bb_new);
}

void display_copy_mono4(const gfx_bitblt_t *bb) {
  display_fb_info_t fb;

  display_get_frame_buffer(&fb);

  gfx_bitblt_t bb_new = *bb;
  bb_new.dst_row = (uint8_t *)fb.ptr + (fb.stride * bb_new.dst_y);
  bb_new.dst_stride = fb.stride;

  gfx_rgb565_copy_mono4(&bb_new);
}
