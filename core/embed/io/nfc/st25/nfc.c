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

#include "card_emulation.h"
#include "ndef.h"
#include "nfc_internal.h"
#include "nfc_poll.h"
#include "rfal_isoDep.h"
#include "rfal_nfc.h"
#include "rfal_nfca.h"
#include "rfal_rf.h"
#include "rfal_t2t.h"
#include "rfal_utils.h"
#include "sys/mpu.h"

// NFC-A SEL_RES configured for Type 4A Tag Platform
#define LM_SEL_RES 0x20U

// NFC-F SENSF_RES configured for Type 3 Tag Platform
#define LM_NFCID2_BYTE1 0x02U

// NFC-F System Code byte 1
#define LM_SC_BYTE1 0x12U

// NFC-F System Code byte 2
#define LM_SC_BYTE2 0xFCU

// NFC-F PAD0
#define LM_PAD0 0x00U

// Interval to poll NFC device if still present (ms)
#define NFC_POLLING_INTERVAL_MS 300

typedef struct {
  bool initialized;
  bool rfal_initialized;
  bool card_connected;
  // SPI driver
  SPI_HandleTypeDef hspi;
  // NFC IRQ pin callback
  void (*nfc_irq_callback)(void);
  EXTI_HandleTypeDef hEXTI;
  const rfalNfcDiscoverParam *disc_params;
} st25_driver_t;

static const rfalNfcDiscoverParam default_disc_params = {
    .compMode = RFAL_COMPLIANCE_MODE_NFC,
    .devLimit = 1u,
    .nfcfBR = RFAL_BR_212,
    .ap2pBR = RFAL_BR_424,
    .maxBR = RFAL_BR_KEEP,
    .isoDepFS = RFAL_ISODEP_FSXI_256,
    .nfcDepLR = RFAL_NFCDEP_LR_254,
    // P2P communication data
    .nfcid3 = {0x01, 0xFE, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A},
    .GB = {0x46, 0x66, 0x6d, 0x01, 0x01, 0x11, 0x02, 0x02, 0x07, 0x80,
           0x03, 0x02, 0x00, 0x03, 0x04, 0x01, 0x32, 0x07, 0x01, 0x03},
    .GBLen = 20,
    .p2pNfcaPrio = true,
    .wakeupEnabled = false,
    .wakeupConfigDefault = true,
    .wakeupConfig = {0},
    .wakeupPollBefore = false,
    .wakeupNPolls = 1U,
    .totalDuration = 1000U,
    .techs2Find = RFAL_NFC_POLL_TECH_A | RFAL_NFC_POLL_TECH_B,
    .techs2Bail = RFAL_NFC_TECH_NONE,
    .propNfc = {0},
    .lmConfigPA = {0},
    .lmConfigPF = {{0}, {0}},
    .notifyCb = NULL,
};

static st25_driver_t g_st25_driver = {
    .initialized = false,
    .rfal_initialized = false,
};


static nfc_status_t nfc_transcieve_blocking(uint8_t *tx_buf,
                                            uint16_t tx_buf_size,
                                            uint8_t **rx_buf,
                                            uint16_t **rcv_len, uint32_t fwt);

static void nfc_card_emulator_loop(rfalNfcDevice *nfc_dev);

nfc_status_t nfc_init() {
  st25_driver_t *drv = &g_st25_driver;

  if (drv->initialized) {
    return NFC_OK;
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

  if (status != HAL_OK) {
    goto cleanup;
  }

  // Initialize EXTI for NFC IRQ pin
  EXTI_ConfigTypeDef EXTI_Config = {0};
  EXTI_Config.GPIOSel = NFC_EXTI_INTERRUPT_GPIOSEL;
  EXTI_Config.Line = NFC_EXTI_INTERRUPT_LINE;
  EXTI_Config.Mode = EXTI_MODE_INTERRUPT;
  EXTI_Config.Trigger = EXTI_TRIGGER_RISING;
  status = HAL_EXTI_SetConfigLine(&drv->hEXTI, &EXTI_Config);

  if (status != HAL_OK) {
    goto cleanup;
  }

  NVIC_SetPriority(NFC_EXTI_INTERRUPT_NUM, IRQ_PRI_NORMAL);
  __HAL_GPIO_EXTI_CLEAR_IT(NFC_INT_PIN);
  NVIC_ClearPendingIRQ(NFC_EXTI_INTERRUPT_NUM);

  ReturnCode ret;
  ret = rfalNfcInitialize();

  if (ret != RFAL_ERR_NONE) {
    goto cleanup;
  }

  __HAL_GPIO_EXTI_CLEAR_IT(NFC_INT_PIN);
  NVIC_ClearPendingIRQ(NFC_EXTI_INTERRUPT_NUM);
  NVIC_EnableIRQ(NFC_EXTI_INTERRUPT_NUM);

  drv->rfal_initialized = true;
  drv->initialized = true;
  drv->card_connected = false;
  drv->disc_params = &default_disc_params;

  if (!nfc_poll_init()) {
    goto cleanup;
  }

  return NFC_OK;

cleanup:
  nfc_deinit();
  return NFC_ERROR;
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
  st25_driver_t *drv = &g_st25_driver;

  if (!drv->initialized) {
    return NFC_NOT_INITIALIZED;
  }

  if (discovery_type == NFC_DISCOVERY_TYPE_CARD_EMULATION) {
    nfc_status_t status = nfc_register_tech(NFC_CARD_EMU_TECH_A);
    if (status != NFC_OK) {
      return status;
    }
  } else {
    memcpy(&drv->disc_params, &default_disc_params, sizeof(drv->disc_params));
  }

  ReturnCode err;
  err = rfalNfcDiscover(drv->disc_params);
  if (err != RFAL_ERR_NONE) {
    return NFC_ERROR;
  }

  return NFC_OK;
}

nfc_status_t nfc_stop_discovery(void) {
  st25_driver_t *drv = &g_st25_driver;
  drv->card_connected = false;

  if (!drv->initialized) {
    return NFC_OK;
  }

  // In case the NFC state machine is active, deactivate to idle before
  // registering a new card emulation technology.
  if (rfalNfcGetState() != RFAL_NFC_STATE_IDLE) {
    rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_IDLE);
    do {
      rfalNfcWorker();
    } while (rfalNfcGetState() != RFAL_NFC_STATE_IDLE);
  }

  return NFC_OK;
}

