// clang-format off

/**
  ******************************************************************************
  * @file    usbd_conf_template.h
  * @author  MCD Application Team
  * @brief   Header file for the usbd_conf_template.c file
  ******************************************************************************
  * @attention
  *
  * <h2><center>&copy; Copyright (c) 2015 STMicroelectronics.
  * All rights reserved.</center></h2>
  *
  * This software component is licensed by ST under Ultimate Liberty license
  * SLA0044, the "License"; You may not use this file except in compliance with
  * the License. You may obtain a copy of the License at:
  *                      http://www.st.com/SLA0044
  *
  ******************************************************************************
  */

/* Define to prevent recursive inclusion -------------------------------------*/
#ifndef __USBD_CONF_H
#define __USBD_CONF_H

/* Includes ------------------------------------------------------------------*/
#include STM32_HAL_H
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Exported types ------------------------------------------------------------*/
/* Exported constants --------------------------------------------------------*/
/* Common Config */
#define USB_PHY_FS_ID                         0
#define USB_PHY_HS_ID                         1
#define USBD_MAX_NUM_INTERFACES               8
#define USBD_MAX_NUM_CONFIGURATION            1
#define USBD_SUPPORT_USER_STRING              1
#define USBD_SELF_POWERED                     0
#define USBD_DEBUG_LEVEL                      0
#define USBD_LPM_ENABLED                      1

/* Exported macro ------------------------------------------------------------*/
/* Memory management macros */
/*
these should not be used because the GC is reset on a soft reset but the usb is not
#include "gc.h"
#define USBD_malloc               gc_alloc
#define USBD_free                 gc_free
#define USBD_memset               memset
#define USBD_memcpy               memcpy
*/

/* DEBUG macros */
#if (USBD_DEBUG_LEVEL > 0U)
#define  USBD_UsrLog(...)   do { \
                            printf(__VA_ARGS__); \
                            printf("\n"); \
} while (0)
#else
#define USBD_UsrLog(...) do {} while (0)
#endif

#if (USBD_DEBUG_LEVEL > 1U)

#define  USBD_ErrLog(...) do { \
                            printf("ERROR: ") ; \
                            printf(__VA_ARGS__); \
                            printf("\n"); \
} while (0)
#else
#define USBD_ErrLog(...) do {} while (0)
#endif

#if (USBD_DEBUG_LEVEL > 2U)
#define  USBD_DbgLog(...)   do { \
                            printf("DEBUG : ") ; \
                            printf(__VA_ARGS__); \
                            printf("\n"); \
} while (0)
#else
#define USBD_DbgLog(...) do {} while (0)
#endif

/* Exported functions ------------------------------------------------------- */

#endif /* __USBD_CONF_H */

/************************ (C) COPYRIGHT STMicroelectronics *****END OF FILE****/
