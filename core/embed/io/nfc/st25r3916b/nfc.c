
#include <sys/irq.h>
#include <sys/systick.h>
#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include "../inc/io/nfc.h"
#include "nfc_internal.h"
#include "rfal_platform.h"

#include "../rfal/include/rfal_nfca.h"
#include "../rfal/include/rfal_rf.h"
#include "../rfal/include/rfal_utils.h"

#include "stm32u5xx_hal.h"

typedef struct {
  bool initialized;
  // SPI driver
  SPI_HandleTypeDef hspi;
  // NFC IRQ pin callback
  void (*nfc_irq_callback)(void);
  EXTI_HandleTypeDef hEXTI;
} st25r3916b_driver_t;

static st25r3916b_driver_t g_st25r3916b_driver = {
    .initialized = false,
};

nfc_status_t nfc_init() {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  if (drv->initialized) {
    return NFC_OK;
  }

  // Enable clock of relevant peripherals
  // SPI + GPIO ports
  SPI_INSTANCE_3_CLK_EN();
  SPI_INSTANCE_3_MISO_CLK_EN();
  SPI_INSTANCE_3_MOSI_CLK_EN();
  SPI_INSTANCE_3_SCK_CLK_EN();
  SPI_INSTANCE_3_NSS_CLK_EN();

  // SPI peripheral pin config
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStruct.Alternate = SPI_INSTANCE_3_PIN_AF;

  GPIO_InitStruct.Pin = SPI_INSTANCE_3_MISO_PIN;
  HAL_GPIO_Init(SPI_INSTANCE_3_MISO_PORT, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = SPI_INSTANCE_3_MOSI_PIN;
  HAL_GPIO_Init(SPI_INSTANCE_3_MOSI_PORT, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = SPI_INSTANCE_3_SCK_PIN;
  HAL_GPIO_Init(SPI_INSTANCE_3_SCK_PORT, &GPIO_InitStruct);

  // NSS pin controled by software, set as classical GPIO
  GPIO_InitTypeDef GPIO_InitStruct_nss = {0};
  GPIO_InitStruct_nss.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct_nss.Pull = GPIO_NOPULL;
  GPIO_InitStruct_nss.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStruct_nss.Pin = SPI_INSTANCE_3_NSS_PIN;
  HAL_GPIO_Init(SPI_INSTANCE_3_NSS_PORT, &GPIO_InitStruct_nss);

  // NFC IRQ pin
  GPIO_InitTypeDef GPIO_InitStructure_int = {0};
  GPIO_InitStructure_int.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure_int.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure_int.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure_int.Pin = NFC_INT_PIN;
  HAL_GPIO_Init(NFC_INT_PORT, &GPIO_InitStructure_int);

  memset(&(drv->hspi), 0, sizeof(drv->hspi));

  drv->hspi.Instance = SPI_INSTANCE_3;
  drv->hspi.Init.Mode = SPI_MODE_MASTER;
  drv->hspi.Init.BaudRatePrescaler =
      SPI_BAUDRATEPRESCALER_32;  // TODO: Calculate frequency precisly.
  drv->hspi.Init.DataSize = SPI_DATASIZE_8BIT;
  drv->hspi.Init.Direction = SPI_DIRECTION_2LINES;
  drv->hspi.Init.CLKPolarity = SPI_POLARITY_LOW;
  drv->hspi.Init.CLKPhase = SPI_PHASE_2EDGE;
  drv->hspi.Init.NSS = SPI_NSS_SOFT;  // For rfal lib purpose, use software NSS
  drv->hspi.Init.NSSPolarity = SPI_NSS_POLARITY_LOW;
  drv->hspi.Init.NSSPMode = SPI_NSS_PULSE_DISABLE;

  EXTI_ConfigTypeDef EXTI_Config = {0};
  EXTI_Config.GPIOSel = NFC_EXTI_INTERRUPT_GPIOSEL;
  EXTI_Config.Line = NFC_EXTI_INTERRUPT_LINE;
  EXTI_Config.Mode = EXTI_MODE_INTERRUPT;
  EXTI_Config.Trigger = EXTI_TRIGGER_RISING;
  HAL_EXTI_SetConfigLine(&drv->hEXTI, &EXTI_Config);
  NVIC_SetPriority(NFC_EXTI_INTERRUPT_NUM, IRQ_PRI_NORMAL);
  __HAL_GPIO_EXTI_CLEAR_FLAG(NFC_INT_PIN);
  NVIC_EnableIRQ(NFC_EXTI_INTERRUPT_NUM);

  HAL_StatusTypeDef status;

  status = HAL_SPI_Init(&(drv->hspi));

  if (status != HAL_OK) {
    return false;
  }

  ReturnCode ret_code = rfalInitialize();
  if (ret_code != RFAL_ERR_NONE) {
    return NFC_INITIALIZATION_FAILED;
  }

  drv->initialized = true;

  return NFC_OK;
}

nfc_status_t nfc_deinit() {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  if (!drv->initialized) {
    return NFC_OK;
  }

  HAL_EXTI_ClearConfigLine(&drv->hEXTI);
  NVIC_DisableIRQ(NFC_EXTI_INTERRUPT_NUM);

  ReturnCode ret_code = rfalDeinitialize();

  if (ret_code != RFAL_ERR_NONE) {
    return NFC_ERROR;
  }

  HAL_SPI_DeInit(&(drv->hspi));

  HAL_GPIO_DeInit(SPI_INSTANCE_3_MISO_PORT, SPI_INSTANCE_3_MISO_PIN);
  HAL_GPIO_DeInit(SPI_INSTANCE_3_MOSI_PORT, SPI_INSTANCE_3_MOSI_PIN);
  HAL_GPIO_DeInit(SPI_INSTANCE_3_SCK_PORT, SPI_INSTANCE_3_SCK_PIN);
  HAL_GPIO_DeInit(SPI_INSTANCE_3_NSS_PORT, SPI_INSTANCE_3_NSS_PIN);
  HAL_GPIO_DeInit(NFC_INT_PORT, NFC_INT_PIN);

  drv->initialized = false;

  return NFC_OK;
}

HAL_StatusTypeDef nfc_spi_transmit_receive(const uint8_t *txData,
                                           uint8_t *rxData, uint16_t length) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;
  HAL_StatusTypeDef status;

  if ((txData != NULL) && (rxData == NULL)) {
    status = HAL_SPI_Transmit(&(drv->hspi), (uint8_t *)txData, length, 1000);
  } else if ((txData == NULL) && (rxData != NULL)) {
    status = HAL_SPI_Receive(&(drv->hspi), rxData, length, 1000);
  } else {
    status = HAL_SPI_TransmitReceive(&(drv->hspi), (uint8_t *)txData, rxData,
                                     length, 1000);
  }

  return status;
}

uint32_t nfc_create_timer(uint16_t time) { return (systick_ms() + time); }

bool nfc_timer_is_expired(uint32_t timer) {

  uint32_t u_diff;
  int32_t s_diff;

  u_diff = (timer - systick_ms()); // Calculate the diff between the timers
  s_diff = u_diff;                 // Convert the diff to a signed var

  // Check if the given timer has expired already
  if (s_diff < 0) {
    return true;
  }

  return false;
}

void nfc_ext_irq_set_callback(void (*cb)(void)) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;
  drv->nfc_irq_callback = cb;
}

