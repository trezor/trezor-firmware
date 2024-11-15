/**
  ******************************************************************************
  * @file    stm32u5x9j_discovery_lcd.c
  * @author  MCD Application Team
  * @brief   This file includes the driver for Liquid Crystal Display (LCD)
  module
  *          mounted on MB1829A board (ARGB8888 color format).
  @verbatim
  1. How To use this driver:
  --------------------------
     - This driver is used to drive directly in command mode a LCD TFT using the
       DSI interface.
       The following IPs are implied : DSI Host IP block working
       in conjunction to the LTDC controller.
     - This driver is linked by construction to LCD.

  2. Driver description:
  ----------------------
    + Initialization steps:
       o Initialize the LCD using the BSP_LCD_Init() function. You can select
         display orientation with "Orientation" parameter (portrait, landscape,
         portrait with 180 degrees rotation or landscape with 180 degrees
         rotation).
       o Call BSP_LCD_GetXSize() and BSP_LCD_GetYsize() to get respectively
         width and height in pixels of LCD in the current orientation.
       o Call BSP_LCD_SetBrightness() and BSP_LCD_GetBrightness() to
         respectively set and get LCD brightness.
       o Call BSP_LCD_SetActiveLayer() to select the current active layer.
       o Call BSP_LCD_GetFormat() to get LCD pixel format supported.

    + Display on LCD:
       o Call BSP_LCD_DisplayOn() and BSP_LCD_DisplayOff() to respectively
         switch on and switch off the LCD display.
       o First, check that frame buffer is available using
  BSP_LCD_IsFrameBufferAvailable(). o When frame buffer is available, modify it
  using following functions: o Call BSP_LCD_WritePixel() and BSP_LCD_ReadPixel()
  to respectively write and read a pixel. o Call BSP_LCD_DrawHLine() to draw a
  horizontal line. o Call BSP_LCD_DrawVLine() to draw a vertical line. o Call
  BSP_LCD_DrawBitmap() to draw a bitmap. o Call BSP_LCD_FillRect() to draw a
  rectangle. o Call BSP_LCD_FillRGBRect() to draw a rectangle with RGB buffer.
       o Call BSP_LCD_Refresh() to refresh LCD display.

    + De-initialization steps:
       o De-initialize the LCD using the BSP_LCD_DeInit() function.

  @endverbatim
  ******************************************************************************
  * @attention
  *
  * Copyright (c) 2023 STMicroelectronics.
  * All rights reserved.
  *
  * This software is licensed under terms that can be found in the LICENSE file
  * in the root directory of this software component.
  * If no LICENSE file comes with this software, it is provided AS-IS.
  *
  ******************************************************************************
  */

/* Includes ------------------------------------------------------------------*/
#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sys/irq.h>
#include "display_internal.h"

#ifdef KERNEL_MODE

/* Common Error codes */
#define BSP_ERROR_NONE 0
#define BSP_ERROR_NO_INIT -1
#define BSP_ERROR_WRONG_PARAM -2
#define BSP_ERROR_BUSY -3
#define BSP_ERROR_PERIPH_FAILURE -4
#define BSP_ERROR_COMPONENT_FAILURE -5
#define BSP_ERROR_UNKNOWN_FAILURE -6
#define BSP_ERROR_UNKNOWN_COMPONENT -7
#define BSP_ERROR_BUS_FAILURE -8
#define BSP_ERROR_CLOCK_FAILURE -9
#define BSP_ERROR_MSP_FAILURE -10
#define BSP_ERROR_FEATURE_NOT_SUPPORTED -11

#define BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE (-102)
/* Button user interrupt priority */
#define BSP_BUTTON_USER_IT_PRIORITY \
  0x0FUL /* Default is lowest priority level */

#define LCD_PIXEL_FORMAT_ARGB8888                                           \
  0x00000000U                               /*!< ARGB8888 LTDC pixel format \
                                             */
#define LCD_PIXEL_FORMAT_RGB888 0x00000001U /*!< RGB888 LTDC pixel format   */
#define LCD_PIXEL_FORMAT_RGB565 0x00000002U /*!< RGB565 LTDC pixel format   */
#define LCD_PIXEL_FORMAT_ARGB1555             \
  0x00000003U /*!< ARGB1555 LTDC pixel format \
               */
#define LCD_PIXEL_FORMAT_ARGB4444                                         \
  0x00000004U                             /*!< ARGB4444 LTDC pixel format \
                                           */
#define LCD_PIXEL_FORMAT_L8 0x00000005U   /*!< L8 LTDC pixel format       */
#define LCD_PIXEL_FORMAT_AL44 0x00000006U /*!< AL44 LTDC pixel format     */
#define LCD_PIXEL_FORMAT_AL88 0x00000007U /*!< AL88 LTDC pixel format     */
/* LCD instances */
#define LCD_INSTANCES_NBR 1U

#define DSI_POWERON_GPIO_PORT GPIOI
#define DSI_POWERON_GPIO_PIN GPIO_PIN_5
#define DSI_POWERON_GPIO_CLOCK_ENABLE() __HAL_RCC_GPIOI_CLK_ENABLE()

#define DSI_RESET_GPIO_PORT GPIOD
#define DSI_RESET_GPIO_PIN GPIO_PIN_5
#define DSI_RESET_GPIO_CLOCK_ENABLE() __HAL_RCC_GPIOD_CLK_ENABLE()

#define VSYNC 1
#define VBP 12
#define VFP 50
#define VACT 481
#define HSYNC 2
#define HBP 1
#define HFP 1
#define HACT 480
#define LCD_WIDTH 480
#define LCD_HEIGHT 480

#include "display_gfxmmu_lut.h"

/** @addtogroup BSP
 * @{
 */

/** @addtogroup STM32U5x9J_DISCOVERY
 * @{
 */

/** @defgroup STM32U5x9J_DISCOVERY_LCD LCD
 * @{
 */

/** @defgroup STM32U5x9J_DISCOVERY_LCD_Private_Defines LCD Private Constants
 * @{
 */

