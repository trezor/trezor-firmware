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

#ifdef KERNEL_MODE

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <io/nfc.h>
#include <rtl/strutils.h>
#include <sys/irq.h>
#include <sys/systick.h>

#include "ndef.h"
#include "nfc_internal.h"
#include "nfc_poll.h"
#include "rfal_isoDep.h"
#include "rfal_nfc.h"
#include "rfal_nfca.h"
#include "rfal_platform.h"
#include "rfal_rf.h"
#include "rfal_t2t.h"
#include "rfal_utils.h"
#include "sys/mpu.h"

// Interval to poll NFC device if still present (ms)
#define NFC_POLLING_INTERVAL_MS 300u

typedef struct {
  bool initialized;
  bool rfal_initialized;
  // SPI driver
  SPI_HandleTypeDef hspi;
  // NFC IRQ pin callback
  void (*nfc_irq_callback)(void);
  EXTI_HandleTypeDef hEXTI;
  rfalNfcDiscoverParam disc_params;
} st25_driver_t;

static st25_driver_t g_st25_driver = {
    .initialized = false,
    .rfal_initialized = false,
};

static ts_t nfc_transceive_blocking(const nfc_apdu_cmd_t cmd,
                                    nfc_apdu_response_t resp, uint32_t fwt);

static ts_t nfc_dev_read_info(nfc_dev_info_t *dev_info);

