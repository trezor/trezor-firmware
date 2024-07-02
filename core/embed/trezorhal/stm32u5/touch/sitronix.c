#include STM32_HAL_H
#include TREZOR_BOARD

#include "i2c.h"

/** @addtogroup STM32U5x9J_DISCOVERY
 * @{
 */

/** @addtogroup STM32U5x9J_DISCOVERY_BUS
 * @{
 */
/** @defgroup STM32U5x9J_DISCOVERY_BUS_Exported_Types BUS Exported Types
 * @{
 */
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

/* BSP OSPI error codes */
#define BSP_ERROR_OSPI_SUSPENDED -20
#define BSP_ERROR_OSPI_MMP_UNLOCK_FAILURE -21
#define BSP_ERROR_OSPI_MMP_LOCK_FAILURE -22

/* BSP HSPI error codes */
#define BSP_ERROR_HSPI_MMP_UNLOCK_FAILURE -31
#define BSP_ERROR_HSPI_MMP_LOCK_FAILURE -32

/* BSP BUS error codes */
#define BSP_ERROR_BUS_TRANSACTION_FAILURE -100
#define BSP_ERROR_BUS_ARBITRATION_LOSS -101
#define BSP_ERROR_BUS_ACKNOWLEDGE_FAILURE -102
#define BSP_ERROR_BUS_PROTOCOL_FAILURE -103

#define BSP_ERROR_BUS_MODE_FAULT -104
#define BSP_ERROR_BUS_FRAME_ERROR -105
#define BSP_ERROR_BUS_CRC_ERROR -106
#define BSP_ERROR_BUS_DMA_FAILURE -107

/* TS I2C address */
#define TS_I2C_ADDRESS 0xE0U

/*******************************************************************************
 * Function Name : sitronix_read_reg
 * Description   : Generic Reading function. It must be full-filled with either
 *                 I2C or SPI reading functions
 * Input         : Register Address, length of buffer
 * Output        : pdata Read
 *******************************************************************************/
int32_t sitronix_read_reg(uint8_t reg, uint8_t *pdata, uint16_t length) {
  return i2c_mem_read(TOUCH_I2C_INSTANCE, TS_I2C_ADDRESS, reg, length, pdata,
                      length, 1000);
}

/*******************************************************************************
 * Function Name : sitronix_write_reg
 * Description   : Generic Writing function. It must be full-filled with either
 *                 I2C or SPI writing function
 * Input         : Register Address, pdata to be written, length of buffer
 * Output        : None
 *******************************************************************************/
int32_t sitronix_write_reg(uint8_t reg, uint8_t *pdata, uint16_t length) {
  return i2c_mem_write(TOUCH_I2C_INSTANCE, TS_I2C_ADDRESS, reg, length, pdata,
                       length, 1000);
}

/*******************************************************************************
 * Function Name : sitronix_read_data
 * Description   : Generic Reading function. It must be full-filled with either
 *                 I2C or SPI reading functions
 * Input         : Register Address, length of buffer
 * Output        : pdata Read
 *******************************************************************************/
int32_t sitronix_read_data(uint8_t *pdata, uint16_t length) {
  return i2c_receive(TOUCH_I2C_INSTANCE, TS_I2C_ADDRESS, pdata, length, 1000);
}

/* Includes ------------------------------------------------------------------*/
/* Macros --------------------------------------------------------------------*/
/* Exported types ------------------------------------------------------------*/
/* Exported constants --------------------------------------------------------*/
#define SITRONIX_MAX_X_LENGTH 480U
#define SITRONIX_MAX_Y_LENGTH 480U

/** @defgroup SITRONIX_Exported_Constants SITRONIX Exported Constants
 * @{
 */
#define SITRONIX_OK (0)
#define SITRONIX_ERROR (-1)

/* Max detectable simultaneous touches */
#define SITRONIX_MAX_DETECTABLE_TOUCH 10U

/* Touch FT6XX6 IDs */
#define SITRONIX_ID 0x02U

/* Values Pn_XH and Pn_YH related */
#define SITRONIX_TOUCH_EVT_FLAG_PRESS_DOWN 0x20U
#define SITRONIX_TOUCH_EVT_FLAG_LIFT_UP 0x60U
#define SITRONIX_TOUCH_EVT_FLAG_CONTACT 0x80U
#define SITRONIX_TOUCH_EVT_FLAG_NO_EVENT 0x00U
#define SITRONIX_TOUCH_POS_MSB_MASK 0x07U
#define SITRONIX_TOUCH_POS_LSB_MASK 0x70U

/* Point 1 registers */
#define SITRONIX_P1_XH_REG 0x09U
#define SITRONIX_P1_XL_REG 0x0AU
#define SITRONIX_P1_YH_REG 0x0BU
#define SITRONIX_P1_YL_REG 0x0CU

/**
 * @}
 */

/* Exported types ------------------------------------------------------------*/

/** @defgroup SITRONIX_Exported_Types SITRONIX Exported Types
 * @{
 */
typedef struct {
  uint32_t Radian;
  uint32_t OffsetLeftRight;
  uint32_t OffsetUpDown;
  uint32_t DistanceLeftRight;
  uint32_t DistanceUpDown;
  uint32_t DistanceZoom;
} SITRONIX_Gesture_Init_t;

typedef struct {
  uint32_t TouchDetected;
  uint32_t TouchX;
  uint32_t TouchY;
} SITRONIX_State_t;