/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_LCD_Private_Variables LCD Private Variables
 * @{
 */

#if (USE_HAL_GFXMMU_REGISTER_CALLBACKS == 1)
static uint32_t LcdGfxmmu_IsMspCbValid[LCD_INSTANCES_NBR] = {0};
#endif /* (USE_HAL_GFXMMU_REGISTER_CALLBACKS == 1) */

#if (USE_HAL_LTDC_REGISTER_CALLBACKS == 1)
static uint32_t LcdLtdc_IsMspCbValid[LCD_INSTANCES_NBR] = {0};
#endif /* (USE_HAL_LTDC_REGISTER_CALLBACKS == 1) */

#if (USE_HAL_DSI_REGISTER_CALLBACKS == 1)
static uint32_t LcdDsi_IsMspCbValid[LCD_INSTANCES_NBR] = {0};
#endif /* (USE_HAL_DSI_REGISTER_CALLBACKS == 1) */

GFXMMU_HandleTypeDef hlcd_gfxmmu = {0};
LTDC_HandleTypeDef hlcd_ltdc = {0};
DSI_HandleTypeDef hlcd_dsi = {0};
static DSI_VidCfgTypeDef DSIVidCfg = {0};

/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_LCD_Private_FunctionPrototypes LCD Private
 * Function Prototypes
 * @{
 */
static int32_t LCD_Init(void);
static int32_t LCD_DeInit(void);

static void GFXMMU_MspInit(GFXMMU_HandleTypeDef *hgfxmmu);
static void GFXMMU_MspDeInit(GFXMMU_HandleTypeDef *hgfxmmu);
static void LTDC_MspInit(LTDC_HandleTypeDef *hltdc);
static void LTDC_MspDeInit(LTDC_HandleTypeDef *hltdc);
static void DSI_MspInit(DSI_HandleTypeDef *hdsi);
static void DSI_MspDeInit(DSI_HandleTypeDef *hdsi);
#if (USE_HAL_DSI_REGISTER_CALLBACKS == 1)
static void DSI_EndOfRefreshCallback(DSI_HandleTypeDef *hdsi);
#endif /* (USE_HAL_DSI_REGISTER_CALLBACKS == 1) */
/**
 * @}
 */

/** @addtogroup STM32U5x9J_DISCOVERY_LCD_Exported_Functions
 * @{
 */
/**
 * @brief  Initialize the LCD.
 * @param  Instance LCD Instance.
 * @param  Orientation LCD_ORIENTATION_PORTRAIT, LCD_ORIENTATION_LANDSCAPE,
 *                     LCD_ORIENTATION_PORTRAIT_ROT180 or
 * LCD_ORIENTATION_LANDSCAPE_ROT180.
 * @retval BSP status.
 */
int32_t BSP_LCD_Init(uint32_t Instance, uint32_t Orientation) {
  memset(&hlcd_gfxmmu, 0, sizeof(hlcd_gfxmmu));
  memset(&hlcd_ltdc, 0, sizeof(hlcd_ltdc));
  memset(&hlcd_dsi, 0, sizeof(hlcd_dsi));
  memset(&DSIVidCfg, 0, sizeof(DSIVidCfg));

  int32_t status = BSP_ERROR_NONE;

  if ((Instance >= LCD_INSTANCES_NBR) ||
      (Orientation > LCD_ORIENTATION_LANDSCAPE_ROT180)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else if ((Orientation == LCD_ORIENTATION_LANDSCAPE) ||
             (Orientation == LCD_ORIENTATION_LANDSCAPE_ROT180)) {
    status = BSP_ERROR_FEATURE_NOT_SUPPORTED;
  } else {
    if (LCD_Init() != 0) {
      status = BSP_ERROR_PERIPH_FAILURE;
    }
  }

  return status;
}

/**
 * @brief  De-Initialize the LCD.
 * @param  Instance LCD Instance.
 * @retval BSP status.
 */
int32_t BSP_LCD_DeInit(uint32_t Instance) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    if (LCD_DeInit() != 0) {
      status = BSP_ERROR_PERIPH_FAILURE;
    }
  }

  return status;
}

/**
 * @brief  Set the display on.
 * @param  Instance LCD Instance.
 * @retval BSP status.
 */
int32_t BSP_LCD_DisplayOn(uint32_t Instance) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Set the display on */
    if (HAL_DSI_ShortWrite(&hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1,
                           DSI_SET_DISPLAY_ON, 0x00) != HAL_OK) {
      status = BSP_ERROR_WRONG_PARAM;
    }
  }

  return status;
}

/**
 * @brief  Set the display off.
 * @param  Instance LCD Instance.
 * @retval BSP status.
 */
int32_t BSP_LCD_DisplayOff(uint32_t Instance) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Set the display off */
    if (HAL_DSI_ShortWrite(&hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1,
                           DSI_SET_DISPLAY_OFF, 0x00) != HAL_OK) {
      status = BSP_ERROR_WRONG_PARAM;
    }
  }

  return status;
}

/**
 * @brief  Set the display brightness.
 * @param  Instance LCD Instance.
 * @param  Brightness [00: Min (black), 100 Max].
 * @retval BSP status.
 */
int32_t BSP_LCD_SetBrightness(uint32_t Instance, uint32_t Brightness) {
  int32_t status;

  if ((Instance >= LCD_INSTANCES_NBR) || (Brightness > 100U)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    status = BSP_ERROR_FEATURE_NOT_SUPPORTED;
  }

  return status;
}

/**
 * @brief  Get the display brightness.
 * @param  Instance LCD Instance.
 * @param  Brightness [00: Min (black), 100 Max].
 * @retval BSP status.
 */
int32_t BSP_LCD_GetBrightness(uint32_t Instance, uint32_t *Brightness) {
  int32_t status;

  if ((Instance >= LCD_INSTANCES_NBR) || (Brightness == NULL)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    status = BSP_ERROR_FEATURE_NOT_SUPPORTED;
  }

  return status;
}

/**
 * @brief  Get the LCD X size.
 * @param  Instance LCD Instance.
 * @param  Xsize LCD X size.
 * @retval BSP status.
 */
int32_t BSP_LCD_GetXSize(uint32_t Instance, uint32_t *Xsize) {
  int32_t status = BSP_ERROR_NONE;

  if ((Instance >= LCD_INSTANCES_NBR) || (Xsize == NULL)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Get the display Xsize */
    *Xsize = LCD_WIDTH;
  }

  return status;
}

/**
 * @brief  Get the LCD Y size.
 * @param  Instance LCD Instance.
 * @param  Ysize LCD Y size.
 * @retval BSP status.
 */
int32_t BSP_LCD_GetYSize(uint32_t Instance, uint32_t *Ysize) {
  int32_t status = BSP_ERROR_NONE;

  if ((Instance >= LCD_INSTANCES_NBR) || (Ysize == NULL)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Get the display Ysize */
    *Ysize = LCD_HEIGHT;
  }

  return status;
}

/**
 * @brief  Set the LCD active layer.
 * @param  Instance LCD Instance.
 * @param  LayerIndex Active layer index.
 * @retval BSP status.
 */
int32_t BSP_LCD_SetActiveLayer(uint32_t Instance, uint32_t LayerIndex) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Nothing to do */
    UNUSED(LayerIndex);
  }

  return status;
}

/**
 * @brief  Get pixel format supported by LCD.
 * @param  Instance LCD Instance.
 * @param  Format Pointer on pixel format.
 * @retval BSP status.
 */
int32_t BSP_LCD_GetFormat(uint32_t Instance, uint32_t *Format) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Get pixel format supported by LCD */
    *Format = LCD_PIXEL_FORMAT_ARGB8888;
  }

  return status;
}

void MX_GFXMMU_Reinit(GFXMMU_HandleTypeDef *hgfxmmu) {
  /* Initialize GFXMMU */
  hgfxmmu->Instance = GFXMMU;
  hgfxmmu->Init.BlocksPerLine = GFXMMU_192BLOCKS;
  hgfxmmu->Init.DefaultValue = 0xFFFFFFFFU;
  hgfxmmu->Init.Buffers.Buf0Address = (uint32_t)physical_frame_buffer_0;
  hgfxmmu->Init.Buffers.Buf1Address = (uint32_t)physical_frame_buffer_1;
  hgfxmmu->Init.Buffers.Buf2Address = 0;
  hgfxmmu->Init.Buffers.Buf3Address = 0;
#if defined(GFXMMU_CR_CE)
  hgfxmmu->Init.CachePrefetch.Activation = DISABLE;
  hgfxmmu->Init.CachePrefetch.CacheLock = GFXMMU_CACHE_LOCK_DISABLE;
  hgfxmmu->Init.CachePrefetch.CacheLockBuffer =
      GFXMMU_CACHE_LOCK_BUFFER0;                                      /* NU */
  hgfxmmu->Init.CachePrefetch.CacheForce = GFXMMU_CACHE_FORCE_ENABLE; /* NU */
  hgfxmmu->Init.CachePrefetch.OutterBufferability =
      GFXMMU_OUTTER_BUFFERABILITY_DISABLE;
  hgfxmmu->Init.CachePrefetch.OutterCachability =
      GFXMMU_OUTTER_CACHABILITY_DISABLE;
  hgfxmmu->Init.CachePrefetch.Prefetch = GFXMMU_PREFETCH_DISABLE;
#endif /* GFXMMU_CR_CE */
#if defined(GFXMMU_CR_ACE)
  hgfxmmu->Init.AddressCache.Activation = DISABLE;
  hgfxmmu->Init.AddressCache.AddressCacheLockBuffer =
      GFXMMU_ADDRESSCACHE_LOCK_BUFFER0;
#endif /* GFXMMU_CR_ACE */
  hgfxmmu->Init.Interrupts.Activation = DISABLE;
  hgfxmmu->Init.Interrupts.UsedInterrupts = GFXMMU_AHB_MASTER_ERROR_IT; /* NU */
}