ts_t nfc_init(void) {
  TSH_DECLARE;
  st25_driver_t *drv = &g_st25_driver;

  if (drv->initialized) {
    TSH_RETURN;
  }

  memset(drv, 0, sizeof(st25_driver_t));

  // Enable clock of relevant peripherals
  // SPI + GPIO ports
  NFC_SPI_FORCE_RESET();
  NFC_SPI_RELEASE_RESET();
  NFC_SPI_CLK_EN();
  NFC_SPI_MISO_CLK_EN();
  NFC_SPI_MOSI_CLK_EN();
  NFC_SPI_SCK_CLK_EN();
  NFC_SPI_NSS_CLK_EN();

  // SPI peripheral pin config
  GPIO_InitTypeDef GPIO_InitStruct = {0};
  GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
  GPIO_InitStruct.Pull = GPIO_NOPULL;
  GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStruct.Alternate = NFC_SPI_PIN_AF;

  GPIO_InitStruct.Pin = NFC_SPI_MISO_PIN;
  HAL_GPIO_Init(NFC_SPI_MISO_PORT, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = NFC_SPI_MOSI_PIN;
  HAL_GPIO_Init(NFC_SPI_MOSI_PORT, &GPIO_InitStruct);

  GPIO_InitStruct.Pin = NFC_SPI_SCK_PIN;
  HAL_GPIO_Init(NFC_SPI_SCK_PORT, &GPIO_InitStruct);

  // NSS pin controlled by software, set as classical GPIO
  GPIO_InitTypeDef GPIO_InitStruct_nss = {0};
  GPIO_InitStruct_nss.Mode = GPIO_MODE_OUTPUT_PP;
  GPIO_InitStruct_nss.Pull = GPIO_NOPULL;
  GPIO_InitStruct_nss.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStruct_nss.Pin = NFC_SPI_NSS_PIN;
  HAL_GPIO_Init(NFC_SPI_NSS_PORT, &GPIO_InitStruct_nss);

  // NFC IRQ pin
  GPIO_InitTypeDef GPIO_InitStructure_int = {0};
  GPIO_InitStructure_int.Mode = GPIO_MODE_INPUT;
  GPIO_InitStructure_int.Pull = GPIO_PULLDOWN;
  GPIO_InitStructure_int.Speed = GPIO_SPEED_FREQ_LOW;
  GPIO_InitStructure_int.Pin = NFC_INT_PIN;
  HAL_GPIO_Init(NFC_INT_PORT, &GPIO_InitStructure_int);

  memset(&drv->hspi, 0, sizeof(drv->hspi));

  drv->hspi.Instance = NFC_SPI_INSTANCE;
  drv->hspi.Init.Mode = SPI_MODE_MASTER;
  drv->hspi.Init.BaudRatePrescaler =
      SPI_BAUDRATEPRESCALER_32;  // TODO: Calculate frequency precisly.
  drv->hspi.Init.DataSize = SPI_DATASIZE_8BIT;
  drv->hspi.Init.Direction = SPI_DIRECTION_2LINES;
  drv->hspi.Init.CLKPolarity = SPI_POLARITY_LOW;
  drv->hspi.Init.CLKPhase = SPI_PHASE_2EDGE;
  drv->hspi.Init.NSS = SPI_NSS_SOFT;  // For RFAL lib purpose, use software NSS
  drv->hspi.Init.NSSPolarity = SPI_NSS_POLARITY_LOW;
  drv->hspi.Init.NSSPMode = SPI_NSS_PULSE_DISABLE;

  HAL_StatusTypeDef status;
  status = HAL_SPI_Init(&drv->hspi);

  TSH_CHECK(status == HAL_OK, TS_EIO);

  // Initialize EXTI for NFC IRQ pin
  EXTI_ConfigTypeDef EXTI_Config = {0};
  EXTI_Config.GPIOSel = NFC_EXTI_INTERRUPT_GPIOSEL;
  EXTI_Config.Line = NFC_EXTI_INTERRUPT_LINE;
  EXTI_Config.Mode = EXTI_MODE_INTERRUPT;
  EXTI_Config.Trigger = EXTI_TRIGGER_RISING;
  status = HAL_EXTI_SetConfigLine(&drv->hEXTI, &EXTI_Config);
  TSH_CHECK(status == HAL_OK, TS_EIO);

  NVIC_SetPriority(NFC_EXTI_INTERRUPT_NUM, IRQ_PRI_NORMAL);
  __HAL_GPIO_EXTI_CLEAR_IT(NFC_INT_PIN);
  NVIC_ClearPendingIRQ(NFC_EXTI_INTERRUPT_NUM);

  ReturnCode ret = rfalNfcInitialize();
  TSH_CHECK(ret == RFAL_ERR_NONE, TS_ENOINIT);

  __HAL_GPIO_EXTI_CLEAR_IT(NFC_INT_PIN);
  NVIC_ClearPendingIRQ(NFC_EXTI_INTERRUPT_NUM);
  NVIC_EnableIRQ(NFC_EXTI_INTERRUPT_NUM);

  drv->rfal_initialized = true;
  drv->initialized = true;
  drv->disc_params = &default_disc_params;

  TSH_CHECK(nfc_poll_init(), TS_ENOINIT);

  TSH_RETURN;

cleanup:
  nfc_deinit();
  TSH_RETURN;
}

void nfc_deinit(void) {
  st25_driver_t *drv = &g_st25_driver;

  nfc_stop_discovery();
  nfc_poll_deinit();

  HAL_EXTI_ClearConfigLine(&drv->hEXTI);
  NVIC_DisableIRQ(NFC_EXTI_INTERRUPT_NUM);

  if (drv->rfal_initialized) {
    rfalDeinitialize();
    drv->rfal_initialized = false;
  }

  if (drv->hspi.Instance != NULL) {
    HAL_SPI_DeInit(&drv->hspi);
  }

  HAL_GPIO_DeInit(NFC_SPI_MISO_PORT, NFC_SPI_MISO_PIN);
  HAL_GPIO_DeInit(NFC_SPI_MOSI_PORT, NFC_SPI_MOSI_PIN);
  HAL_GPIO_DeInit(NFC_SPI_SCK_PORT, NFC_SPI_SCK_PIN);
  HAL_GPIO_DeInit(NFC_SPI_NSS_PORT, NFC_SPI_NSS_PIN);
  HAL_GPIO_DeInit(NFC_INT_PORT, NFC_INT_PIN);

  memset(drv, 0, sizeof(st25_driver_t));
}

ts_t nfc_start_discovery(void) {
  TSH_DECLARE;
  st25_driver_t *drv = &g_st25_driver;
  TSH_CHECK(drv->initialized, TS_ENOINIT);

  ReturnCode err = rfalNfcDiscover(drv->disc_params);
  TSH_CHECK(err == RFAL_ERR_NONE, TS_ENOEN);

cleanup:
  TSH_RETURN;
}

ts_t nfc_stop_discovery(void) {
  TSH_DECLARE;
  st25_driver_t *drv = &g_st25_driver;
  TSH_CHECK(drv->initialized, TS_ENOINIT);

  // In case the NFC state machine is active, deactivate to idle before
  // registering a new card emulation technology.
  TSH_CHECK(rfalNfcGetState() == RFAL_NFC_STATE_IDLE, TS_ENOSTATE);

  ReturnCode ret = rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_IDLE);
  TSH_CHECK_ARG(ret == RFAL_ERR_NONE);
  do {
    rfalNfcWorker();
  } while (rfalNfcGetState() != RFAL_NFC_STATE_IDLE);

cleanup:
  TSH_RETURN;
}