typedef struct {
  uint32_t TouchDetected;
  uint32_t TouchX[SITRONIX_MAX_DETECTABLE_TOUCH];
  uint32_t TouchY[SITRONIX_MAX_DETECTABLE_TOUCH];
  uint32_t TouchWeight[SITRONIX_MAX_DETECTABLE_TOUCH];
  uint32_t TouchEvent[SITRONIX_MAX_DETECTABLE_TOUCH];
  uint32_t TouchArea[SITRONIX_MAX_DETECTABLE_TOUCH];
} SITRONIX_MultiTouch_State_t;

typedef struct {
  uint8_t IsInitialized;
} SITRONIX_Object_t;

typedef struct {
  uint8_t MultiTouch;
  uint8_t Gesture;
  uint8_t MaxTouch;
  uint32_t MaxXl;
  uint32_t MaxYl;
} SITRONIX_Capabilities_t;

typedef struct {
  int32_t (*Init)(SITRONIX_Object_t *);
  int32_t (*DeInit)(SITRONIX_Object_t *);
  int32_t (*GestureConfig)(SITRONIX_Object_t *, SITRONIX_Gesture_Init_t *);
  int32_t (*ReadID)(SITRONIX_Object_t *, uint32_t *);
  int32_t (*GetState)(SITRONIX_Object_t *, SITRONIX_State_t *);
  int32_t (*GetMultiTouchState)(SITRONIX_Object_t *,
                                SITRONIX_MultiTouch_State_t *);
  int32_t (*GetGesture)(SITRONIX_Object_t *, uint8_t *);
  int32_t (*GetCapabilities)(SITRONIX_Object_t *, SITRONIX_Capabilities_t *);
  int32_t (*EnableIT)(SITRONIX_Object_t *);
  int32_t (*DisableIT)(SITRONIX_Object_t *);
  int32_t (*ClearIT)(SITRONIX_Object_t *);
  int32_t (*ITStatus)(SITRONIX_Object_t *);
} SITRONIX_TS_Drv_t;

int32_t SITRONIX_Init(SITRONIX_Object_t *pObj);
int32_t SITRONIX_DeInit(SITRONIX_Object_t *pObj);
int32_t SITRONIX_GestureConfig(SITRONIX_Object_t *pObj,
                               SITRONIX_Gesture_Init_t *GestureInit);
int32_t SITRONIX_ReadID(SITRONIX_Object_t *pObj, uint32_t *Id);
int32_t SITRONIX_GetState(SITRONIX_Object_t *pObj, SITRONIX_State_t *State);
int32_t SITRONIX_GetMultiTouchState(SITRONIX_Object_t *pObj,
                                    SITRONIX_MultiTouch_State_t *State);
int32_t SITRONIX_GetGesture(SITRONIX_Object_t *pObj, uint8_t *GestureId);
int32_t SITRONIX_EnableIT(SITRONIX_Object_t *pObj);
int32_t SITRONIX_DisableIT(SITRONIX_Object_t *pObj);
int32_t SITRONIX_ITStatus(SITRONIX_Object_t *pObj);
int32_t SITRONIX_ClearIT(SITRONIX_Object_t *pObj);
int32_t SITRONIX_GetCapabilities(SITRONIX_Object_t *pObj,
                                 SITRONIX_Capabilities_t *Capabilities);

/* Touch screen driver structure initialization */
SITRONIX_TS_Drv_t SITRONIX_TS_Driver = {
    SITRONIX_Init,       SITRONIX_DeInit,          SITRONIX_GestureConfig,
    SITRONIX_ReadID,     SITRONIX_GetState,        SITRONIX_GetMultiTouchState,
    SITRONIX_GetGesture, SITRONIX_GetCapabilities, SITRONIX_EnableIT,
    SITRONIX_DisableIT,  SITRONIX_ClearIT,         SITRONIX_ITStatus};
/**
 * @}
 */

/** @defgroup SITRONIX_Private_Function_Prototypes SITRONIX Private Function
 * Prototypes
 * @{
 */
#if (SITRONIX_AUTO_CALIBRATION_ENABLED == 1)
static int32_t SITRONIX_TS_Calibration(SITRONIX_Object_t *pObj);
static int32_t SITRONIX_Delay(SITRONIX_Object_t *pObj, uint32_t Delay);
#endif /* SITRONIX_AUTO_CALIBRATION_ENABLED == 1 */
static int32_t SITRONIX_DetectTouch(SITRONIX_Object_t *pObj);
// static int32_t ReadRegWrap(void *handle, uint8_t Reg, uint8_t *Data,
//                            uint16_t Length);
// static int32_t WriteRegWrap(void *handle, uint8_t Reg, uint8_t *Data,
//                             uint16_t Length);
// static int32_t ReadDataWrap(void *handle, uint8_t *pData, uint16_t Length);

/**
 * @}
 */

/** @defgroup SITRONIX_Exported_Functions SITRONIX Exported Functions
 * @{
 */

/**
 * @brief  Get SITRONIX sensor capabilities
 * @param  pObj Component object pointer
 * @param  Capabilities pointer to SITRONIX sensor capabilities
 * @retval Component status
 */
int32_t SITRONIX_GetCapabilities(SITRONIX_Object_t *pObj,
                                 SITRONIX_Capabilities_t *Capabilities) {
  /* Prevent unused argument(s) compilation warning */
  (void)(pObj);

  /* Store component's capabilities */
  Capabilities->MultiTouch = 1;
  Capabilities->Gesture =
      0; /* Gesture feature is currently not activated on FW chipset */
  Capabilities->MaxTouch = SITRONIX_MAX_DETECTABLE_TOUCH;
  Capabilities->MaxXl = SITRONIX_MAX_X_LENGTH;
  Capabilities->MaxYl = SITRONIX_MAX_Y_LENGTH;

  return SITRONIX_OK;
}