/**
 * @brief  MX GFXMMU initialization.
 * @param  hgfxmmu GFXMMU handle.
 * @retval HAL status.
 */
__weak HAL_StatusTypeDef MX_GFXMMU_Init(GFXMMU_HandleTypeDef *hgfxmmu) {
  MX_GFXMMU_Reinit(hgfxmmu);
  return HAL_GFXMMU_Init(hgfxmmu);
}

/**
 * @brief  MX LTDC clock configuration.
 * @param  hltdc LTDC handle.
 * @retval HAL status.
 */
__weak HAL_StatusTypeDef MX_LTDC_ClockConfig(LTDC_HandleTypeDef *hltdc) {
  RCC_PeriphCLKInitTypeDef PLL3InitPeriph = {0};

  /* Prevent unused argument(s) compilation warning */
  UNUSED(hltdc);

  /* Start and configurre PLL3 */
  /* HSE = 16MHZ */
  /* 16/(M=4)   = 4MHz input (min) */
  /* 4*(N=125)  = 500MHz VCO (almost max) */
  /* 500/(P=8)  = 62.5 for DSI ie exactly the lane byte clock*/
  /* 500/(R=24) = 20.83 for LTDC exact match with DSI bandwidth */
  PLL3InitPeriph.PeriphClockSelection = RCC_PERIPHCLK_LTDC;
  PLL3InitPeriph.LtdcClockSelection = RCC_LTDCCLKSOURCE_PLL3;
  PLL3InitPeriph.PLL3.PLL3M = 4;
  PLL3InitPeriph.PLL3.PLL3N = 125;
  PLL3InitPeriph.PLL3.PLL3P = 8;
  PLL3InitPeriph.PLL3.PLL3Q = 8;
  PLL3InitPeriph.PLL3.PLL3R = 24;
  PLL3InitPeriph.PLL3.PLL3FRACN = 0;
  PLL3InitPeriph.PLL3.PLL3RGE = RCC_PLLVCIRANGE_1;
  PLL3InitPeriph.PLL3.PLL3ClockOut = RCC_PLL3_DIVR | RCC_PLL3_DIVP;
  PLL3InitPeriph.PLL3.PLL3Source = RCC_PLLSOURCE_HSE;
  return HAL_RCCEx_PeriphCLKConfig(&PLL3InitPeriph);
}

void MX_LTDC_Reinit(LTDC_HandleTypeDef *hltdc) {
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

  HAL_LTDCEx_StructInitFromVideoConfig(&hlcd_ltdc, &DSIVidCfg);
}

/**
 * @brief  MX LTDC initialization.
 * @param  hltdc LTDC handle.
 * @retval HAL status.
 */
__weak HAL_StatusTypeDef MX_LTDC_Init(LTDC_HandleTypeDef *hltdc) {
  MX_LTDC_Reinit(hltdc);

  return HAL_LTDC_Init(hltdc);
}

// HAL_StatusTypeDef MX_LTDC_ReConfigLayer(LTDC_HandleTypeDef *hltdc, uint32_t
// LayerIndex)
//{
//   LTDC_LayerCfgTypeDef LayerCfg = {0};
//
///* LTDC layer configuration */
//  LayerCfg.WindowX0        = 0;
//  LayerCfg.WindowX1        = LCD_WIDTH;
//  LayerCfg.WindowY0        = 1;
//  LayerCfg.WindowY1        = (uint32_t)LCD_HEIGHT + 1UL;
//  LayerCfg.PixelFormat     = LTDC_PIXEL_FORMAT_ARGB8888;
//  LayerCfg.Alpha           = 0xFF; /* NU default value */
//  LayerCfg.Alpha0          = 0; /* NU default value */
//  LayerCfg.BlendingFactor1 = LTDC_BLENDING_FACTOR1_PAxCA; /* Not Used: default
//  value */ LayerCfg.BlendingFactor2 = LTDC_BLENDING_FACTOR2_PAxCA; /* Not
//  Used: default value */ LayerCfg.FBStartAdress   =
//  GFXMMU_VIRTUAL_BUFFER0_BASE; LayerCfg.ImageWidth      =
//  FRAME_BUFFER_PIXELS_PER_LINE; /* Number of pixels per line in virtual frame
//  buffer */ LayerCfg.ImageHeight = LCD_HEIGHT; LayerCfg.Backcolor.Red   = 0;
//  /* Not Used: default value */ LayerCfg.Backcolor.Green = 0; /* Not Used:
//  default value */ LayerCfg.Backcolor.Blue  = 0; /* Not Used: default value */
//  LayerCfg.Bac
//  return HAL_LTDC_ConfigLayer(hltdc, &LayerCfg, LayerIndex);kcolor.Reserved =
//  0xFF;
//}

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
  LayerCfg.WindowY0 = 1;
  LayerCfg.WindowY1 = (uint32_t)LCD_HEIGHT + 1UL;
  LayerCfg.PixelFormat = LTDC_PIXEL_FORMAT_ARGB8888;
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
  return HAL_LTDC_ConfigLayer(hltdc, &LayerCfg, LayerIndex);
}

/**
 * @brief  MX DSI initialization.
 * @param  hdsi DSI handle.
 * @retval HAL status.
 */
HAL_StatusTypeDef MX_DSI_Reinit(DSI_HandleTypeDef *hdsi) {
  /* DSI initialization */
  hdsi->Instance = DSI;
  hdsi->Init.AutomaticClockLaneControl = DSI_AUTO_CLK_LANE_CTRL_DISABLE;
  /* We have 1 data lane at 500Mbps => lane byte clock at 500/8 = 62,5 MHZ */
  /* We want TX escape clock at around 20MHz and under 20MHz so clock division
   * is set to 4 */
  hdsi->Init.TXEscapeCkdiv = 4;
  hdsi->Init.NumberOfLanes = DSI_TWO_DATA_LANES;
  hdsi->Init.PHYFrequencyRange = DSI_DPHY_FRANGE_450MHZ_510MHZ;
  hdsi->Init.PHYLowPowerOffset = 0;

  /* Configure the DSI for Video mode */
  DSIVidCfg.VirtualChannelID = 0;
  DSIVidCfg.HSPolarity = DSI_HSYNC_ACTIVE_HIGH;
  DSIVidCfg.VSPolarity = DSI_VSYNC_ACTIVE_HIGH;
  DSIVidCfg.DEPolarity = DSI_DATA_ENABLE_ACTIVE_HIGH;
  DSIVidCfg.ColorCoding = DSI_RGB888;
  DSIVidCfg.Mode = DSI_VID_MODE_BURST;
  DSIVidCfg.PacketSize = LCD_WIDTH;
  DSIVidCfg.NullPacketSize = 0xFFFU;
  DSIVidCfg.HorizontalSyncActive = HSYNC * 3;
  DSIVidCfg.HorizontalBackPorch = HBP * 3;
  DSIVidCfg.HorizontalLine = (HACT + HSYNC + HBP + HFP) * 3;
  DSIVidCfg.VerticalSyncActive = VSYNC;
  DSIVidCfg.VerticalBackPorch = VBP;
  DSIVidCfg.VerticalFrontPorch = VFP;
  DSIVidCfg.VerticalActive = VACT;
  DSIVidCfg.LPCommandEnable = DSI_LP_COMMAND_ENABLE;
  DSIVidCfg.LPLargestPacketSize = 64;
  /* Specify for each region of the video frame, if the transmission of command
   * in LP mode is allowed in this region */
  /* while streaming is active in video mode */
  DSIVidCfg.LPHorizontalFrontPorchEnable = DSI_LP_HFP_ENABLE;
  DSIVidCfg.LPHorizontalBackPorchEnable = DSI_LP_HBP_ENABLE;
  DSIVidCfg.LPVerticalActiveEnable = DSI_LP_VACT_ENABLE;
  DSIVidCfg.LPVerticalFrontPorchEnable = DSI_LP_VFP_ENABLE;
  DSIVidCfg.LPVerticalBackPorchEnable = DSI_LP_VBP_ENABLE;
  DSIVidCfg.LPVerticalSyncActiveEnable = DSI_LP_VSYNC_ENABLE;
  DSIVidCfg.FrameBTAAcknowledgeEnable = DSI_FBTAA_ENABLE;
  DSIVidCfg.LooselyPacked = DSI_LOOSELY_PACKED_DISABLE;

  return HAL_OK;
}