// Deactivate the currently activated NFC device and put RFAL state machine
// back to discovery state.
ts_t nfc_restart_discovery(void) {
  TSH_DECLARE;
  st25_driver_t *drv = &g_st25_driver;
  TSH_CHECK(drv->initialized, TS_ENOINIT);

  ReturnCode ret = rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_DISCOVERY);
  TSH_CHECK_ARG(ret == RFAL_ERR_NONE);

cleanup:
  TSH_RETURN;
}

bool nfc_identify(nfc_dev_info_t *dev_info) {
  TSH_DECLARE;
  ts_t status = nfc_dev_read_info(dev_info);
  TSH_CHECK_OK(status);

  if (((dev_info->type == NFC_DEV_TYPE_A) ||
       (dev_info->type == NFC_DEV_TYPE_B)) &&
      (dev_info->interface == NFC_DEV_INTERFACE_ISODEP)) {
    return true;
  }

cleanup:
  memset(dev_info, 0, sizeof(nfc_dev_info_t));
  return false;
}

bool nfc_check_connection(nfc_dev_info_t *dev_info) {
  TSH_DECLARE;
  static uint32_t last_check_time = 0;
  if (!ticks_expired(last_check_time + NFC_POLLING_INTERVAL_MS)) {
    return true;
  }
  last_check_time = ticks();

  if (dev_info->interface == NFC_DEV_INTERFACE_ISODEP) {
    uint8_t tx_read_1b[] = {0x00, 0xB0, 0x00, 0x00, 0x01};
    uint8_t *rx_dummy = NULL;
    uint16_t *rx_dummy_len = NULL;
    nfc_apdu_cmd_t tx_buf = {.data = tx_read_1b,
                             .data_len = sizeof(tx_read_1b)};
    nfc_apdu_response_t rx_buf = {.data = &rx_dummy, .data_len = &rx_dummy_len};
    ts_t status = nfc_transceive(tx_buf, rx_buf);
    return ts_ok(status);
  }

  switch (dev_info->type) {
    case NFC_DEV_TYPE_A:
      uint8_t rxBuf[20];
      uint16_t rxLen = sizeof(rxBuf);
      ReturnCode err = rfalT2TPollerRead(0x00, rxBuf, sizeof(rxBuf), &rxLen);
      return err == RFAL_ERR_NONE;
    case NFC_DEV_TYPE_B:
    default:
      return false;
  }

  return false;
}

ts_t nfc_transceive(const nfc_apdu_cmd_t cmd, nfc_apdu_response_t resp) {
  TSH_DECLARE;
  st25_driver_t *drv = &g_st25_driver;
  TSH_CHECK(drv->initialized, TS_ENOINIT);

  rfalNfcState state = rfalNfcGetState();
  if (state != RFAL_NFC_STATE_ACTIVATED &&
      state != RFAL_NFC_STATE_DATAEXCHANGE_DONE) {
    return TS_ENOSTATE;
  }

  return nfc_transceive_blocking(cmd, resp, RFAL_FWT_NONE);

cleanup:
  TSH_RETURN;
}