/**
 * @brief  Initialize the SITRONIX communication bus
 *         from MCU to SITRONIX : ie I2C channel initialization (if required).
 * @param  pObj Component object pointer
 * @retval Component status
 */
int32_t SITRONIX_Init(SITRONIX_Object_t *pObj) {
  int32_t ret = SITRONIX_OK;
  uint8_t data[28U];

  if (pObj->IsInitialized == 0U) {
    if (sitronix_read_data(data, (uint16_t)sizeof(data)) != SITRONIX_OK) {
      ret = SITRONIX_ERROR;
    }

    pObj->IsInitialized = 1;
  }

  if (ret != SITRONIX_OK) {
    ret = SITRONIX_ERROR;
  }

  return ret;
}

/**
 * @brief  De-Initialize the SITRONIX communication bus
 *         from MCU to SITRONIX : ie I2C channel initialization (if required).
 * @param  pObj Component object pointer
 * @retval Component status
 */
int32_t SITRONIX_DeInit(SITRONIX_Object_t *pObj) {
  if (pObj->IsInitialized == 1U) {
    pObj->IsInitialized = 0;
  }

  return SITRONIX_OK;
}

/**
 * @brief  Configure the SITRONIX gesture
 *         from MCU to SITRONIX : ie I2C channel initialization (if required).
 * @param  pObj  Component object pointer
 * @param  GestureInit Gesture init structure
 * @retval Component status
 */
int32_t SITRONIX_GestureConfig(SITRONIX_Object_t *pObj,
                               SITRONIX_Gesture_Init_t *GestureInit) {
  return SITRONIX_ERROR;
}

/**
 * @brief  Read the SITRONIX device ID, pre initialize I2C in case of need to be
 *         able to read the SITRONIX device ID, and verify this is a SITRONIX.
 * @param  pObj Component object pointer
 * @param  Id Pointer to component's ID
 * @retval Component status
 */
int32_t SITRONIX_ReadID(SITRONIX_Object_t *pObj, uint32_t *Id) {
  int32_t ret = SITRONIX_OK;
  uint8_t data[28];
  uint8_t trial = 0;

  for (trial = 0; trial < 10; trial++) {
    if (sitronix_read_data(data, 28) != SITRONIX_OK) {
      ret = SITRONIX_ERROR;
    } else {
      if ((uint32_t)data[0] == SITRONIX_ID) {
        *Id = (uint32_t)data[0];
        return ret;
      }
    }
  }
  return ret;
}

uint8_t sitronix_touching = 0;

/**
 * @brief  Get the touch screen X and Y positions values
 * @param  pObj Component object pointer
 * @param  State Single Touch structure pointer
 * @retval Component status.
 */
int32_t SITRONIX_GetState(SITRONIX_Object_t *pObj, SITRONIX_State_t *State) {
  int32_t ret = SITRONIX_OK;
  uint8_t data[64];

  State->TouchDetected = (uint32_t)SITRONIX_DetectTouch(pObj);
  if (sitronix_read_data(data, (uint16_t)sizeof(data)) != SITRONIX_OK) {
    ret = SITRONIX_ERROR;
  } else {
    if ((uint32_t)data[2] & 0x80) {
      sitronix_touching = 1;
    } else {
      sitronix_touching = 0;
    }

    State->TouchX = (((uint32_t)data[2] & SITRONIX_TOUCH_POS_LSB_MASK) << 4);

    /* Send back first ready X position to caller */
    State->TouchX = ((((uint32_t)data[2] & SITRONIX_TOUCH_POS_LSB_MASK) << 4) |
                     ((uint32_t)data[3]));
    /* Send back first ready Y position to caller */
    State->TouchY = (((uint32_t)data[2] & SITRONIX_TOUCH_POS_MSB_MASK) << 8) |
                    ((uint32_t)data[4]);
  }

  return ret;
}
/**
 * @brief  Get the touch screen Xn and Yn positions values in multi-touch mode
 * @param  pObj Component object pointer
 * @param  State Multi Touch structure pointer
 * @retval Component status.
 */
int32_t SITRONIX_GetMultiTouchState(SITRONIX_Object_t *pObj,
                                    SITRONIX_MultiTouch_State_t *State) {
  int32_t ret = SITRONIX_OK;
  uint8_t data[28];

  State->TouchDetected = (uint32_t)SITRONIX_DetectTouch(pObj);

  if (sitronix_read_reg(SITRONIX_P1_XH_REG, data, (uint16_t)sizeof(data)) !=
      SITRONIX_OK) {
    ret = SITRONIX_ERROR;
  } else {
    /* To be implemented */
  }

  return ret;
}

/**
 * @brief  Get Gesture ID
 * @param  pObj Component object pointer
 * @param  GestureId gesture ID
 * @retval Component status
 */
int32_t SITRONIX_GetGesture(SITRONIX_Object_t *pObj, uint8_t *GestureId) {
  /* Prevent unused argument(s) compilation warning */
  (void)(pObj);

  /* Always return SITRONIX_OK as feature not supported by SITRONIX */
  return SITRONIX_ERROR;
}

/**
 * @brief  Configure the SITRONIX device to generate IT on given INT pin
 *         connected to MCU as EXTI.
 * @param  pObj Component object pointer
 * @retval Component status
 */
int32_t SITRONIX_EnableIT(SITRONIX_Object_t *pObj) {
  /* Prevent unused argument(s) compilation warning */
  (void)(pObj);

  /* Always return SITRONIX_OK as feature not supported by SITRONIX */
  return SITRONIX_ERROR;
}