/**
 * @brief  MX DSI initialization.
 * @param  hdsi DSI handle.
 * @retval HAL status.
 */
__weak HAL_StatusTypeDef MX_DSI_Init(DSI_HandleTypeDef *hdsi) {
  DSI_PLLInitTypeDef PLLInit = {0};

  /* DSI initialization */
  hdsi->Instance = DSI;
  hdsi->Init.AutomaticClockLaneControl = DSI_AUTO_CLK_LANE_CTRL_DISABLE;
  /* We have 1 data lane at 500Mbps => lane byte clock at 500/8 = 62,5 MHZ */
  /* We want TX escape clock at around 20MHz and under 20MHz so clock division
   * is set to 4 */
  hdsi->Init.TXEscapeCkdiv = 4;
  hdsi->Init.NumberOfLanes = DSI_TWO_DATA_LANES;
  hdsi->Init.PHYFrequencyRange = DSI_DPHY_FRANGE_450MHZ_510MHZ;
  hdsi->Init.PHYLowPowerOffset = 0;

  PLLInit.PLLNDIV = 125;
  PLLInit.PLLIDF = 4;
  PLLInit.PLLODF = 2;
  PLLInit.PLLVCORange = DSI_DPHY_VCO_FRANGE_800MHZ_1GHZ;
  PLLInit.PLLChargePump = DSI_PLL_CHARGE_PUMP_2000HZ_4400HZ;
  PLLInit.PLLTuning = DSI_PLL_LOOP_FILTER_2000HZ_4400HZ;

  if (HAL_DSI_Init(hdsi, &PLLInit) != HAL_OK) {
    return HAL_ERROR;
  }

  if (HAL_DSI_SetGenericVCID(&hlcd_dsi, 0) != HAL_OK) {
    return HAL_ERROR;
  }

  /* Configure the DSI for Video mode */
  DSIVidCfg.VirtualChannelID = 0;
  DSIVidCfg.HSPolarity = DSI_HSYNC_ACTIVE_HIGH;
  DSIVidCfg.VSPolarity = DSI_VSYNC_ACTIVE_HIGH;
  DSIVidCfg.DEPolarity = DSI_DATA_ENABLE_ACTIVE_HIGH;
  DSIVidCfg.ColorCoding = DSI_RGB888;
  DSIVidCfg.Mode = DSI_VID_MODE_BURST;
  DSIVidCfg.PacketSize = LCD_WIDTH;
  DSIVidCfg.NullPacketSize = 0xFFFU;
  DSIVidCfg.HorizontalSyncActive = HSYNC * 3;
  DSIVidCfg.HorizontalBackPorch = HBP * 3;
  DSIVidCfg.HorizontalLine = (HACT + HSYNC + HBP + HFP) * 3;
  DSIVidCfg.VerticalSyncActive = VSYNC;
  DSIVidCfg.VerticalBackPorch = VBP;
  DSIVidCfg.VerticalFrontPorch = VFP;
  DSIVidCfg.VerticalActive = VACT;
  DSIVidCfg.LPCommandEnable = DSI_LP_COMMAND_ENABLE;
  DSIVidCfg.LPLargestPacketSize = 64;
  /* Specify for each region of the video frame, if the transmission of command
   * in LP mode is allowed in this region */
  /* while streaming is active in video mode */
  DSIVidCfg.LPHorizontalFrontPorchEnable = DSI_LP_HFP_ENABLE;
  DSIVidCfg.LPHorizontalBackPorchEnable = DSI_LP_HBP_ENABLE;
  DSIVidCfg.LPVerticalActiveEnable = DSI_LP_VACT_ENABLE;
  DSIVidCfg.LPVerticalFrontPorchEnable = DSI_LP_VFP_ENABLE;
  DSIVidCfg.LPVerticalBackPorchEnable = DSI_LP_VBP_ENABLE;
  DSIVidCfg.LPVerticalSyncActiveEnable = DSI_LP_VSYNC_ENABLE;
  DSIVidCfg.FrameBTAAcknowledgeEnable = DSI_FBTAA_ENABLE;
  DSIVidCfg.LooselyPacked = DSI_LOOSELY_PACKED_DISABLE;

  /* Drive the display */
  if (HAL_DSI_ConfigVideoMode(&hlcd_dsi, &DSIVidCfg) != HAL_OK) {
    return HAL_ERROR;
  }

  return HAL_OK;
}

/**
 * @brief  MX DMA2D initialization.
 * @param  hdma2d  DMA2D handle.
 * @param  Mode    DMA2D transfer mode.
 * @param  OffLine DMA2D output offset.
 * @retval HAL status.
 */
__weak HAL_StatusTypeDef MX_DMA2D_Init(DMA2D_HandleTypeDef *hdma2d,
                                       uint32_t Mode, uint32_t OffLine) {
  /* Register to memory mode with ARGB8888 as color Mode */
  hdma2d->Instance = DMA2D;
  hdma2d->Init.Mode = Mode;
  hdma2d->Init.ColorMode = DMA2D_OUTPUT_ARGB8888;
  hdma2d->Init.OutputOffset = OffLine;
  hdma2d->Init.AlphaInverted = DMA2D_REGULAR_ALPHA;
  hdma2d->Init.RedBlueSwap = DMA2D_RB_REGULAR;
  hdma2d->Init.BytesSwap = DMA2D_BYTES_REGULAR;
  hdma2d->Init.LineOffsetMode = DMA2D_LOM_PIXELS;

  /* DMA2D Initialization */
  return HAL_DMA2D_Init(hdma2d);
}

#if (USE_HAL_GFXMMU_REGISTER_CALLBACKS == 1)
/**
 * @brief  Register Default LCD GFXMMU Msp Callbacks
 * @retval BSP status
 */
int32_t BSP_LCD_GFXMMU_RegisterDefaultMspCallbacks(uint32_t Instance) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    __HAL_GFXMMU_RESET_HANDLE_STATE(&hlcd_gfxmmu);

    /* Register default MspInit/MspDeInit Callback */
    if (HAL_GFXMMU_RegisterCallback(&hlcd_gfxmmu, HAL_GFXMMU_MSPINIT_CB_ID,
                                    GFXMMU_MspInit) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else if (HAL_GFXMMU_RegisterCallback(&hlcd_gfxmmu,
                                           HAL_GFXMMU_MSPDEINIT_CB_ID,
                                           GFXMMU_MspDeInit) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else {
      LcdGfxmmu_IsMspCbValid[Instance] = 1U;
    }
  }

  /* BSP status */
  return status;
}

/**
 * @brief Register LCD GFXMMU Msp Callback
 * @param Callbacks pointer to LCD MspInit/MspDeInit callback functions
 * @retval BSP status
 */