// Deactivate the currently activated NFC device and put RFAL state machine
// back to discovery state.
nfc_status_t nfc_restart_discovery(void) {
  st25_driver_t *drv = &g_st25_driver;
  drv->card_connected = false;

  if (!drv->initialized) {
    return NFC_NOT_INITIALIZED;
  }

  rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_DISCOVERY);

  return NFC_OK;
}

void nfc_get_state(nfc_state_t *state) {
  if (rfalNfcIsDevActivated(rfalNfcGetState())) {
    *state = (nfc_state_t){.connected = true};
  } else {
    *state = (nfc_state_t){.connected = false};
  }
}

bool nfc_is_connected() {
  st25_driver_t *drv = &g_st25_driver;
  return drv->card_connected;
}

bool nfc_identify(void) {
  st25_driver_t *drv = &g_st25_driver;
  nfc_dev_info_t dev_info;
  nfc_status_t status = nfc_dev_read_info(&dev_info);
  if (status != NFC_OK) {
    return false;
  }

  if (dev_info.type == NFC_DEV_TYPE_A || dev_info.type == NFC_DEV_TYPE_B ||
      dev_info.type == NFC_DEV_TYPE_V) {
    drv->card_connected = true;
    return true;
  } else {
    return false;
  }
}

bool nfc_check_connection() {
  static uint32_t last_check_time = 0;
  if (!ticks_expired(last_check_time + NFC_POLLING_INTERVAL_MS)) {
    return true;
  }
  last_check_time = ticks();

  nfc_dev_info_t dev_info;
  nfc_status_t status = nfc_dev_read_info(&dev_info);

  if (status != NFC_OK) {
    return false;
  }

  if (dev_info.interface == NFC_DEV_INTERFACE_ISODEP) {
    uint8_t tx_read_1b[] = {0x00, 0xB0, 0x00, 0x00, 0x01};
    uint8_t *rx_dummy = NULL;
    uint16_t *rx_dummy_len = NULL;
    status = nfc_transceive(tx_read_1b, sizeof(tx_read_1b), &rx_dummy,
                            &rx_dummy_len);
    return status == NFC_OK;
  }

  switch (dev_info.type) {
    case NFC_DEV_TYPE_A:
      uint8_t rxBuf[20];
      uint16_t rxLen = sizeof(rxBuf);
      ReturnCode err = rfalT2TPollerRead(0x00, rxBuf, sizeof(rxBuf), &rxLen);
      return err == RFAL_ERR_NONE;
    case NFC_DEV_TYPE_B:
    case NFC_DEV_TYPE_V:
    default:
      return false;
  }
}

nfc_status_t nfc_transceive(const uint8_t *tx_data, uint16_t tx_data_len,
                            uint8_t **rx_data, uint16_t **rx_data_len) {
  st25_driver_t *drv = &g_st25_driver;

  if (drv->initialized == false) {
    return NFC_NOT_INITIALIZED;
  }

  rfalNfcState state = rfalNfcGetState();
  if (state != RFAL_NFC_STATE_ACTIVATED &&
      state != RFAL_NFC_STATE_DATAEXCHANGE_DONE) {
    return NFC_WRONG_STATE;
  }

  nfc_status_t err = nfc_transcieve_blocking(
      (uint8_t *)tx_data, tx_data_len, rx_data, rx_data_len, RFAL_FWT_NONE);

  return err;
}