void NFC_EXTI_INTERRUPT_HANDLER(void) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  // Clear the EXTI line pending bit
  __HAL_GPIO_EXTI_CLEAR_FLAG(NFC_INT_PIN);
  if (drv->nfc_irq_callback != NULL) {
    drv->nfc_irq_callback();
  }
}

#define EXAMPLE_NFCA_DEVICES 10

void nfc_poll_type_A() {
  /*
  ******************************************************************************
  * GLOBAL FUNCTIONS
  ******************************************************************************
  */
  ReturnCode err;
  rfalNfcaSensRes sensRes;
  rfalNfcaSelRes selRes;
  rfalNfcaListenDevice nfcaDevList[EXAMPLE_NFCA_DEVICES];
  uint8_t devCnt;
  uint8_t devIt;

  rfalInitialize();

  for (;;) {
    rfalFieldOff(); /* Turn the Field Off */
    platformDelay(500);
    rfalNfcaPollerInitialize(); /* Initialize RFAL for NFC-A */
    rfalFieldOnAndStartGT();    /* Turns the Field On and starts GT timer */

    /*******************************************************************************/
    /* Perform NFC-A Technology detection */
    err = rfalNfcaPollerTechnologyDetection(
        RFAL_COMPLIANCE_MODE_NFC, &sensRes); /* Poll for nearby NFC-A devices */

    if (err == RFAL_ERR_NONE) /* NFC-A type card found */
    {
      return;
      /*******************************************************************************/
      /* Perform NFC-A Collision Resolution */
      err = rfalNfcaPollerFullCollisionResolution(
          RFAL_COMPLIANCE_MODE_NFC, EXAMPLE_NFCA_DEVICES, nfcaDevList,
          &devCnt); /* Perform collision avoidance */
      if ((err == RFAL_ERR_NONE) && (devCnt > 0)) {
        platformLog("NFC-A device(s) found %d\r\n", devCnt);
        devIt = 0; /* Use the first device on the list */
        /*******************************************************************************/
        /* Check if desired device is in Sleep */
        if (nfcaDevList[devIt].isSleep) {
          err = rfalNfcaPollerCheckPresence(RFAL_14443A_SHORTFRAME_CMD_WUPA,
                                            &sensRes); /* Wake up all cards */
          if (err != RFAL_ERR_NONE) {
            continue;
          }
          err = rfalNfcaPollerSelect(nfcaDevList[devIt].nfcId1,
                                     nfcaDevList[devIt].nfcId1Len,
                                     &selRes); /* Select specific device */
          if (err != RFAL_ERR_NONE) {
            continue;
          }
        }
        /*******************************************************************************/
        /* Perform protocol specific activation */
        switch (nfcaDevList[devIt].type) {
          case RFAL_NFCA_T1T:
            /* No further activation needed for a T1T (RID already
             * performed)*/
            platformLog(
                "NFC-A T1T device found \r\n"); /* NFC-A T1T device fained in:
                                                   t1tRidRes.uid */
            /* Following communications shall be performed using:
             * - Non blocking: rfalStartTransceive() +
             * rfalGetTransceiveState()
             * - Blocking: rfalTransceiveBlockingTx() +
             * rfalTransceiveBlockingRx() or rfalTransceiveBlockingTxRx() */
            break;
          case RFAL_NFCA_T2T:
            /* No specific activation needed for a T2T */
            platformLog(
                "NFC-A T2T device found \r\n"); /* NFC-A T2T device found,
                                                   NFCID/UID is contained in:
                                                   nfcaDev.nfcid */
            /* Following communications shall be perforound,
                                                   NFCID/UID is contmed using:
             * - Non blocking: rfalStartTransceive() +
             * rfalGetTransceiveState()
             * - Blocking: rfalTransceiveBlockingTx() +
             * rfalTransceiveBlockingRx() or rfalTransceiveBlockingTxRx() */
            break;
          case RFAL_NFCA_T4T:
            platformLog(
                "NFC-A T4T (ISO-DEP) device found \r\n"); /* NFC-A T4T device
                                                             found, NFCID/UID
                                                             is contained in:
                                                             nfcaDev.nfcid */
            /* Activation should continue using
             * rfalIsoDepPollAHandleActivation(), see exampleRfalPoller.c */
            break;
          case RFAL_NFCA_T4T_NFCDEP: /* Device supports T4T and NFC-DEP */
          case RFAL_NFCA_NFCDEP:     /* Device supports NFC-DEP */
            platformLog(
                "NFC-A P2P (NFC-DEP) device found \r\n"); /* NFC-A P2P device
                                                             found, NFCID/UID
                                                             is contained in:
                                                             nfcaDev.nfcid */
            /* Activation should continue using
             * rfalNfcDepInitiatorHandleActivation(), see exampleRfalPoller.c
             */
            break;
        }
        rfalNfcaPollerSleep(); /* Put device to sleep / HLTA (useless as the
                                  field will be turned off anyhow) */
      }
    }
  }
}