int32_t BSP_LCD_GFXMMU_RegisterMspCallbacks(uint32_t Instance,
                                            BSP_LCD_GFXMMU_Cb_t *Callback) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    __HAL_GFXMMU_RESET_HANDLE_STATE(&hlcd_gfxmmu);

    /* Register MspInit/MspDeInit Callbacks */
    if (HAL_GFXMMU_RegisterCallback(&hlcd_gfxmmu, HAL_GFXMMU_MSPINIT_CB_ID,
                                    Callback->pMspGfxmmuInitCb) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else if (HAL_GFXMMU_RegisterCallback(
                   &hlcd_gfxmmu, HAL_GFXMMU_MSPDEINIT_CB_ID,
                   Callback->pMspGfxmmuDeInitCb) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else {
      LcdGfxmmu_IsMspCbValid[Instance] = 1U;
    }
  }

  /* BSP status */
  return status;
}
#endif /* USE_HAL_GFXMMU_REGISTER_CALLBACKS */

#if (USE_HAL_LTDC_REGISTER_CALLBACKS == 1)
/**
 * @brief  Register Default LCD LTDC Msp Callbacks
 * @retval BSP status
 */
int32_t BSP_LCD_LTDC_RegisterDefaultMspCallbacks(uint32_t Instance) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    __HAL_LTDC_RESET_HANDLE_STATE(&hlcd_ltdc);

    /* Register default MspInit/MspDeInit Callback */
    if (HAL_LTDC_RegisterCallback(&hlcd_ltdc, HAL_LTDC_MSPINIT_CB_ID,
                                  LTDC_MspInit) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else if (HAL_LTDC_RegisterCallback(&hlcd_ltdc, HAL_LTDC_MSPDEINIT_CB_ID,
                                         LTDC_MspDeInit) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else {
      LcdLtdc_IsMspCbValid[Instance] = 1U;
    }
  }

  /* BSP status */
  return status;
}

/**
 * @brief Register LCD LTDC Msp Callback
 * @param Callbacks pointer to LCD MspInit/MspDeInit callback functions
 * @retval BSP status
 */
int32_t BSP_LCD_LTDC_RegisterMspCallbacks(uint32_t Instance,
                                          BSP_LCD_LTDC_Cb_t *Callback) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    __HAL_LTDC_RESET_HANDLE_STATE(&hlcd_ltdc);

    /* Register MspInit/MspDeInit Callbacks */
    if (HAL_LTDC_RegisterCallback(&hlcd_ltdc, HAL_LTDC_MSPINIT_CB_ID,
                                  Callback->pMspLtdcInitCb) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else if (HAL_LTDC_RegisterCallback(&hlcd_ltdc, HAL_LTDC_MSPDEINIT_CB_ID,
                                         Callback->pMspLtdcDeInitCb) !=
               HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else {
      LcdLtdc_IsMspCbValid[Instance] = 1U;
    }
  }

  /* BSP status */
  return status;
}
#endif /* USE_HAL_LTDC_REGISTER_CALLBACKS */

#if (USE_HAL_DSI_REGISTER_CALLBACKS == 1)
/**
 * @brief  Register Default LCD DSI Msp Callbacks
 * @retval BSP status
 */
int32_t BSP_LCD_DSI_RegisterDefaultMspCallbacks(uint32_t Instance) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    __HAL_DSI_RESET_HANDLE_STATE(&hlcd_dsi);

    /* Register default MspInit/MspDeInit Callback */
    if (HAL_DSI_RegisterCallback(&hlcd_dsi, HAL_DSI_MSPINIT_CB_ID,
                                 DSI_MspInit) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else if (HAL_DSI_RegisterCallback(&hlcd_dsi, HAL_DSI_MSPDEINIT_CB_ID,
                                        DSI_MspDeInit) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else {
      LcdDsi_IsMspCbValid[Instance] = 1U;
    }
  }

  /* BSP status */
  return status;
}

/**
 * @brief Register LCD DSI Msp Callback
 * @param Callbacks pointer to LCD MspInit/MspDeInit callback functions
 * @retval BSP status
 */
int32_t BSP_LCD_DSI_RegisterMspCallbacks(uint32_t Instance,
                                         BSP_LCD_DSI_Cb_t *Callback) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    __HAL_DSI_RESET_HANDLE_STATE(&hlcd_dsi);

    /* Register MspInit/MspDeInit Callbacks */
    if (HAL_DSI_RegisterCallback(&hlcd_dsi, HAL_DSI_MSPINIT_CB_ID,
                                 Callback->pMspDsiInitCb) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else if (HAL_DSI_RegisterCallback(&hlcd_dsi, HAL_DSI_MSPDEINIT_CB_ID,
                                        Callback->pMspDsiDeInitCb) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else {
      LcdDsi_IsMspCbValid[Instance] = 1U;
    }
  }

  /* BSP status */
  return status;
}
#endif /* USE_HAL_DSI_REGISTER_CALLBACKS */

#if (USE_HAL_DMA2D_REGISTER_CALLBACKS == 1)
/**
 * @brief  Register Default LCD DMA2D Msp Callbacks
 * @retval BSP status
 */
int32_t BSP_LCD_DMA2D_RegisterDefaultMspCallbacks(uint32_t Instance) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    __HAL_DMA2D_RESET_HANDLE_STATE(&hlcd_dma2d);

    /* Register default MspInit/MspDeInit Callback */
    if (HAL_DMA2D_RegisterCallback(&hlcd_dma2d, HAL_DMA2D_MSPINIT_CB_ID,
                                   DMA2D_MspInit) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else if (HAL_DMA2D_RegisterCallback(&hlcd_dma2d,
                                          HAL_DMA2D_MSPDEINIT_CB_ID,
                                          DMA2D_MspDeInit) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else {
      LcdDma2d_IsMspCbValid[Instance] = 1U;
    }
  }

  /* BSP status */
  return status;
}

/**
 * @brief Register LCD DMA2D Msp Callback
 * @param Callbacks pointer to LCD MspInit/MspDeInit callback functions
 * @retval BSP status
 */
