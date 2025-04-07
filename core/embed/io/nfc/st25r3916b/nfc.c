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
#include "rfal_isoDep.h"
#include "rfal_nfc.h"
#include "rfal_nfca.h"
#include "rfal_platform.h"
#include "rfal_rf.h"
#include "rfal_t2t.h"
#include "rfal_utils.h"

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

typedef enum {
  NFC_STATE_ACTIVE,
  NFC_STATE_NOT_ACTIVE,
} nfc_state_t;

typedef struct {
  bool initialized;
  // SPI driver
  SPI_HandleTypeDef hspi;
  // NFC IRQ pin callback
  void (*nfc_irq_callback)(void);
  EXTI_HandleTypeDef hEXTI;
  rfalNfcDiscoverParam disc_params;
  bool rfal_initialized;
  nfc_state_t last_nfc_state;
} st25r3916b_driver_t;

static st25r3916b_driver_t g_st25r3916b_driver = {
    .initialized = false,
    .rfal_initialized = false,
};

typedef struct {
  uint8_t UID[7];
  uint8_t BCC[1];
  uint8_t SYSTEM_AREA[2];
  union {
    uint8_t CC[4];
    struct {
      uint8_t CC_MAGIC_NUMBER;
      uint8_t CC_VERSION;
      uint8_t CC_SIZE;
      uint8_t CC_ACCESS_CONDITION;
    };
  };
} nfc_device_header_t2t_t;

// P2P communication data
static const uint8_t nfcid3[] = {0x01, 0xFE, 0x03, 0x04, 0x05,
                                 0x06, 0x07, 0x08, 0x09, 0x0A};
static const uint8_t gb[] = {0x46, 0x66, 0x6d, 0x01, 0x01, 0x11, 0x02,
                             0x02, 0x07, 0x80, 0x03, 0x02, 0x00, 0x03,
                             0x04, 0x01, 0x32, 0x07, 0x01, 0x03};

// NFC-A CE config
// 4-byte UIDs with first byte 0x08 would need random number for the subsequent
// 3 bytes. 4-byte UIDs with first byte 0x*F are Fixed number, not unique, use
// for this demo 7-byte UIDs need a manufacturer ID and need to assure
// uniqueness of the rest.
static const uint8_t ce_nfca_nfcid[] = {
    0x1, 0x2, 0x3, 0x4};  // =_STM, 5F 53 54 4D NFCID1 / UID (4 bytes)
static const uint8_t ce_nfca_sens_res[] = {
    0x02, 0x00};  // SENS_RES / ATQA for 4-byte UID
static const uint8_t ce_nfca_sel_res = LM_SEL_RES;  // SEL_RES / SAK

static const uint8_t ce_nfcf_nfcid2[] = {
    LM_NFCID2_BYTE1, 0xFE, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66};

// NFC-F CE config
static const uint8_t ce_nfcf_sc[] = {LM_SC_BYTE1, LM_SC_BYTE2};
static uint8_t ce_nfcf_sensf_res[] = {
    0x01,  // SENSF_RES
    0x02,    0xFE,    0x11, 0x22,
    0x33,    0x44,    0x55, 0x66,  // NFCID2
    LM_PAD0, LM_PAD0, 0x00, 0x00,
    0x00,    0x7F,    0x7F, 0x00,  // PAD0, PAD1, MRTIcheck, MRTIupdate, PAD2
    0x00,    0x00};                // RD

static nfc_status_t nfc_transcieve_blocking(uint8_t *tx_buf,
                                            uint16_t tx_buf_size,
                                            uint8_t **rx_buf,
                                            uint16_t **rcv_len, uint32_t fwt);

static void nfc_card_emulator_loop(rfalNfcDevice *nfc_dev);

nfc_status_t nfc_init() {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  if (drv->initialized) {
    return NFC_OK;
  }

  memset(drv, 0, sizeof(st25r3916b_driver_t));

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

  ReturnCode ret;
  ret = rfalNfcInitialize();

  // Set default discovery parameters
  rfalNfcDefaultDiscParams(&drv->disc_params);

  if (ret != RFAL_ERR_NONE) {
    goto cleanup;
  }

  drv->rfal_initialized = true;

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
  __HAL_GPIO_EXTI_CLEAR_FLAG(NFC_INT_PIN);
  NVIC_ClearPendingIRQ(NFC_EXTI_INTERRUPT_NUM);
  NVIC_EnableIRQ(NFC_EXTI_INTERRUPT_NUM);

  drv->initialized = true;
  drv->last_nfc_state = NFC_STATE_NOT_ACTIVE;

  return NFC_OK;

cleanup:
  nfc_deinit();
  return NFC_ERROR;
}