nfc_status_t nfc_dev_write_ndef_uri(void) {
  st25_driver_t *drv = &g_st25_driver;

  if (!drv->initialized) {
    return NFC_NOT_INITIALIZED;
  }

  // NDEF message
  uint8_t ndef_message[128] = {0};

  uint16_t buffer_len =
      ndef_create_uri("trezor.io/", ndef_message, sizeof(ndef_message));

  for (uint8_t i = 0; i < buffer_len / 4; i++) {
    rfalT2TPollerWrite(4 + i, ndef_message + i * 4);
  }

  return NFC_OK;
}

nfc_status_t nfc_dev_read_info(nfc_dev_info_t *dev_info) {
  if (rfalNfcIsDevActivated(rfalNfcGetState())) {
    rfalNfcDevice *nfc_device;
    if (rfalNfcGetActiveDevice(&nfc_device) != RFAL_ERR_NONE) {
      return NFC_ERROR;
    }

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
      case RFAL_NFC_INTERFACE_NFCDEP:
        dev_info->interface = NFC_DEV_INTERFACE_NFCDEP;
        break;
      default:
        dev_info->interface = NFC_DEV_INTERFACE_UNKNOWN;
    }

    // For poll mode, run the card emulator loop to handle the
    // communication until the peer device deactivates.
    if (dev_info->type == NFC_DEV_TYPE_POLL_TYPE_A ||
        dev_info->type == NFC_DEV_TYPE_POLL_TYPE_F) {
      if (dev_info->interface == NFC_DEV_INTERFACE_NFCDEP) {
        // not supported yet
      } else {
        nfc_card_emulator_loop(nfc_device);
      }
      return NFC_ERROR;  // Automatically deactivate
    }

    dev_info->uid_len = nfc_device->nfcidLen;

    if (nfc_device->nfcidLen > NFC_MAX_UID_LEN) {
      return NFC_ERROR;
    }

    // Copy the hex UID in printable string
    cstr_encode_hex(dev_info->uid, NFC_MAX_UID_BUF_SIZE, nfc_device->nfcid,
                    nfc_device->nfcidLen);

  } else {
    // No device activated
    return NFC_ERROR;
  }

  return NFC_OK;
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

static void nfc_card_emulator_loop(rfalNfcDevice *nfc_dev) {
  ReturnCode err = RFAL_ERR_INTERNAL;
  uint8_t *rx_buf;
  uint16_t *rcv_len;
  uint8_t tx_buf[150];
  uint16_t tx_len;

  do {
    rfalNfcWorker();

    switch (rfalNfcGetState()) {
      case RFAL_NFC_STATE_ACTIVATED:
        err = nfc_transcieve_blocking(NULL, 0, &rx_buf, &rcv_len, 0);
        break;

      case RFAL_NFC_STATE_DATAEXCHANGE:
      case RFAL_NFC_STATE_DATAEXCHANGE_DONE:

        tx_len =
            ((nfc_dev->type == RFAL_NFC_POLL_TYPE_NFCA)
                 ? card_emulation_t4t(rx_buf, *rcv_len, tx_buf, sizeof(tx_buf))
                 : rfalConvBytesToBits(
                       card_emulation_t3t(rx_buf, rfalConvBitsToBytes(*rcv_len),
                                          tx_buf, sizeof(rx_buf))));

        err = nfc_transcieve_blocking(tx_buf, tx_len, &rx_buf, &rcv_len,
                                      RFAL_FWT_NONE);
        break;

      case RFAL_NFC_STATE_START_DISCOVERY:
        return;

      case RFAL_NFC_STATE_LISTEN_SLEEP:
      default:
        break;
    }
  } while ((err == RFAL_ERR_NONE) || (err == RFAL_ERR_SLEEP_REQ));
}

static nfc_status_t nfc_transcieve_blocking(uint8_t *tx_buf,
                                            uint16_t tx_buf_size,
                                            uint8_t **rx_buf,
                                            uint16_t **rcv_len, uint32_t fwt) {
  ReturnCode err;
  err = rfalNfcDataExchangeStart(tx_buf, tx_buf_size, rx_buf, rcv_len, fwt);
  if (err == RFAL_ERR_NONE) {
    do {
      rfalNfcWorker();
      err = rfalNfcDataExchangeGetStatus();
    } while (err == RFAL_ERR_BUSY);
  } else {
    if (err == RFAL_ERR_WRONG_STATE) {
      return NFC_WRONG_STATE;
    } else if (err == RFAL_ERR_PARAM) {
      return NFC_PARAM;
    }
  }

  if (err != RFAL_ERR_NONE) {
    return NFC_ERROR;
  } else {
    return NFC_OK;
  }
}

#endif