int32_t BSP_LCD_DMA2D_RegisterMspCallbacks(uint32_t Instance,
                                           BSP_LCD_DMA2D_Cb_t *Callback) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    __HAL_DMA2D_RESET_HANDLE_STATE(&hlcd_dma2d);

    /* Register MspInit/MspDeInit Callbacks */
    if (HAL_DMA2D_RegisterCallback(&hlcd_dma2d, HAL_DMA2D_MSPINIT_CB_ID,
                                   Callback->pMspDma2dInitCb) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else if (HAL_DMA2D_RegisterCallback(
                   &hlcd_dma2d, HAL_DMA2D_MSPDEINIT_CB_ID,
                   Callback->pMspDma2dDeInitCb) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else {
      LcdDma2d_IsMspCbValid[Instance] = 1U;
    }
  }

  /* BSP status */
  return status;
}
#endif /* USE_HAL_DMA2D_REGISTER_CALLBACKS */
/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_LCD_Private_Functions LCD Private Functions
 * @{
 */

/**
 * @brief  Initialize LCD.
 * @retval BSP status.
 */
static int32_t LCD_Init(void) {
  int32_t status = BSP_ERROR_NONE;
  uint32_t ErrorNumber = 0;
  DSI_PHY_TimerTypeDef PhyTimers = {0};
  DSI_HOST_TimeoutTypeDef HostTimeouts = {0};

  /***************/
  /* GFXMMU init */
  /***************/
#if (USE_HAL_GFXMMU_REGISTER_CALLBACKS == 0)
  GFXMMU_MspInit(&hlcd_gfxmmu);
#else
  /* Register the GFXMMU MSP Callbacks */
  if (LcdGfxmmu_IsMspCbValid[0] == 0U) {
    if (BSP_LCD_GFXMMU_RegisterDefaultMspCallbacks(0) != BSP_ERROR_NONE) {
      status = BSP_ERROR_PERIPH_FAILURE;
    }
  }
#endif /* (USE_HAL_GFXMMU_REGISTER_CALLBACKS == 0) */

  if (status == BSP_ERROR_NONE) {
    /* GFXMMU peripheral initialization */
    if (MX_GFXMMU_Init(&hlcd_gfxmmu) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    }
    /* Initialize LUT */
    else if (HAL_GFXMMU_ConfigLut(&hlcd_gfxmmu, 0, LCD_WIDTH,
                                  (uint32_t)&gfxmmu_lut_config) != HAL_OK) {
      status = BSP_ERROR_PERIPH_FAILURE;
    } else {
      /* Disable non visible lines : from line 480 to 1023 */
      if (HAL_OK != HAL_GFXMMU_DisableLutLines(&hlcd_gfxmmu, LCD_WIDTH, 544)) {
        status = BSP_ERROR_PERIPH_FAILURE;
      }
    }
  }

  /************/
  /* DSI init */
  /************/
  if (status == BSP_ERROR_NONE) {
#if (USE_HAL_DSI_REGISTER_CALLBACKS == 0)
    DSI_MspInit(&hlcd_dsi);
#else
    /* Register the DSI MSP Callbacks */
    if (LcdDsi_IsMspCbValid[0] == 0U) {
      if (BSP_LCD_DSI_RegisterDefaultMspCallbacks(0) != BSP_ERROR_NONE) {
        status = BSP_ERROR_PERIPH_FAILURE;
      }
    }
#endif /* (USE_HAL_DSI_REGISTER_CALLBACKS == 0) */

    if (status == BSP_ERROR_NONE) {
      /* DSI peripheral initialization */
      if (MX_DSI_Init(&hlcd_dsi) != HAL_OK) {
        status = BSP_ERROR_PERIPH_FAILURE;
      }
    }
  }

  /*********************/
  /* LCD configuration */
  /*********************/
  if (status == BSP_ERROR_NONE) {
    PhyTimers.ClockLaneHS2LPTime = 11;
    PhyTimers.ClockLaneLP2HSTime = 40;
    PhyTimers.DataLaneHS2LPTime = 12;
    PhyTimers.DataLaneLP2HSTime = 23;
    PhyTimers.DataLaneMaxReadTime = 0;
    PhyTimers.StopWaitTime = 7;

    if (HAL_DSI_ConfigPhyTimer(&hlcd_dsi, &PhyTimers) != HAL_OK) {
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

    if (HAL_DSI_ConfigHostTimeouts(&hlcd_dsi, &HostTimeouts) != HAL_OK) {
      return 7;
    }

    if (HAL_DSI_ConfigFlowControl(&hlcd_dsi, DSI_FLOW_CONTROL_BTA) != HAL_OK) {
      return 7;
    }

    /* Enable the DSI host */
    __HAL_DSI_ENABLE(&hlcd_dsi);

    /*************/
    /* LTDC init */
    /*************/
    if (status == BSP_ERROR_NONE) {
      if (MX_LTDC_ClockConfig(&hlcd_ltdc) != HAL_OK) {
        status = BSP_ERROR_PERIPH_FAILURE;
      } else {
#if (USE_HAL_LTDC_REGISTER_CALLBACKS == 0)
        LTDC_MspInit(&hlcd_ltdc);
#else
        /* Register the LTDC MSP Callbacks */
        if (LcdLtdc_IsMspCbValid[0] == 0U) {
          if (BSP_LCD_LTDC_RegisterDefaultMspCallbacks(0) != BSP_ERROR_NONE) {
            status = BSP_ERROR_PERIPH_FAILURE;
          }
        }
#endif /* (USE_HAL_GFXMMU_REGISTER_CALLBACKS == 0) */

        if (status == BSP_ERROR_NONE) {
          /* LTDC peripheral initialization */
          if (MX_LTDC_Init(&hlcd_ltdc) != HAL_OK) {
            status = BSP_ERROR_PERIPH_FAILURE;
          } else {
            if (MX_LTDC_ConfigLayer(&hlcd_ltdc, LTDC_LAYER_1,
                                    GFXMMU_VIRTUAL_BUFFER0_BASE_S) != HAL_OK) {
              status = BSP_ERROR_PERIPH_FAILURE;
            }
          }
        }
      }
    }

    /* Start DSI */
    if (HAL_DSI_Start(&(hlcd_dsi)) != HAL_OK) {
      return 8;
    }

    /* CMD Mode */
    uint8_t InitParam1[3] = {0xFF, 0x83, 0x79};
    if (HAL_DSI_LongWrite(&hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 3, 0xB9,
                          InitParam1) != HAL_OK) {
      ErrorNumber++;
    }

    /* SETPOWER */
    uint8_t InitParam2[16] = {0x44, 0x1C, 0x1C, 0x37, 0x57, 0x90, 0xD0, 0xE2,
                              0x58, 0x80, 0x38, 0x38, 0xF8, 0x33, 0x34, 0x42};
    if (HAL_DSI_LongWrite(&hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 16, 0xB1,
                          InitParam2) != HAL_OK) {
      ErrorNumber++;
    }

    /* SETDISP */
    uint8_t InitParam3[9] = {0x80, 0x14, 0x0C, 0x30, 0x20,
                             0x50, 0x11, 0x42, 0x1D};
    if (HAL_DSI_LongWrite(&hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 9, 0xB2,
                          InitParam3) != HAL_OK) {
      ErrorNumber++;
    }

    /* Set display cycle timing */
    uint8_t InitParam4[10] = {0x01, 0xAA, 0x01, 0xAF, 0x01,
                              0xAF, 0x10, 0xEA, 0x1C, 0xEA};
    if (HAL_DSI_LongWrite(&hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 10, 0xB4,
                          InitParam4) != HAL_OK) {
      ErrorNumber++;
    }

    /* SETVCOM */
    uint8_t InitParam5[4] = {00, 00, 00, 0xC0};
    if (HAL_DSI_LongWrite(&hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 4, 0xC7,
                          InitParam5) != HAL_OK) {
      ErrorNumber++;
    }

    /* Set Panel Related Registers */
    if (HAL_DSI_ShortWrite(&hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xCC,
                           0x02) != HAL_OK) {
      ErrorNumber++;
    }

    if (HAL_DSI_ShortWrite(&hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xD2,
                           0x77) != HAL_OK) {
      ErrorNumber++;
    }

    uint8_t InitParam6[37] = {0x00, 0x07, 0x00, 0x00, 0x00, 0x08, 0x08, 0x32,
                              0x10, 0x01, 0x00, 0x01, 0x03, 0x72, 0x03, 0x72,
                              0x00, 0x08, 0x00, 0x08, 0x33, 0x33, 0x05, 0x05,
                              0x37, 0x05, 0x05, 0x37, 0x0A, 0x00, 0x00, 0x00,
                              0x0A, 0x00, 0x01, 0x00, 0x0E};
    if (HAL_DSI_LongWrite(&hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 37, 0xD3,
                          InitParam6) != HAL_OK) {
      ErrorNumber++;
    }

    uint8_t InitParam7[34] = {
        0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x19, 0x19, 0x18, 0x18,
        0x18, 0x18, 0x19, 0x19, 0x01, 0x00, 0x03, 0x02, 0x05, 0x04, 0x07, 0x06,
        0x23, 0x22, 0x21, 0x20, 0x18, 0x18, 0x18, 0x18, 0x00, 0x00};
    if (HAL_DSI_LongWrite(&hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 34, 0xD5,
                          InitParam7) != HAL_OK) {
      ErrorNumber++;
    }

    uint8_t InitParam8[32] = {0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18, 0x18,
                              0x19, 0x19, 0x18, 0x18, 0x19, 0x19, 0x18, 0x18,
                              0x06, 0x07, 0x04, 0x05, 0x02, 0x03, 0x00, 0x01,
                              0x20, 0x21, 0x22, 0x23, 0x18, 0x18, 0x18, 0x18};
    if (HAL_DSI_LongWrite(&hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 35, 0xD6,
                          InitParam8) != HAL_OK) {
      ErrorNumber++;
    }

    /* SET GAMMA */
    uint8_t InitParam9[42] = {
        0x00, 0x16, 0x1B, 0x30, 0x36, 0x3F, 0x24, 0x40, 0x09, 0x0D, 0x0F,
        0x18, 0x0E, 0x11, 0x12, 0x11, 0x14, 0x07, 0x12, 0x13, 0x18, 0x00,
        0x17, 0x1C, 0x30, 0x36, 0x3F, 0x24, 0x40, 0x09, 0x0C, 0x0F, 0x18,
        0x0E, 0x11, 0x14, 0x11, 0x12, 0x07, 0x12, 0x14, 0x18};
    if (HAL_DSI_LongWrite(&hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 42, 0xE0,
                          InitParam9) != HAL_OK) {
      ErrorNumber++;
    }

    uint8_t InitParam10[3] = {0x2C, 0x2C, 00};
    if (HAL_DSI_LongWrite(&hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 3, 0xB6,
                          InitParam10) != HAL_OK) {
      ErrorNumber++;
    }

    if (HAL_DSI_ShortWrite(&hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xBD,
                           0x00) != HAL_OK) {
      ErrorNumber++;
    }

    uint8_t InitParam11[] = {
        0x01, 0x00, 0x07, 0x0F, 0x16, 0x1F, 0x27, 0x30, 0x38, 0x40, 0x47,
        0x4E, 0x56, 0x5D, 0x65, 0x6D, 0x74, 0x7D, 0x84, 0x8A, 0x90, 0x99,
        0xA1, 0xA9, 0xB0, 0xB6, 0xBD, 0xC4, 0xCD, 0xD4, 0xDD, 0xE5, 0xEC,
        0xF3, 0x36, 0x07, 0x1C, 0xC0, 0x1B, 0x01, 0xF1, 0x34, 0x00};
    if (HAL_DSI_LongWrite(&hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 42, 0xC1,
                          InitParam11) != HAL_OK) {
      ErrorNumber++;
    }

    if (HAL_DSI_ShortWrite(&hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xBD,
                           0x01) != HAL_OK) {
      ErrorNumber++;
    }

    uint8_t InitParam12[] = {
        0x00, 0x08, 0x0F, 0x16, 0x1F, 0x28, 0x31, 0x39, 0x41, 0x48, 0x51,
        0x59, 0x60, 0x68, 0x70, 0x78, 0x7F, 0x87, 0x8D, 0x94, 0x9C, 0xA3,
        0xAB, 0xB3, 0xB9, 0xC1, 0xC8, 0xD0, 0xD8, 0xE0, 0xE8, 0xEE, 0xF5,
        0x3B, 0x1A, 0xB6, 0xA0, 0x07, 0x45, 0xC5, 0x37, 0x00};
    if (HAL_DSI_LongWrite(&hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 42, 0xC1,
                          InitParam12) != HAL_OK) {
      ErrorNumber++;
    }

    if (HAL_DSI_ShortWrite(&hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xBD,
                           0x02) != HAL_OK) {
      ErrorNumber++;
    }

    uint8_t InitParam13[42] = {
        0x00, 0x09, 0x0F, 0x18, 0x21, 0x2A, 0x34, 0x3C, 0x45, 0x4C, 0x56,
        0x5E, 0x66, 0x6E, 0x76, 0x7E, 0x87, 0x8E, 0x95, 0x9D, 0xA6, 0xAF,
        0xB7, 0xBD, 0xC5, 0xCE, 0xD5, 0xDF, 0xE7, 0xEE, 0xF4, 0xFA, 0xFF,
        0x0C, 0x31, 0x83, 0x3C, 0x5B, 0x56, 0x1E, 0x5A, 0xFF};
    if (HAL_DSI_LongWrite(&hlcd_dsi, 0, DSI_DCS_LONG_PKT_WRITE, 42, 0xC1,
                          InitParam13) != HAL_OK) {
      ErrorNumber++;
    }

    if (HAL_DSI_ShortWrite(&hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1, 0xBD,
                           0x00) != HAL_OK) {
      ErrorNumber++;
    }

    /* Exit Sleep Mode*/
    if (HAL_DSI_ShortWrite(&hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x11,
                           0x00) != HAL_OK) {
      ErrorNumber++;
    }

    HAL_Delay(120);

    /* Display On */
    if (HAL_DSI_ShortWrite(&hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P0, 0x29,
                           0x00) != HAL_OK) {
      ErrorNumber++;
    }

    HAL_Delay(120);

    if (ErrorNumber != 0U) {
      status = BSP_ERROR_PERIPH_FAILURE;
    }
  }

  return status;
}

/**
 * @brief  De-Initialize LCD.
 * @retval BSP status.
 */
static int32_t LCD_DeInit(void) {
  int32_t status = BSP_ERROR_NONE;
  uint32_t ErrorNumber = 0;

  /* Disable DSI wrapper */
  __HAL_DSI_WRAPPER_DISABLE(&hlcd_dsi);

  /* Set display off */
  if (HAL_DSI_ShortWrite(&hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P1,
                         DSI_SET_DISPLAY_OFF, 0x00) != HAL_OK) {
    ErrorNumber++;
  }

  /* Wait before entering in sleep mode */
  HAL_Delay(2000);

  /* Put LCD in sleep mode */
  if (HAL_DSI_ShortWrite(&hlcd_dsi, 0, DSI_DCS_SHORT_PKT_WRITE_P0,
                         DSI_ENTER_SLEEP_MODE, 0x0) != HAL_OK) {
    ErrorNumber++;
  }

  HAL_Delay(120);

  /* De-initialize DSI */
  if (HAL_DSI_DeInit(&hlcd_dsi) != HAL_OK) {
    ErrorNumber++;
  }
#if (USE_HAL_DSI_REGISTER_CALLBACKS == 0)
  DSI_MspDeInit(&hlcd_dsi);
#endif /* (USE_HAL_DSI_REGISTER_CALLBACKS == 0) */

  /* De-initialize LTDC */
  if (HAL_LTDC_DeInit(&hlcd_ltdc) != HAL_OK) {
    ErrorNumber++;
  }
#if (USE_HAL_LTDC_REGISTER_CALLBACKS == 0)
  LTDC_MspDeInit(&hlcd_ltdc);
#endif /* (USE_HAL_LTDC_REGISTER_CALLBACKS == 0) */

  /* De-initialize GFXMMU */
  if (HAL_GFXMMU_DeInit(&hlcd_gfxmmu) != HAL_OK) {
    ErrorNumber++;
  }
#if (USE_HAL_GFXMMU_REGISTER_CALLBACKS == 0)
  GFXMMU_MspDeInit(&hlcd_gfxmmu);
#endif /* (USE_HAL_GFXMMU_REGISTER_CALLBACKS == 0) */

  if (ErrorNumber != 0U) {
    status = BSP_ERROR_PERIPH_FAILURE;
  }

  return status;
}

/**
 * @brief  Initialize GFXMMU MSP.
 * @param  hgfxmmu GFXMMU handle
 * @retval None
 */
static void GFXMMU_MspInit(GFXMMU_HandleTypeDef *hgfxmmu) {
  /* Prevent unused argument(s) compilation warning */
  UNUSED(hgfxmmu);

  /* GFXMMU clock enable */
  __HAL_RCC_GFXMMU_CLK_ENABLE();

  /* Enable GFXMMU interrupt */
  NVIC_SetPriority(GFXMMU_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(GFXMMU_IRQn);
}

/**
 * @brief  De-Initialize GFXMMU MSP.
 * @param  hgfxmmu GFXMMU handle
 * @retval None
 */
static void GFXMMU_MspDeInit(GFXMMU_HandleTypeDef *hgfxmmu) {
  /* Prevent unused argument(s) compilation warning */
  UNUSED(hgfxmmu);

  /* Disable GFXMMU interrupt */
  NVIC_DisableIRQ(GFXMMU_IRQn);

  /* GFXMMU clock disable */
  __HAL_RCC_GFXMMU_CLK_DISABLE();
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
  NVIC_SetPriority(LTDC_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(LTDC_IRQn);

  NVIC_SetPriority(LTDC_ER_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(LTDC_ER_IRQn);
}

/**
 * @brief  De-Initialize LTDC MSP.
 * @param  hltdc LTDC handle
 * @retval None
 */
static void LTDC_MspDeInit(LTDC_HandleTypeDef *hltdc) {
  /* Prevent unused argument(s) compilation warning */
  UNUSED(hltdc);

  /* Disable LTDC interrupts */
  NVIC_DisableIRQ(LTDC_ER_IRQn);
  NVIC_DisableIRQ(LTDC_IRQn);

  /* LTDC clock disable */
  __HAL_RCC_LTDC_CLK_DISABLE();
}

/**
 * @brief  Initialize DSI MSP.
 * @param  hdsi DSI handle
 * @retval None
 */
static void DSI_MspInit(DSI_HandleTypeDef *hdsi) {
  RCC_PeriphCLKInitTypeDef PLL3InitPeriph = {0};
  RCC_PeriphCLKInitTypeDef DSIPHYInitPeriph = {0};
  GPIO_InitTypeDef GPIO_InitStruct = {0};

  UNUSED(hdsi);

  /* Enable GPIOI & GPIOD clocks */
  __HAL_RCC_GPIOD_CLK_ENABLE();
  __HAL_RCC_GPIOI_CLK_ENABLE();

  /* Configure DSI Reset pin */
  GPIO_InitStruct.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct.Pull = GPIO_PULLDOWN;
  GPIO_InitStruct.Pin = GPIO_PIN_5;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);

  /* Configure LCD Backlight Pin */
  GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
  GPIO_InitStruct.Pull = GPIO_PULLUP;
  GPIO_InitStruct.Pin = GPIO_PIN_6;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  HAL_GPIO_Init(GPIOI, &GPIO_InitStruct);

  /* Enable DSI clock */
  __HAL_RCC_DSI_CLK_ENABLE();

  /** ################ Set DSI clock to D-PHY source clock ##################
   * **/

  /* Start and configurre PLL3 */
  /* HSE = 16MHZ */
  /* 16/(M=4)   = 4MHz input (min) */
  /* 4*(N=125)  = 500MHz VCO (almost max) */
  /* 500/(P=8)  = 62.5 for DSI ie exactly the lane byte clock*/

  PLL3InitPeriph.PeriphClockSelection = RCC_PERIPHCLK_DSI;
  PLL3InitPeriph.DsiClockSelection = RCC_DSICLKSOURCE_PLL3;
  PLL3InitPeriph.PLL3.PLL3M = 4;
  PLL3InitPeriph.PLL3.PLL3N = 125;
  PLL3InitPeriph.PLL3.PLL3P = 8;
  PLL3InitPeriph.PLL3.PLL3Q = 8;
  PLL3InitPeriph.PLL3.PLL3R = 24;
  PLL3InitPeriph.PLL3.PLL3FRACN = 0;
  PLL3InitPeriph.PLL3.PLL3RGE = RCC_PLLVCIRANGE_1;
  PLL3InitPeriph.PLL3.PLL3ClockOut = RCC_PLL3_DIVR | RCC_PLL3_DIVP;
  PLL3InitPeriph.PLL3.PLL3Source = RCC_PLLSOURCE_HSE;
  (void)HAL_RCCEx_PeriphCLKConfig(&PLL3InitPeriph);

  __HAL_RCC_DSI_CLK_ENABLE();

  /* Switch to D-PHY source clock */
  /* Enable the DSI host */
  hlcd_dsi.Instance = DSI;

  __HAL_DSI_ENABLE(&hlcd_dsi);

  /* Enable the DSI PLL */
  __HAL_DSI_PLL_ENABLE(&hlcd_dsi);

  HAL_Delay(1);

  /* Enable the clock lane and the digital section of the D-PHY   */
  hlcd_dsi.Instance->PCTLR |= (DSI_PCTLR_CKE | DSI_PCTLR_DEN);

  /* Set the TX escape clock division factor */
  hlcd_dsi.Instance->CCR = 4;

  HAL_Delay(1);

  /* Config DSI Clock to DSI PHY */
  DSIPHYInitPeriph.PeriphClockSelection = RCC_PERIPHCLK_DSI;
  DSIPHYInitPeriph.DsiClockSelection = RCC_DSICLKSOURCE_DSIPHY;

  (void)HAL_RCCEx_PeriphCLKConfig(&DSIPHYInitPeriph);

  /* Reset  */
  HAL_Delay(11);
  HAL_GPIO_WritePin(GPIOD, GPIO_PIN_5, GPIO_PIN_SET);
  HAL_Delay(150);

  /* Reset the TX escape clock division factor */
  hlcd_dsi.Instance->CCR &= ~DSI_CCR_TXECKDIV;

  /* Disable the DSI PLL */
  __HAL_DSI_PLL_DISABLE(&hlcd_dsi);

  /* Disable the DSI host */
  __HAL_DSI_DISABLE(&hlcd_dsi);

  /** #########################################################################
   * **/

  /* Enable DSI NVIC interrupt */
  /* Default is lowest priority level */
  NVIC_SetPriority(DSI_IRQn, IRQ_PRI_NORMAL);
  NVIC_EnableIRQ(DSI_IRQn);
}

/**
 * @brief  De-Initialize DSI MSP.
 * @param  hdsi DSI handle
 * @retval None
 */
static void DSI_MspDeInit(DSI_HandleTypeDef *hdsi) {
  RCC_PeriphCLKInitTypeDef PLL3InitPeriph = {0};

  UNUSED(hdsi);

  /* Switch to PLL3 before Disable */
  PLL3InitPeriph.PeriphClockSelection = RCC_PERIPHCLK_DSI;
  PLL3InitPeriph.DsiClockSelection = RCC_DSICLKSOURCE_PLL3;
  PLL3InitPeriph.PLL3.PLL3M = 4;
  PLL3InitPeriph.PLL3.PLL3N = 125;
  PLL3InitPeriph.PLL3.PLL3P = 8;
  PLL3InitPeriph.PLL3.PLL3Q = 8;
  PLL3InitPeriph.PLL3.PLL3R = 24;
  PLL3InitPeriph.PLL3.PLL3FRACN = 0;
  PLL3InitPeriph.PLL3.PLL3RGE = RCC_PLLVCIRANGE_1;
  PLL3InitPeriph.PLL3.PLL3ClockOut = RCC_PLL3_DIVR | RCC_PLL3_DIVP;
  PLL3InitPeriph.PLL3.PLL3Source = RCC_PLLSOURCE_HSE;
  (void)HAL_RCCEx_PeriphCLKConfig(&PLL3InitPeriph);

  /* DSI clock disable */
  __HAL_RCC_DSI_CLK_DISABLE();

  /** @brief Toggle Sw reset of DSI IP */
  __HAL_RCC_DSI_FORCE_RESET();
  __HAL_RCC_DSI_RELEASE_RESET();

  /* Disable DSI interrupts */
  NVIC_DisableIRQ(DSI_IRQn);
}

int32_t BSP_LCD_SetFrameBuffer(uint32_t Instance, uint32_t fb_addr) {
  int32_t status = BSP_ERROR_NONE;
  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    MX_LTDC_ConfigLayer(&hlcd_ltdc, 0, fb_addr);
  }

  return status;
}

int32_t BSP_LCD_Reinit(uint32_t Instance) {
  int32_t status = BSP_ERROR_NONE;
  if (Instance >= LCD_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    // Switch to D-PHY source clock
    // Enable the DSI host
    hlcd_dsi.Instance = DSI;

    MX_GFXMMU_Reinit(&hlcd_gfxmmu);
    MX_DSI_Reinit(&hlcd_dsi);
    MX_LTDC_Reinit(&hlcd_ltdc);
  }

  return status;
}

#endif