void nfc_deinit(void) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  if (drv->rfal_initialized) {
    // Deactivate rfal STM (Disconnects active devices)
    rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_IDLE);
    while (rfalNfcGetState() != RFAL_NFC_STATE_IDLE) {
      rfalNfcWorker();
    }
  }

  HAL_EXTI_ClearConfigLine(&drv->hEXTI);
  NVIC_DisableIRQ(NFC_EXTI_INTERRUPT_NUM);

  if (drv->rfal_initialized) {
    rfalDeinitialize();
    drv->rfal_initialized = false;
  }

  HAL_SPI_DeInit(&drv->hspi);

  HAL_GPIO_DeInit(NFC_SPI_MISO_PORT, NFC_SPI_MISO_PIN);
  HAL_GPIO_DeInit(NFC_SPI_MOSI_PORT, NFC_SPI_MOSI_PIN);
  HAL_GPIO_DeInit(NFC_SPI_SCK_PORT, NFC_SPI_SCK_PIN);
  HAL_GPIO_DeInit(NFC_SPI_NSS_PORT, NFC_SPI_NSS_PIN);
  HAL_GPIO_DeInit(NFC_INT_PORT, NFC_INT_PIN);

  memset(drv, 0, sizeof(st25r3916b_driver_t));
}

nfc_status_t nfc_register_tech(const nfc_tech_t tech) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  if (drv->initialized == false) {
    return NFC_NOT_INITIALIZED;
  }

  drv->disc_params.devLimit = 1;
  memcpy(&drv->disc_params.nfcid3, nfcid3, sizeof(nfcid3));
  memcpy(&drv->disc_params.GB, gb, sizeof(gb));
  drv->disc_params.GBLen = sizeof(gb);
  drv->disc_params.p2pNfcaPrio = true;
  drv->disc_params.totalDuration = 1000U;

  if (rfalNfcGetState() != RFAL_NFC_STATE_IDLE) {
    return NFC_ERROR;
  }

  // Set general discovery parameters.
  if (tech & NFC_POLLER_TECH_A) {
    drv->disc_params.techs2Find |= RFAL_NFC_POLL_TECH_A;
  }

  if (tech & NFC_POLLER_TECH_B) {
    drv->disc_params.techs2Find |= RFAL_NFC_POLL_TECH_B;
  }

  if (tech & NFC_POLLER_TECH_F) {
    drv->disc_params.techs2Find |= RFAL_NFC_POLL_TECH_F;
  }

  if (tech & NFC_POLLER_TECH_V) {
    drv->disc_params.techs2Find |= RFAL_NFC_POLL_TECH_V;
  }

  if (tech & NFC_CARD_EMU_TECH_A) {
    card_emulation_init(ce_nfcf_nfcid2);

    // Set SENS_RES / ATQA
    memcpy(drv->disc_params.lmConfigPA.SENS_RES, ce_nfca_sens_res,
           RFAL_LM_SENS_RES_LEN);

    // Set NFCID / UID
    memcpy(drv->disc_params.lmConfigPA.nfcid, ce_nfca_nfcid,
           RFAL_LM_NFCID_LEN_04);

    // Set NFCID length to 4 bytes
    drv->disc_params.lmConfigPA.nfcidLen = RFAL_LM_NFCID_LEN_04;

    // Set SEL_RES / SAK
    drv->disc_params.lmConfigPA.SEL_RES = ce_nfca_sel_res;
    drv->disc_params.techs2Find |= RFAL_NFC_LISTEN_TECH_A;
  }

  if (tech & NFC_CARD_EMU_TECH_F) {
    // Set configuration for NFC-F CE
    memcpy(drv->disc_params.lmConfigPF.SC, ce_nfcf_sc,
           RFAL_LM_SENSF_SC_LEN);  // Set System Code

    // Load NFCID2 on SENSF_RES
    memcpy(&ce_nfcf_sensf_res[RFAL_NFCF_CMD_LEN], ce_nfcf_nfcid2,
           RFAL_NFCID2_LEN);

    // Set SENSF_RES / Poll Response
    memcpy(drv->disc_params.lmConfigPF.SENSF_RES, ce_nfcf_sensf_res,
           RFAL_LM_SENSF_RES_LEN);

    drv->disc_params.techs2Find |= RFAL_NFC_LISTEN_TECH_F;
  }

  return NFC_OK;
}

nfc_status_t nfc_activate_stm(void) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  if (!drv->initialized) {
    return NFC_NOT_INITIALIZED;
  }

  ReturnCode err;
  err = rfalNfcDiscover(&drv->disc_params);
  if (err != RFAL_ERR_NONE) {
    return NFC_ERROR;
  }

  return NFC_OK;
}

nfc_status_t nfc_deactivate_stm(void) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

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