static ts_t nfc_dev_read_info(nfc_dev_info_t *dev_info) {
  TSH_DECLARE;
  TSH_CHECK(rfalNfcIsDevActivated(rfalNfcGetState()), TS_ENOEN);

  rfalNfcDevice *nfc_device;
  ReturnCode ret = rfalNfcGetActiveDevice(&nfc_device);
  TSH_CHECK(ret == RFAL_ERR_NONE, TS_ENOEN);

  // Resolve device type
  switch (nfc_device->type) {
    case RFAL_NFC_LISTEN_TYPE_NFCA:
      dev_info->type = NFC_DEV_TYPE_A;
      break;
    case RFAL_NFC_LISTEN_TYPE_NFCB:
      dev_info->type = NFC_DEV_TYPE_B;
      break;
    default:
      dev_info->type = NFC_DEV_TYPE_UNKNOWN;
      break;
  }

  switch (nfc_device->rfInterface) {
    case RFAL_NFC_INTERFACE_RF:
      dev_info->interface = NFC_DEV_INTERFACE_RF;
      break;
    case RFAL_NFC_INTERFACE_ISODEP:
      dev_info->interface = NFC_DEV_INTERFACE_ISODEP;
      break;
    default:
      dev_info->interface = NFC_DEV_INTERFACE_UNKNOWN;
  }

  dev_info->uid_len = nfc_device->nfcidLen;
  TSH_CHECK(nfc_device->nfcidLen <= NFC_MAX_UID_LEN, TS_ENOEN);

  // Copy the hex UID in printable string
  cstr_encode_hex(dev_info->uid, NFC_MAX_UID_BUF_SIZE, nfc_device->nfcid,
                  nfc_device->nfcidLen);

cleanup:
  TSH_RETURN;
}

HAL_StatusTypeDef nfc_spi_transmit_receive(const uint8_t *tx_data,
                                           uint8_t *rx_data, uint16_t length) {
  st25_driver_t *drv = &g_st25_driver;
  HAL_StatusTypeDef status;

  if ((tx_data != NULL) && (rx_data == NULL)) {
    status = HAL_SPI_Transmit(&drv->hspi, (uint8_t *)tx_data, length, 1000);
  } else if ((tx_data == NULL) && (rx_data != NULL)) {
    status = HAL_SPI_Receive(&drv->hspi, rx_data, length, 1000);
  } else {
    status = HAL_SPI_TransmitReceive(&drv->hspi, (uint8_t *)tx_data, rx_data,
                                     length, 1000);
  }

  return status;
}

void nfc_ext_irq_set_callback(void (*cb)(void)) {
  st25_driver_t *drv = &g_st25_driver;
  drv->nfc_irq_callback = cb;
}

void NFC_EXTI_INTERRUPT_HANDLER(void) {
  IRQ_LOG_ENTER();
  mpu_mode_t mode = mpu_reconfig(MPU_MODE_DEFAULT);

  st25_driver_t *drv = &g_st25_driver;

  // Clear the EXTI line pending bit
  __HAL_GPIO_EXTI_CLEAR_IT(NFC_INT_PIN);
  if (drv->nfc_irq_callback != NULL) {
    drv->nfc_irq_callback();
  }

  mpu_restore(mode);
  IRQ_LOG_EXIT();
}

static ts_t nfc_transceive_blocking(const nfc_apdu_cmd_t cmd,
                                    nfc_apdu_response_t resp, uint32_t fwt) {
  TSH_DECLARE;
  ReturnCode err = rfalNfcDataExchangeStart((uint8_t *)cmd.data, cmd.data_len,
                                            resp.data, resp.data_len, fwt);

  if (err == RFAL_ERR_WRONG_STATE) {
    return TS_ENOSTATE;
  } else if (err == RFAL_ERR_PARAM) {
    return TS_EINVAL;
  }

  do {
    rfalNfcWorker();
    err = rfalNfcDataExchangeGetStatus();
  } while (err == RFAL_ERR_BUSY);
  TSH_CHECK(err == RFAL_ERR_NONE, TS_ENOEN);

cleanup:
  TSH_RETURN;
}

#endif
