/**
 ******************************************************************************
 * @file    card_emulation.h
 * @author  MMY Application Team
 * @brief   Implementation of Common CardEmulation parts
 ******************************************************************************
 ** This notice applies to any and all portions of this file
 * that are not between comment pairs USER CODE BEGIN and
 * USER CODE END. Other portions of this file, whether
 * inserted by the user or by software development tools
 * are owned by their respective copyright owners.
 *
 * COPYRIGHT(c) 2018 STMicroelectronics
 *
 ******************************************************************************
 */

/* Define to prevent recursive inclusion -------------------------------------*/
#pragma once

#ifdef __cplusplus
extern "C" {
#endif

/* Includes ------------------------------------------------------------------*/
#include <trezor_bsp.h>

/** @addtogroup X-CUBE-NFC6_Applications
 *  @brief Sample applications for X-NUCLEO-NFC06A1 STM32 expansion boards.
 *  @{
 */

/** @addtogroup CardEmulation
 *  @{
 */

/** @defgroup CE_CardEmul
 *  @brief Card Emulation management functions
 * @{
 */

/* Exported constants --------------------------------------------------------*/
/* T3T Information Block Bytes offset */
#define T3T_INFBLK_VER_OFFSET 0
#define T3T_INFBLK_NBR_OFFSET 1
#define T3T_INFBLK_NBW_OFFSET 2
#define T3T_INFBLK_NMAXB_OFFSET 3
#define T3T_INFBLK_WRITEFLAG_OFFSET 9
#define T3T_INFBLK_RWFLAG_OFFSET 10
#define T3T_INFBLK_LN_OFFSET 11
#define T3T_INFBCK_CHECKSUM_OFFSET 14

/* T3T Information Block WriteFlag values */
#define T3T_WRITEFLAG_OFF 0x00
#define T3T_WRITEFLAG_ON 0x0F

/* T3T COMMAND OFFSET */
#define T3T_CHECK_RESP_CMD_OFFSET 0
#define T3T_CHECK_RESP_NFCID2_OFFSET 1
#define T3T_CHECK_RESP_SF1_OFFSET 9
#define T3T_CHECK_RESP_SF2_OFFSET 10
#define T3T_CHECK_RESP_NOB_OFFSET 11
#define T3T_CHECK_RESP_DATA_OFFSET 12
#define T3T_UPDATE_RESP_CMD_OFFSET 0
#define T3T_UPDATE_RESP_NFCID2_OFFSET 1
#define T3T_UPDATE_RESP_SF1_OFFSET 9
#define T3T_UPDATE_RESP_SF2_OFFSET 10

/* External variables --------------------------------------------------------*/
/* Exported macro ------------------------------------------------------------*/
/* Exported functions ------------------------------------------------------- */
/** @defgroup CE_CardEmul_Exported_functions
 *  @{
 */
void card_emulation_init(const uint8_t *nfcfNfcid);
uint16_t card_emulation_t3t(uint8_t *rxData, uint16_t rxDataLen, uint8_t *txBuf,
                            uint16_t txBufLen);
uint16_t card_emulation_t4t(uint8_t *rxData, uint16_t rxDataLen, uint8_t *txBuf,
                            uint16_t txBufLen);

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

#ifdef __cplusplus
}
#endif

/******************* (C) COPYRIGHT 2018 STMicroelectronics *****END OF FILE****/