/**
 * @brief  Configure the SITRONIX device to stop generating IT on the given INT
 * pin connected to MCU as EXTI.
 * @param  pObj Component object pointer
 * @retval Component status
 */
int32_t SITRONIX_DisableIT(SITRONIX_Object_t *pObj) {
  /* Prevent unused argument(s) compilation warning */
  (void)(pObj);

  /* Always return SITRONIX_OK as feature not supported by SITRONIX */
  return SITRONIX_ERROR;
}

/**
 * @brief  Get IT status from SITRONIX interrupt status registers
 *         Should be called Following an EXTI coming to the MCU to know the
 * detailed reason of the interrupt.
 *         @note : This feature is not supported by SITRONIX.
 * @param  pObj Component object pointer
 * @retval Component status
 */
int32_t SITRONIX_ITStatus(SITRONIX_Object_t *pObj) {
  /* Prevent unused argument(s) compilation warning */
  (void)(pObj);

  /* Always return SITRONIX_OK as feature not supported by SITRONIX */
  return SITRONIX_ERROR;
}

/**
 * @brief  Clear IT status in SITRONIX interrupt status clear registers
 *         Should be called Following an EXTI coming to the MCU.
 *         @note : This feature is not supported by SITRONIX.
 * @param  pObj Component object pointer
 * @retval Component status
 */
int32_t SITRONIX_ClearIT(SITRONIX_Object_t *pObj) {
  /* Prevent unused argument(s) compilation warning */
  (void)(pObj);

  /* Always return SITRONIX_OK as feature not supported by SITRONIX */
  return SITRONIX_ERROR;
}

/**
 * @}
 */

/** @defgroup SITRONIX_Private_Functions SITRONIX Private Functions
 * @{
 */

/**
 * @brief  Return if there is touches detected or not.
 *         Try to detect new touches and forget the old ones (reset internal
 * global variables).
 * @param  pObj Component object pointer
 * @retval Number of active touches detected (can be between 0 and10) or
 * SITRONIX_ERROR in case of error
 */
__attribute__((optimize("-O0"))) int32_t SITRONIX_DetectTouch(
    SITRONIX_Object_t *pObj) {
  int32_t ret;
  uint8_t nb_touch = 0;
  static uint8_t first_event = 0;
  uint8_t data[28];

  if (sitronix_read_data((uint8_t *)&data, 28) != SITRONIX_OK) {
    ret = SITRONIX_ERROR;
  } else {
    if (first_event == 0) {
      if ((data[0] == 0x09)) {
        nb_touch = 1;
        first_event = 1;
      } else {
        nb_touch = 0;
      }
    } else {
      if (data[8] == 0x60) {
        nb_touch = 0;
      } else {
        nb_touch = 1;
      }
    }
    ret = (int32_t)nb_touch;
  }

  return ret;
}
//
///**
// * @brief  Wrap IO bus read function to component register red function
// * @param  handle Component object handle
// * @param  Reg The target register address to read
// * @param  pData The target register value to be read
// * @param  Length buffer size to be read
// * @retval Component status.
// */
// static int32_t ReadRegWrap(void *handle, uint8_t Reg, uint8_t *pData,
//                           uint16_t Length) {
//  return i2c_mem_read(TOUCH_I2C_INSTANCE, TS_I2C_ADDRESS, Reg, Length, pData,
//  Length, 1000);
//}
//
///**
// * @brief  Wrap IO bus write function to component register write function
// * @param  handle Component object handle
// * @param  Reg The target register address to write
// * @param  pData The target register value to be written
// * @param  Length buffer size to be written
// * @retval Component status.
// */
// static int32_t WriteRegWrap(void *handle, uint8_t Reg, uint8_t *pData,
//                            uint16_t Length) {
//  return i2c_mem_write(TOUCH_I2C_INSTANCE, TS_I2C_ADDRESS, Reg, Length, pData,
//  Length, 1000);
//}
//
///**
// * @brief  Wrap IO bus read function to component register red function
// * @param  handle Component object handle
// * @param  pData The target register value to be read
// * @param  Length buffer size to be read
// * @retval Component status.
// */
// static int32_t ReadDataWrap(void *handle, uint8_t *pData, uint16_t Length) {
//  return i2c_receive(TOUCH_I2C_INSTANCE, TS_I2C_ADDRESS, pData, Length, 1000);
//}

/**
  ******************************************************************************
  * @file    stm32u5x9j_discovery_ts.c
  * @author  MCD Application Team
  * @brief   This file provides a set of functions needed to manage the Touch
  *          Screen on STM32U5x9J-DISCOVERY board.
  @verbatim
  1. How To use this driver:
  --------------------------
   - This driver is used to drive the touch screen module of the
  STM32U5x9J-DISCOVERY board on the LCD mounted on MB1829A daughter board. The
  touch screen driver IC is a SITRONIX.

  2. Driver description:
  ---------------------
    + Initialization steps:
       o Initialize the TS using the BSP_TS_Init() function. You can select
         display orientation with "Orientation" parameter of TS_Init_t structure
         (portrait, landscape, portrait with 180 degrees rotation or landscape
         with 180 degrees rotation). The LCD size properties (width and height)
         are also parameters of TS_Init_t and depend on the orientation
  selected.

    + Touch screen use
       o Call BSP_TS_EnableIT() (BSP_TS_DisableIT()) to enable (disable) touch
         screen interrupt. BSP_TS_Callback() is called when TS interrupt occurs.
       o Call BSP_TS_GetState() to get the current touch status (detection and
         coordinates).
       o Call BSP_TS_Set_Orientation() to change the current orientation.
         Call BSP_TS_Get_Orientation() to get the current orientation.
       o Call BSP_TS_GetCapabilities() to get the SITRONIX capabilities.
       o SITRONIX doesn't support multi touch and gesture features.
         BSP_TS_Get_MultiTouchState(), BSP_TS_GestureConfig() and
         BSP_TS_GetGestureId() functions will return
  BSP_ERROR_FEATURE_NOT_SUPPORTED.

    + De-initialization steps:
       o De-initialize the touch screen using the BSP_TS_DeInit() function.

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
/* TS instances */
#define TS_INSTANCES_NBR 1U
#define TS_TOUCH_NBR 10U