nfc_status_t nfc_get_event(nfc_event_t *event) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  *event = NFC_NO_EVENT;

  if (!drv->initialized) {
    return NFC_NOT_INITIALIZED;
  }

  rfalNfcDevice *nfc_device;

  // Run RFAL worker periodically
  rfalNfcWorker();

  rfalNfcState rfal_state = rfalNfcGetState();

  nfc_state_t cur_nfc_state = NFC_STATE_NOT_ACTIVE;

  if (rfalNfcIsDevActivated(rfal_state)) {
    cur_nfc_state = NFC_STATE_ACTIVE;
  }

  if (cur_nfc_state != drv->last_nfc_state) {
    switch (cur_nfc_state) {
      case NFC_STATE_ACTIVE:
        *event = NFC_EVENT_ACTIVATED;
        break;

      case NFC_STATE_NOT_ACTIVE:
        *event = NFC_EVENT_DEACTIVATED;
        break;

      default:
        *event = NFC_NO_EVENT;
    }

    drv->last_nfc_state = cur_nfc_state;
  }

  if (cur_nfc_state == NFC_STATE_ACTIVE) {
    rfalNfcGetActiveDevice(&nfc_device);

    // Perform immediate mandatory actions for certain technology (Placeholder)
    switch (nfc_device->type) {
      case RFAL_NFC_LISTEN_TYPE_NFCA:

        switch (nfc_device->dev.nfca.type) {
          case RFAL_NFCA_T1T:
            break;
          case RFAL_NFCA_T4T:
            break;
          case RFAL_NFCA_T4T_NFCDEP:
            break;
          case RFAL_NFCA_NFCDEP:
            break;
          default:
            break;
        }

      case RFAL_NFC_LISTEN_TYPE_NFCB:
        break;

      case RFAL_NFC_LISTEN_TYPE_NFCF:
        break;

      case RFAL_NFC_LISTEN_TYPE_NFCV:
        break;

      case RFAL_NFC_LISTEN_TYPE_ST25TB:
        break;

      case RFAL_NFC_LISTEN_TYPE_AP2P:
      case RFAL_NFC_POLL_TYPE_AP2P:
        break;

      // Card emulators must respond to reader commands promptly. Once
      // activated, the RFAL worker is called multiple times until back-to-back
      // communication with the reader finishes. This can prolong the
      // nfc_get_event() service time compared to standard reader mode.
      case RFAL_NFC_POLL_TYPE_NFCA:
      case RFAL_NFC_POLL_TYPE_NFCF:

        if (nfc_device->rfInterface == RFAL_NFC_INTERFACE_NFCDEP) {
          // not supported yet
        } else {
          nfc_card_emulator_loop(nfc_device);
          rfalNfcDeactivate(
              RFAL_NFC_DEACTIVATE_DISCOVERY);  // Automatically deactivate
        }

        // No event in CE mode, activation/deactivation handled automatically
        *event = NFC_NO_EVENT;

        break;

      default:
        break;
    }
  }

  return NFC_OK;
}

nfc_status_t nfc_dev_deactivate(void) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  if (!drv->initialized) {
    return NFC_NOT_INITIALIZED;
  }

  rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_DISCOVERY);

  return NFC_OK;
}

nfc_status_t nfc_transceive(const uint8_t *tx_data, uint16_t tx_data_len,
                            uint8_t *rx_data, uint16_t *rx_data_len) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  if (drv->initialized == false) {
    return NFC_NOT_INITIALIZED;
  }

  if (rfalNfcGetState() != RFAL_NFC_STATE_IDLE) {
    return NFC_ERROR;
  }

  ReturnCode err;
  err = nfc_transcieve_blocking((uint8_t *)tx_data, tx_data_len, &rx_data,
                                &rx_data_len, RFAL_FWT_NONE);

  if (err != RFAL_ERR_NONE) {
    return NFC_ERROR;
  }

  return NFC_OK;
}

nfc_status_t nfc_dev_write_ndef_uri(void) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

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
    rfalNfcGetActiveDevice(&nfc_device);

    // Resolve device type
    switch (nfc_device->type) {
      case RFAL_NFC_LISTEN_TYPE_NFCA:
        dev_info->type = NFC_DEV_TYPE_A;
        break;
      case RFAL_NFC_LISTEN_TYPE_NFCB:
        dev_info->type = NFC_DEV_TYPE_B;
        break;
      case RFAL_NFC_LISTEN_TYPE_NFCF:
        dev_info->type = NFC_DEV_TYPE_F;
        break;
      case RFAL_NFC_LISTEN_TYPE_NFCV:
        dev_info->type = NFC_DEV_TYPE_V;
        break;
      case RFAL_NFC_LISTEN_TYPE_ST25TB:
        dev_info->type = NFC_DEV_TYPE_ST25TB;
        break;
      case RFAL_NFC_LISTEN_TYPE_AP2P:
        dev_info->type = NFC_DEV_TYPE_AP2P;
        break;
      default:
        dev_info->type = NFC_DEV_TYPE_UNKNOWN;
        break;
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
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;
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
  }

  if (err != RFAL_ERR_NONE) {
    return NFC_ERROR;
  } else {
    return NFC_OK;
  }
}

#endif
