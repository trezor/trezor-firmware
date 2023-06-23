#include "stm32f4xx_ll_sdmmc.h"

// this function is adapted from stm32f4xx_ll_sdmmc.c

static uint32_t SDMMC_GetCmdResp1(SDIO_TypeDef *SDIOx, uint8_t SD_CMD,
                                  uint32_t Timeout) {
  /* 8 is the number of required instructions cycles for the below loop
  statement. The Timeout is expressed in ms */
  register uint32_t count = Timeout * (SystemCoreClock / 8U / 1000U);

  do {
    if (count-- == 0U) {
      return SDMMC_ERROR_TIMEOUT;
    }
  } while (!__SDIO_GET_FLAG(
      SDIOx, SDIO_FLAG_CCRCFAIL | SDIO_FLAG_CMDREND | SDIO_FLAG_CTIMEOUT));

  if (__SDIO_GET_FLAG(SDIOx, SDIO_FLAG_CTIMEOUT)) {
    __SDIO_CLEAR_FLAG(SDIOx, SDIO_FLAG_CTIMEOUT);
    return SDMMC_ERROR_CMD_RSP_TIMEOUT;
  } else if (__SDIO_GET_FLAG(SDIOx, SDIO_FLAG_CCRCFAIL)) {
    __SDIO_CLEAR_FLAG(SDIOx, SDIO_FLAG_CCRCFAIL);
    return SDMMC_ERROR_CMD_CRC_FAIL;
  }

  /* Check response received is of desired command */
  if (SDIO_GetCommandResponse(SDIOx) != SD_CMD) {
    return SDMMC_ERROR_CMD_CRC_FAIL;
  }

  /* Clear all the static flags */
  __SDIO_CLEAR_FLAG(SDIOx, SDIO_STATIC_FLAGS);

  /* We have received response, retrieve it for analysis  */
  uint32_t response_r1 = SDIO_GetResponse(SDIOx, SDIO_RESP1);

  if ((response_r1 & SDMMC_OCR_ERRORBITS) == SDMMC_ALLZERO) {
    return SDMMC_ERROR_NONE;
  } else {
    return SDMMC_ERROR_GENERAL_UNKNOWN_ERR;
  }
}

// this function is inspired by functions in stm32f4xx_ll_sdmmc.c

uint32_t SDMMC_CmdSetClrCardDetect(SDIO_TypeDef *SDIOx, uint32_t Argument) {
  SDIO_CmdInitTypeDef sdmmc_cmdinit;
  uint32_t errorstate = SDMMC_ERROR_NONE;

  sdmmc_cmdinit.Argument = (uint32_t)Argument;
  sdmmc_cmdinit.CmdIndex = SDMMC_CMD_SD_APP_SET_CLR_CARD_DETECT;
  sdmmc_cmdinit.Response = SDIO_RESPONSE_SHORT;
  sdmmc_cmdinit.WaitForInterrupt = SDIO_WAIT_NO;
  sdmmc_cmdinit.CPSM = SDIO_CPSM_ENABLE;
  SDIO_SendCommand(SDIOx, &sdmmc_cmdinit);

  errorstate = SDMMC_GetCmdResp1(SDIOx, SDMMC_CMD_SD_APP_SET_CLR_CARD_DETECT,
                                 SDIO_CMDTIMEOUT);

  return errorstate;
}