/* TS orientations */
#define TS_ORIENTATION_PORTRAIT 0U
#define TS_ORIENTATION_LANDSCAPE 1U
#define TS_ORIENTATION_PORTRAIT_ROT180 2U
#define TS_ORIENTATION_LANDSCAPE_ROT180 3U

/** @defgroup STM32U5x9J_DISCOVERY_TS_Exported_Types TS Exported Types
 * @{
 */
typedef struct {
  uint32_t Width;       /* Screen width */
  uint32_t Height;      /* Screen height */
  uint32_t Orientation; /* Touch screen orientation */
  uint32_t Accuracy;    /* Expressed in pixel and means the x or y difference vs
                         old    position to consider the new values valid */
} TS_Init_t;

typedef struct {
  uint8_t MultiTouch;
  uint8_t Gesture;
  uint8_t MaxTouch;
  uint32_t MaxXl;
  uint32_t MaxYl;
} TS_Capabilities_t;

typedef struct {
  uint32_t TouchDetected;
  uint32_t TouchX;
  uint32_t TouchY;
} TS_State_t;

typedef struct {
  uint32_t TouchDetected;
  uint32_t TouchX[2];
  uint32_t TouchY[2];
  uint32_t TouchWeight[2];
  uint32_t TouchEvent[2];
  uint32_t TouchArea[2];
} TS_MultiTouch_State_t;

typedef struct {
  uint32_t Radian;
  uint32_t OffsetLeftRight;
  uint32_t OffsetUpDown;
  uint32_t DistanceLeftRight;
  uint32_t DistanceUpDown;
  uint32_t DistanceZoom;
} TS_Gesture_Config_t;

typedef struct {
  uint32_t Width;
  uint32_t Height;
  uint32_t Orientation;
  uint32_t Accuracy;
  uint32_t MaxX;
  uint32_t MaxY;
  uint32_t PreviousX[TS_TOUCH_NBR];
  uint32_t PreviousY[TS_TOUCH_NBR];
} TS_Ctx_t;

typedef struct {
  int32_t (*Init)(void *);
  int32_t (*DeInit)(void *);
  int32_t (*GestureConfig)(void *, void *);
  int32_t (*ReadID)(void *, uint32_t *);
  int32_t (*GetState)(void *, void *);
  int32_t (*GetMultiTouchState)(void *, void *);
  int32_t (*GetGesture)(void *, void *);
  int32_t (*GetCapabilities)(void *, void *);
  int32_t (*EnableIT)(void *);
  int32_t (*DisableIT)(void *);
  int32_t (*ClearIT)(void *);
  int32_t (*ITStatus)(void *);
} TS_Drv_t;

/* DSI TS INT pin */
#define TS_INT_PIN GPIO_PIN_8
#define TS_INT_GPIO_PORT GPIOE
#define TS_INT_GPIO_CLK_ENABLE() __HAL_RCC_GPIOE_CLK_ENABLE()
#define TS_INT_GPIO_CLK_DISABLE() __HAL_RCC_GPIOE_CLK_DISABLE()
#define TS_INT_EXTI_IRQn EXTI8_IRQn

/* Includes ------------------------------------------------------------------*/
// #include "stm32u5x9j_discovery_ts.h"
// #include "stm32u5x9j_discovery.h"

/** @addtogroup BSP
 * @{
 */

/** @addtogroup STM32U5x9J_DISCOVERY
 * @{
 */

/** @defgroup STM32U5x9J_DISCOVERY_TS TS
 * @{
 */

/** @defgroup STM32U5x9J_DISCOVERY_TS_Private_Defines TS Private Defines
 * @{
 */
/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_TS_Private_TypesDefinitions TS Private
 * TypesDefinitions
 * @{
 */
typedef void (*BSP_EXTI_LineCallback)(void);
/**
 * @}
 */

/** @addtogroup STM32U5x9J_DISCOVERY_TS_Exported_Variables TS Exported Variables
 * @{
 */
void *Ts_CompObj[TS_INSTANCES_NBR] = {0};
TS_Drv_t *Ts_Drv[TS_INSTANCES_NBR] = {0};
TS_Ctx_t Ts_Ctx[TS_INSTANCES_NBR] = {0};
EXTI_HandleTypeDef hts_exti[TS_INSTANCES_NBR];
IRQn_Type Ts_IRQn[TS_INSTANCES_NBR] = {EXTI15_IRQn};

/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_TS_Private_FunctionPrototypes TS Private
 * Function Prototypes
 * @{
 */
static int32_t SITRONIX_Probe(uint32_t Instance);

/**
 * @}
 */

/** @addtogroup STM32U5x9J_DISCOVERY_TS_Exported_Functions
 * @{
 */
/**
 * @brief  Initialize the TS.
 * @param  Instance TS Instance.
 * @param  TS_Init  Pointer to TS initialization structure.
 * @retval BSP status.
 */
int32_t BSP_TS_Init(uint32_t Instance, TS_Init_t *TS_Init) {
  int32_t status = BSP_ERROR_NONE;

  if ((TS_Init == NULL) || (Instance >= TS_INSTANCES_NBR)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Probe the TS driver */
    if (SITRONIX_Probe(Instance) != BSP_ERROR_NONE) {
      status = BSP_ERROR_COMPONENT_FAILURE;
    } else {
      TS_Capabilities_t Capabilities;
      uint32_t i;
      /* Store parameters on TS context */
      Ts_Ctx[Instance].Width = TS_Init->Width;
      Ts_Ctx[Instance].Height = TS_Init->Height;
      Ts_Ctx[Instance].Orientation = TS_Init->Orientation;
      Ts_Ctx[Instance].Accuracy = TS_Init->Accuracy;
      /* Get capabilities to retrieve maximum values of X and Y */
      if (Ts_Drv[Instance]->GetCapabilities(Ts_CompObj[Instance],
                                            &Capabilities) < 0) {
        status = BSP_ERROR_COMPONENT_FAILURE;
      } else {
        /* Store maximum X and Y on context */
        Ts_Ctx[Instance].MaxX = Capabilities.MaxXl;
        Ts_Ctx[Instance].MaxY = Capabilities.MaxYl;
        /* Initialize previous position in order to always detect first touch */
        for (i = 0; i < TS_TOUCH_NBR; i++) {
          Ts_Ctx[Instance].PreviousX[i] =
              TS_Init->Width + TS_Init->Accuracy + 1U;
          Ts_Ctx[Instance].PreviousY[i] =
              TS_Init->Height + TS_Init->Accuracy + 1U;
        }
      }
    }
  }

  return status;
}

/**
 * @brief  De-Initialize the TS.
 * @param  Instance TS Instance.
 * @retval BSP status.
 */
int32_t BSP_TS_DeInit(uint32_t Instance) {
  int32_t status = BSP_ERROR_NONE;

  if (Instance >= TS_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* De-Init the TS driver */
    if (Ts_Drv[Instance]->DeInit(Ts_CompObj[Instance]) < 0) {
      status = BSP_ERROR_COMPONENT_FAILURE;
    }
  }

  return status;
}

/**
 * @brief  Enable the TS interrupt.
 * @param  Instance TS Instance.
 * @retval BSP status.
 */
int32_t BSP_TS_EnableIT(uint32_t Instance) {
  /* Prevent unused argument(s) compilation warning */
  UNUSED(Instance);

  GPIO_InitTypeDef gpio_init_structure = {0};

  __HAL_RCC_GPIOE_CLK_ENABLE();

  /* Configure Interrupt mode for TS detection pin */
  gpio_init_structure.Pin = TS_INT_PIN;
  gpio_init_structure.Pull = GPIO_PULLUP;
  gpio_init_structure.Speed = GPIO_SPEED_FREQ_HIGH;
  gpio_init_structure.Mode = GPIO_MODE_IT_FALLING;
  HAL_GPIO_Init(TS_INT_GPIO_PORT, &gpio_init_structure);

  /* Enable and set Touch screen EXTI Interrupt to the lowest priority */
  HAL_NVIC_SetPriority((IRQn_Type)(TS_INT_EXTI_IRQn), 0x0F, 0x00);
  HAL_NVIC_EnableIRQ((IRQn_Type)(TS_INT_EXTI_IRQn));

  return BSP_ERROR_NONE;
}

/**
 * @brief  Disable the TS interrupt.
 * @param  Instance TS Instance.
 * @retval BSP status.
 */
int32_t BSP_TS_DisableIT(uint32_t Instance) {
  /* Prevent unused argument(s) compilation warning */
  UNUSED(Instance);

  /* To be Implemented */
  return BSP_ERROR_NONE;
}

/**
 * @brief  Set the TS orientation.
 * @param  Instance TS Instance.
 * @param  Orientation TS orientation.
 * @retval BSP status.
 */
int32_t BSP_TS_Set_Orientation(uint32_t Instance, uint32_t Orientation) {
  int32_t status = BSP_ERROR_NONE;
  uint32_t temp;
  uint32_t i;

  if ((Instance >= TS_INSTANCES_NBR) ||
      (Orientation > TS_ORIENTATION_LANDSCAPE_ROT180)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Update TS context if orientation is changed from/to portrait to/from
     * landscape */
    if ((((Ts_Ctx[Instance].Orientation == TS_ORIENTATION_LANDSCAPE) ||
          (Ts_Ctx[Instance].Orientation == TS_ORIENTATION_LANDSCAPE_ROT180)) &&
         ((Orientation == TS_ORIENTATION_PORTRAIT) ||
          (Orientation == TS_ORIENTATION_PORTRAIT_ROT180))) ||
        (((Ts_Ctx[Instance].Orientation == TS_ORIENTATION_PORTRAIT) ||
          (Ts_Ctx[Instance].Orientation == TS_ORIENTATION_PORTRAIT_ROT180)) &&
         ((Orientation == TS_ORIENTATION_LANDSCAPE) ||
          (Orientation == TS_ORIENTATION_LANDSCAPE_ROT180)))) {
      /* Invert width and height */
      temp = Ts_Ctx[Instance].Width;
      Ts_Ctx[Instance].Width = Ts_Ctx[Instance].Height;
      Ts_Ctx[Instance].Height = temp;
      /* Invert MaxX and MaxY */
      temp = Ts_Ctx[Instance].MaxX;
      Ts_Ctx[Instance].MaxX = Ts_Ctx[Instance].MaxY;
      Ts_Ctx[Instance].MaxY = temp;
    }
    /* Store orientation on TS context */
    Ts_Ctx[Instance].Orientation = Orientation;
    /* Reset previous position */
    for (i = 0; i < TS_TOUCH_NBR; i++) {
      Ts_Ctx[Instance].PreviousX[i] =
          Ts_Ctx[Instance].Width + Ts_Ctx[Instance].Accuracy + 1U;
      Ts_Ctx[Instance].PreviousY[i] =
          Ts_Ctx[Instance].Height + Ts_Ctx[Instance].Accuracy + 1U;
    }
  }

  return status;
}

/**
 * @brief  Get the TS orientation.
 * @param  Instance TS Instance.
 * @param  Orientation Pointer to TS orientation.
 * @retval BSP status.
 */
int32_t BSP_TS_Get_Orientation(uint32_t Instance, uint32_t *Orientation) {
  int32_t status = BSP_ERROR_NONE;

  if ((Instance >= TS_INSTANCES_NBR) || (Orientation == NULL)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Get orientation from TS context */
    *Orientation = Ts_Ctx[Instance].Orientation;
  }

  return status;
}

/**
 * @brief  Get position of a single touch.
 * @param  Instance TS Instance.
 * @param  TS_State Pointer to single touch structure.
 * @retval BSP status.
 */
int32_t BSP_TS_GetState(uint32_t Instance, TS_State_t *TS_State) {
  int32_t status = BSP_ERROR_NONE;
  uint32_t x_oriented;
  uint32_t y_oriented;
  uint32_t x_diff;
  uint32_t y_diff;

  if (Instance >= TS_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    SITRONIX_State_t state;

    /* Get each touch coordinates */
    if (Ts_Drv[Instance]->GetState(Ts_CompObj[Instance], &state) < 0) {
      status = BSP_ERROR_COMPONENT_FAILURE;
    } /* Check and update the number of touches active detected */
    else if (state.TouchDetected != 0U) {
      x_oriented = /*Ts_Ctx[Instance].MaxX -*/ state.TouchX;
      y_oriented = /*Ts_Ctx[Instance].MaxY -*/ state.TouchY;

      /* Apply boundary */
      TS_State->TouchX =
          (x_oriented * Ts_Ctx[Instance].Width) / (Ts_Ctx[Instance].MaxX);
      TS_State->TouchY =
          (y_oriented * Ts_Ctx[Instance].Height) / (Ts_Ctx[Instance].MaxY);
      /* Store Current TS state */
      TS_State->TouchDetected = state.TouchDetected;

      /* Check accuracy */
      x_diff = (TS_State->TouchX > Ts_Ctx[Instance].PreviousX[0])
                   ? (TS_State->TouchX - Ts_Ctx[Instance].PreviousX[0])
                   : (Ts_Ctx[Instance].PreviousX[0] - TS_State->TouchX);

      y_diff = (TS_State->TouchY > Ts_Ctx[Instance].PreviousY[0])
                   ? (TS_State->TouchY - Ts_Ctx[Instance].PreviousY[0])
                   : (Ts_Ctx[Instance].PreviousY[0] - TS_State->TouchY);

      if ((x_diff > Ts_Ctx[Instance].Accuracy) ||
          (y_diff > Ts_Ctx[Instance].Accuracy)) {
        /* New touch detected */
        Ts_Ctx[Instance].PreviousX[0] = TS_State->TouchX;
        Ts_Ctx[Instance].PreviousY[0] = TS_State->TouchY;
      } else {
        TS_State->TouchX = Ts_Ctx[Instance].PreviousX[0];
        TS_State->TouchY = Ts_Ctx[Instance].PreviousY[0];
      }
    } else {
      TS_State->TouchDetected = 0U;
      TS_State->TouchX = Ts_Ctx[Instance].PreviousX[0];
      TS_State->TouchY = Ts_Ctx[Instance].PreviousY[0];
    }
  }

  return status;
}

/**
 * @brief  Get positions of multiple touch.
 * @param  Instance TS Instance.
 * @param  TS_State Pointer to multiple touch structure.
 * @retval BSP status.
 */
int32_t BSP_TS_Get_MultiTouchState(const uint32_t Instance,
                                   TS_MultiTouch_State_t *TS_State) {
  int32_t status;

  UNUSED(TS_State);

  if (Instance >= TS_INSTANCES_NBR) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Feature not supported in this release */
    status = BSP_ERROR_FEATURE_NOT_SUPPORTED;
  }

  return status;
}

/**
 * @brief  Configure gesture on TS.
 * @param  Instance TS Instance.
 * @param  GestureConfig Pointer to gesture configuration structure.
 * @retval BSP status.
 */
int32_t BSP_TS_GestureConfig(const uint32_t Instance,
                             TS_Gesture_Config_t *GestureConfig) {
  int32_t status;

  if ((Instance >= TS_INSTANCES_NBR) || (GestureConfig == NULL)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Feature not supported */
    status = BSP_ERROR_FEATURE_NOT_SUPPORTED;
  }

  return status;
}

/**
 * @brief  Get gesture.
 * @param  Instance TS Instance.
 * @param  GestureId Pointer to gesture.
 * @retval BSP status.
 */
int32_t BSP_TS_GetGestureId(const uint32_t Instance, uint32_t *GestureId) {
  int32_t status;

  if ((Instance >= TS_INSTANCES_NBR) || (GestureId == NULL)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Feature not supported */
    status = BSP_ERROR_FEATURE_NOT_SUPPORTED;
  }

  return status;
}

/**
 * @brief  Get the TS capabilities.
 * @param  Instance TS Instance.
 * @param  Capabilities Pointer to TS capabilities structure.
 * @retval BSP status.
 */
int32_t BSP_TS_GetCapabilities(uint32_t Instance,
                               TS_Capabilities_t *Capabilities) {
  int32_t status = BSP_ERROR_NONE;

  if ((Instance >= TS_INSTANCES_NBR) || (Capabilities == NULL)) {
    status = BSP_ERROR_WRONG_PARAM;
  } else {
    /* Get the TS driver capabilities */
    if (Ts_Drv[Instance]->GetCapabilities(Ts_CompObj[Instance], Capabilities) <
        0) {
      status = BSP_ERROR_COMPONENT_FAILURE;
    } else {
      /* Update maximum X and Y according orientation */
      if ((Ts_Ctx[Instance].Orientation == TS_ORIENTATION_LANDSCAPE) ||
          (Ts_Ctx[Instance].Orientation == TS_ORIENTATION_LANDSCAPE_ROT180)) {
        uint32_t tmp;
        tmp = Capabilities->MaxXl;
        Capabilities->MaxXl = Capabilities->MaxYl;
        Capabilities->MaxYl = tmp;
      }
    }
  }

  return status;
}

/**
 * @brief  TS Callback.
 * @param  Instance TS Instance.
 * @retval None.
 */
__weak void BSP_TS_Callback(uint32_t Instance) {
  /* Prevent unused argument(s) compilation warning */
  UNUSED(Instance);

  /* This function should be implemented by the user application.
     It is called into this driver when an event on TS touch detection */
}

/**
 * @brief  BSP TS interrupt handler.
 * @param  Instance TS Instance.
 * @retval None.
 */
void BSP_TS_IRQHandler(uint32_t Instance) {
  /* Prevent unused argument(s) compilation warning */
  UNUSED(Instance);

  /* To be implemented */
}
/**
 * @}
 */

/** @defgroup STM32U5x9J_DISCOVERY_TS_Private_Functions TS Private Functions
 * @{
 */
/**
 * @brief  Probe the SITRONIX TS driver.
 * @param  Instance TS Instance.
 * @retval BSP status.
 */
static int32_t SITRONIX_Probe(uint32_t Instance) {
  int32_t status;
  static SITRONIX_Object_t SITRONIXObj;

  Ts_CompObj[Instance] = &SITRONIXObj;
  Ts_Drv[Instance] = (TS_Drv_t *)&SITRONIX_TS_Driver;
  if (Ts_Drv[Instance]->Init(Ts_CompObj[Instance]) < 0) {
    status = BSP_ERROR_COMPONENT_FAILURE;
  } else {
    status = BSP_ERROR_NONE;
  }

  return status;
}

/**
 * @}
 */

/**
 * @}
 */

/**
 * @}
 */

/**
 * @}
 */

#include <string.h>
#include "touch.h"

// Touch driver
typedef struct {
  // Set if driver is initialized
  secbool initialized;
  // Last lower-level driver state
  TS_State_t prev_state;

} touch_driver_t;

// Touch driver instance
static touch_driver_t g_touch_driver = {
    .initialized = secfalse,
};

secbool touch_init(void) {
  touch_driver_t *driver = &g_touch_driver;

  if (sectrue != driver->initialized) {
    TS_Init_t TsInit;

    /* Initialize the TouchScreen */
    TsInit.Width = 480;
    TsInit.Height = 480;
    TsInit.Orientation = 0;
    TsInit.Accuracy = 10;

    BSP_TS_Init(0, &TsInit);

    driver->initialized = sectrue;
  }

  return driver->initialized;
}

void touch_deinit(void) {
  touch_driver_t *driver = &g_touch_driver;

  if (sectrue == driver->initialized) {
    BSP_TS_DeInit(0);
    memset(driver, 0, sizeof(touch_driver_t));
  }
}

secbool touch_ready(void) {
  touch_driver_t *driver = &g_touch_driver;
  return driver->initialized;
}

secbool touch_set_sensitivity(uint8_t value) {
  // Not implemented for the discovery kit
  return sectrue;
}

uint8_t touch_get_version(void) {
  // Not implemented for the discovery kit
  return 0;
}

secbool touch_activity(void) {
  touch_driver_t *driver = &g_touch_driver;

  if (sectrue != driver->initialized) {
    return secfalse;
  }

  TS_State_t new_state = {0};
  BSP_TS_GetState(0, &new_state);

  return sitronix_touching ? sectrue : secfalse;
}

uint32_t touch_get_event(void) {
  touch_driver_t *driver = &g_touch_driver;

  if (sectrue != driver->initialized) {
    return 0;
  }

  TS_State_t new_state = {0};
  BSP_TS_GetState(0, &new_state);

  new_state.TouchDetected = (sitronix_touching != 0);
  new_state.TouchX = new_state.TouchX > 120 ? new_state.TouchX - 120 : 0;
  new_state.TouchY = new_state.TouchY > 120 ? new_state.TouchY - 120 : 0;

  uint32_t event = 0;

  if (new_state.TouchDetected && !driver->prev_state.TouchDetected) {
    uint32_t xy = touch_pack_xy(new_state.TouchX, new_state.TouchY);
    event = TOUCH_START | xy;
  } else if (!new_state.TouchDetected && driver->prev_state.TouchDetected) {
    uint32_t xy =
        touch_pack_xy(driver->prev_state.TouchX, driver->prev_state.TouchY);
    event = TOUCH_END | xy;
  } else if (new_state.TouchDetected) {
    if ((new_state.TouchX != driver->prev_state.TouchX) ||
        (new_state.TouchY != driver->prev_state.TouchY)) {
      uint32_t xy = touch_pack_xy(new_state.TouchX, new_state.TouchY);
      event = TOUCH_MOVE | xy;
    }
  }

  driver->prev_state = new_state;

  return event;
}
