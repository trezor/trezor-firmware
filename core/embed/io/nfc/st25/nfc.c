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
#include <sys/irq.h>
#include <sys/systick.h>

#include "nfc_internal.h"
#include "nfc_poll.h"
#include "rfal_isoDep.h"
#include "rfal_nfc.h"
#include "rfal_rf.h"
#include "rfal_t2t.h"
#include "rfal_utils.h"
#include "sys/mpu.h"

// Interval to poll NFC device if still present (ms)
#define NFC_POLLING_INTERVAL_MS 300u

#define NFC_PSK_FRAME_HEADER 0xB580  // Only 9 MSB bits are used
#define NFC_PSK_FRAME_HEADER_BITS 9U

#define NFC_PSK_SHARE_LEN 16U
#define NFC_PSK_SHARE_REPEAT_COUNT 3U
#define NFC_PSK_FRAME_PAYLOAD_LEN \
  (NFC_PSK_SHARE_LEN * NFC_PSK_SHARE_REPEAT_COUNT)
#define NFC_PSK_FRAME_LEN (NFC_PSK_FRAME_PAYLOAD_LEN + 4)

#define NFC_CRC_A_PRELOAD 0x6363U
#define NFC_CRC_A_POLY 0x8408U

typedef enum {
  NFC_XFER_IDLE = 0,
  NFC_XFER_PENDING,  // exchange in progress
  NFC_XFER_DONE,     // result waits for nfc_transceive_complete()
} nfc_xfer_state_t;

typedef enum {
  NFC_XFER_APDU,  // started by nfc_transceive_start()
  NFC_XFER_PSK,   // started by nfc_transceive_psk_start()
} nfc_xfer_kind_t;

// Asynchronous exchange
typedef struct {
  nfc_xfer_state_t state;
  nfc_xfer_kind_t kind;
  bool event_reported;
  // Rx buffer provided by RFAL, valid until the next exchange
  uint8_t *rx_data;
  uint16_t *rx_data_len;
  // PSK frames, RFAL references them until the exchange finishes
  uint8_t psk_tx_frame[NFC_PSK_FRAME_LEN];
  uint8_t psk_rx_frame[NFC_PSK_FRAME_LEN];
  uint16_t psk_rx_bits;
  ts_t result;
} nfc_xfer_t;

typedef struct {
  bool initialized;
  bool rfal_initialized;
  // SPI driver
  SPI_HandleTypeDef hspi;
  // NFC IRQ pin callback
  void (*nfc_irq_callback)(void);
  EXTI_HandleTypeDef hEXTI;
  const rfalNfcDiscoverParam *disc_params;
  nfc_xfer_t xfer;
} st25_driver_t;

static const rfalNfcDiscoverParam default_disc_params = {
    .compMode = RFAL_COMPLIANCE_MODE_NFC,
    .devLimit = 1u,
    .nfcfBR = RFAL_BR_212,
    .ap2pBR = RFAL_BR_424,
    .maxBR = RFAL_BR_KEEP,
    .isoDepFS = RFAL_ISODEP_FSXI_256,
    .nfcDepLR = RFAL_NFCDEP_LR_254,
    // P2P communication is not used
    .nfcid3 = {0},
    .GB = {0},
    .GBLen = 0U,
    .p2pNfcaPrio = false,  //!> ISO14443-4/T4T priority
    .wakeupEnabled = false,
    .wakeupConfigDefault = true,
    .wakeupConfig = {0},
    .wakeupPollBefore = false,
    .wakeupNPolls = 1U,
    .totalDuration = 100U,
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

// Time of the last card presence check (or a successful exchange, which
// proves the card is present as well)
static uint32_t g_last_check_time = 0;

static void nfc_transceive_finish(ts_t result);

static ts_t nfc_dev_read_info(nfc_dev_info_t *dev_info);

static void nfc_append_bits_to_frame(uint8_t *frame, uint16_t *bit_index,
                                     const uint8_t *data, uint16_t data_bits) {
  for (uint16_t i = 0; i < data_bits; i++) {
    if ((data[i / 8U] & (uint8_t)(1U << (7U - (i % 8U)))) != 0U) {
      frame[*bit_index / 8U] |= (uint8_t)(1U << (7U - (*bit_index % 8U)));
    }
    (*bit_index)++;
  }
}

static uint16_t nfc_crc_a_from_bytestream(const uint8_t *payload,
                                          size_t payload_len) {
  uint16_t crc = NFC_CRC_A_PRELOAD;

  for (size_t i = 0; i < payload_len; i++) {
    uint8_t byte = payload[i];

    // ISO14443A CRC uses LSB-first processing with poly 0x8408.
    for (uint8_t bit = 0; bit < 8U; bit++) {
      uint16_t mix = (uint16_t)((crc ^ (uint16_t)byte) & 0x0001U);
      crc >>= 1U;
      if (mix != 0U) {
        crc ^= NFC_CRC_A_POLY;
      }
      byte >>= 1U;
    }
  }

  return crc;
}

static uint16_t nfc_build_psk_frame(const uint8_t *tx_psk, size_t tx_psk_len,
                                    uint8_t *tx_frame, size_t tx_frame_len) {
  uint16_t bit_index = 0;

  if (tx_psk_len != NFC_PSK_SHARE_LEN ||
      tx_frame_len < (NFC_PSK_FRAME_PAYLOAD_LEN + 4)) {
    return 0;
  }

  uint8_t header[2] = {(uint8_t)(NFC_PSK_FRAME_HEADER >> 8U),
                       (uint8_t)(NFC_PSK_FRAME_HEADER & 0xFFU)};

  uint8_t payload[NFC_PSK_FRAME_PAYLOAD_LEN] = {0};

  memset(tx_frame, 0, NFC_PSK_FRAME_PAYLOAD_LEN + 4);

  for (size_t repeat = 0; repeat < NFC_PSK_SHARE_REPEAT_COUNT; repeat++) {
    memcpy(&payload[repeat * NFC_PSK_SHARE_LEN], tx_psk, NFC_PSK_SHARE_LEN);
  }

  nfc_append_bits_to_frame(tx_frame, &bit_index, header,
                           NFC_PSK_FRAME_HEADER_BITS);
  nfc_append_bits_to_frame(tx_frame, &bit_index, payload,
                           NFC_PSK_FRAME_PAYLOAD_LEN * 8U);

  uint16_t crc_a =
      nfc_crc_a_from_bytestream(payload, NFC_PSK_FRAME_PAYLOAD_LEN);
  crc_a = ~crc_a;  // Invert CRC-A for NFC-A

  nfc_append_bits_to_frame(tx_frame, &bit_index, (uint8_t *)&crc_a, 8U);
  nfc_append_bits_to_frame(tx_frame, &bit_index, ((uint8_t *)&crc_a) + 1, 8U);

  // Align bit index to next byte boundary
  if (bit_index % 8U != 0U) {
    bit_index += (8U - (bit_index % 8U));
  }

  return bit_index;
}

static ts_t nfc_parse_psk_frame(uint8_t *frame, uint16_t frame_len,
                                uint8_t *psk, uint16_t psk_max_len,
                                uint16_t *psk_len) {
  TSH_DECLARE;

  TSH_CHECK_ARG(frame != NULL);
  TSH_CHECK_ARG(frame_len == (2 + NFC_PSK_FRAME_PAYLOAD_LEN + 2));
  TSH_CHECK_ARG(psk != NULL);
  TSH_CHECK_ARG(psk_max_len >= NFC_PSK_SHARE_LEN);

  // Check frame header
  TSH_CHECK(frame[0] == 0xB6 && frame[1] == 0x80, TS_EINVAL);

  // Check that the PSK is repeated correctly in the frame
  TSH_CHECK(
      memcmp(frame + 2, frame + 2 + NFC_PSK_SHARE_LEN, NFC_PSK_SHARE_LEN) == 0,
      TS_EINVAL);
  TSH_CHECK(memcmp(frame + 2, frame + 2 + 2 * NFC_PSK_SHARE_LEN,
                   NFC_PSK_SHARE_LEN) == 0,
            TS_EINVAL);

  uint16_t expected_crc;
  memcpy(&expected_crc, frame + 2 + NFC_PSK_FRAME_PAYLOAD_LEN,
         sizeof(expected_crc));
  uint16_t crc =
      ~nfc_crc_a_from_bytestream(frame + 2, NFC_PSK_FRAME_PAYLOAD_LEN);

  TSH_CHECK(crc == expected_crc, TS_EINVAL);

  memcpy(psk, frame + 2, NFC_PSK_SHARE_LEN);
  *psk_len = NFC_PSK_SHARE_LEN;

cleanup:
  TSH_RETURN;
}

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
  drv->initialized = false;
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

  if (drv->xfer.state == NFC_XFER_PENDING) {
    nfc_transceive_finish(TS_ENOSTATE);
  }

  // In case the NFC state machine is active, deactivate to idle before
  // registering a new card emulation technology.
  if (rfalNfcGetState() != RFAL_NFC_STATE_IDLE) {
    ReturnCode ret = rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_IDLE);
    TSH_CHECK_ARG(ret == RFAL_ERR_NONE);
    do {
      rfalNfcWorker();
    } while (rfalNfcGetState() != RFAL_NFC_STATE_IDLE);
  }

cleanup:
  TSH_RETURN;
}

// Deactivate the currently activated NFC device and put RFAL state machine
// back to discovery state.
ts_t nfc_restart_discovery(void) {
  TSH_DECLARE;
  st25_driver_t *drv = &g_st25_driver;
  TSH_CHECK(drv->initialized, TS_ENOINIT);

  if (drv->xfer.state == NFC_XFER_PENDING) {
    nfc_transceive_finish(TS_ENOSTATE);
  }

  ReturnCode ret = rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_DISCOVERY);
  TSH_CHECK_ARG(ret == RFAL_ERR_NONE);

cleanup:
  TSH_RETURN;
}

bool nfc_identify(nfc_dev_info_t *dev_info) {
  TSH_DECLARE;
  ts_t status = nfc_dev_read_info(dev_info);
  TSH_CHECK_OK(status);

  if (((dev_info->type == NFC_DEV_TYPE_B) ||
       ((dev_info->type == NFC_DEV_TYPE_A) &&
        ((dev_info->tag_type == NFCA_T4T) ||
         (dev_info->tag_type == NFCA_T2T)))) &&
      ((dev_info->interface == NFC_DEV_INTERFACE_ISODEP) ||
       (dev_info->interface == NFC_DEV_INTERFACE_RF))) {
    return true;
  }

cleanup:
  memset(dev_info, 0, sizeof(nfc_dev_info_t));
  return false;
}

bool nfc_check_connection(nfc_dev_info_t *dev_info) {
  TSH_DECLARE;
  if (!ticks_expired(g_last_check_time + NFC_POLLING_INTERVAL_MS)) {
    return true;
  }
  g_last_check_time = ticks();

  if (dev_info->interface == NFC_DEV_INTERFACE_ISODEP) {
    ReturnCode err = rfalIsoDepPollPresenceCheckStart();
    if (err == RFAL_ERR_WRONG_STATE) {
      return true;
    } else if (err != RFAL_ERR_NONE) {
      return false;
    }

    do {
      rfalNfcWorker();
      err = rfalIsoDepPollGetPresenceCheckStatus();
    } while (err == RFAL_ERR_BUSY);

    return err == RFAL_ERR_NONE;
  } else if (dev_info->tag_type == NFCA_T2T) {
    uint8_t rxBuf[20];
    uint16_t rxLen = sizeof(rxBuf);
    ReturnCode err = rfalT2TPollerRead(0x00, rxBuf, sizeof(rxBuf), &rxLen);
    return err == RFAL_ERR_NONE;
  } else {
    return false;
  }
}

// Checks common to starting any asynchronous exchange. On success, `dev` is
// the activated ISO-DEP device.
static ts_t nfc_transceive_check_start(rfalNfcDevice **dev) {
  TSH_DECLARE;
  st25_driver_t *drv = &g_st25_driver;
  nfc_xfer_t *xfer = &drv->xfer;
  TSH_CHECK(drv->initialized, TS_ENOINIT);
  TSH_CHECK(xfer->state == NFC_XFER_IDLE || xfer->state == NFC_XFER_DONE,
            TS_EBUSY);

  rfalNfcState state = rfalNfcGetState();
  TSH_CHECK(state == RFAL_NFC_STATE_ACTIVATED ||
                state == RFAL_NFC_STATE_DATAEXCHANGE_DONE,
            TS_ENOSTATE);

  // Only ISO-DEP is supported. RFAL copies ISO-DEP commands into its own
  // buffer and the protocol bounds the exchange duration, whereas the RF
  // interface (e.g. T2T) keeps referencing the caller's buffer and has no
  // timeout with RFAL_FWT_NONE.
  TSH_CHECK(rfalNfcGetActiveDevice(dev) == RFAL_ERR_NONE && *dev != NULL,
            TS_ENOSTATE);
  TSH_CHECK((*dev)->rfInterface == RFAL_NFC_INTERFACE_ISODEP, TS_ENOSTATE);

cleanup:
  TSH_RETURN;
}

static void nfc_transceive_set_pending(nfc_xfer_kind_t kind) {
  nfc_xfer_t *xfer = &g_st25_driver.xfer;

  xfer->state = NFC_XFER_PENDING;
  xfer->kind = kind;
  xfer->event_reported = false;
  xfer->result = TS_OK;
}

ts_t nfc_transceive_start(const nfc_apdu_message_t *cmd) {
  TSH_DECLARE;
  nfc_xfer_t *xfer = &g_st25_driver.xfer;
  TSH_CHECK(cmd != NULL && cmd->data_len <= sizeof(cmd->data), TS_EINVAL);

  rfalNfcDevice *dev = NULL;
  TSH_CHECK_OK(nfc_transceive_check_start(&dev));

  xfer->rx_data = NULL;
  xfer->rx_data_len = NULL;

  ReturnCode err = rfalNfcDataExchangeStart((uint8_t *)cmd->data, cmd->data_len,
                                            &xfer->rx_data, &xfer->rx_data_len,
                                            RFAL_FWT_NONE);

  TSH_CHECK(err != RFAL_ERR_WRONG_STATE, TS_ENOSTATE);
  TSH_CHECK(err != RFAL_ERR_PARAM, TS_EINVAL);
  TSH_CHECK(err == RFAL_ERR_NONE, TS_ENOEN);

  nfc_transceive_set_pending(NFC_XFER_APDU);

cleanup:
  TSH_RETURN;
}

ts_t nfc_transceive_psk_start(const uint8_t *pcd_psk, size_t pcd_psk_len) {
  TSH_DECLARE;
  nfc_xfer_t *xfer = &g_st25_driver.xfer;
  TSH_CHECK_ARG(pcd_psk != NULL);
  TSH_CHECK_ARG(pcd_psk_len == NFC_PSK_SHARE_LEN);

  uint32_t flags = (uint32_t)RFAL_TXRX_FLAGS_CRC_TX_MANUAL |
                   (uint32_t)RFAL_TXRX_FLAGS_CRC_RX_KEEP |
                   (uint32_t)RFAL_TXRX_FLAGS_CRC_RX_MANUAL |
                   (uint32_t)RFAL_TXRX_FLAGS_PAR_TX_NONE |
                   (uint32_t)RFAL_TXRX_FLAGS_PAR_RX_REMV;

  rfalNfcDevice *dev = NULL;
  TSH_CHECK_OK(nfc_transceive_check_start(&dev));
  // The PSK frame uses ISO14443-A framing
  TSH_CHECK(dev->type == RFAL_NFC_LISTEN_TYPE_NFCA, TS_ENOSTATE);

  memset(xfer->psk_rx_frame, 0, sizeof(xfer->psk_rx_frame));
  xfer->psk_rx_bits = 0;
  uint16_t tx_bits = nfc_build_psk_frame(
      pcd_psk, pcd_psk_len, xfer->psk_tx_frame, sizeof(xfer->psk_tx_frame));

  ReturnCode rc = rfalISO14443AStartTransceiveCustomFrame(
      xfer->psk_tx_frame, tx_bits, xfer->psk_rx_frame,
      rfalConvBytesToBits(sizeof(xfer->psk_rx_frame)), &xfer->psk_rx_bits,
      flags, rfalConvMsTo1fc(100));

  TSH_CHECK(rc != RFAL_ERR_WRONG_STATE, TS_ENOSTATE);
  TSH_CHECK(rc == RFAL_ERR_NONE, TS_EIO);

  nfc_transceive_set_pending(NFC_XFER_PSK);

cleanup:
  TSH_RETURN;
}

ts_t nfc_transceive_complete(nfc_apdu_message_t *resp) {
  bool wipe = false;
  TSH_DECLARE;
  st25_driver_t *drv = &g_st25_driver;
  nfc_xfer_t *xfer = &drv->xfer;
  TSH_CHECK(drv->initialized, TS_ENOINIT);
  TSH_CHECK(resp != NULL, TS_EINVAL);
  TSH_CHECK(xfer->state != NFC_XFER_PENDING, TS_EBUSY);
  TSH_CHECK(xfer->state == NFC_XFER_DONE, TS_ENOSTATE);

  wipe = true;
  TSH_CHECK_OK(xfer->result);

  if (xfer->kind == NFC_XFER_APDU) {
    TSH_CHECK(xfer->rx_data != NULL && xfer->rx_data_len != NULL, TS_EINVAL);
    TSH_CHECK(*xfer->rx_data_len <= sizeof(resp->data), TS_ENOMEM);
    // Copy the response out of the RFAL buffer
    memcpy(resp->data, xfer->rx_data, *xfer->rx_data_len);
    resp->data_len = *xfer->rx_data_len;
  } else {
    ts_t status = nfc_parse_psk_frame(
        xfer->psk_rx_frame, rfalConvBitsToBytes(xfer->psk_rx_bits), resp->data,
        sizeof(resp->data), &resp->data_len);
    TSH_CHECK_OK(status);
  }

cleanup:
  if (wipe) {
    memset(xfer, 0, sizeof(nfc_xfer_t));
  }
  TSH_RETURN;
}

static void nfc_transceive_finish(ts_t result) {
  nfc_xfer_t *xfer = &g_st25_driver.xfer;

  if (ts_ok(result)) {
    // Postpone the next presence check so that it does not get between this
    // exchange and the one following it.
    //
    // The tag does not answer the PSK frame (RFAL_ERR_TIMEOUT) when an
    // ISO-DEP presence check (R(NAK) -> R(ACK)) happens between the applet
    // SELECT and the PSK frame. This contradicts the tag's API specification,
    // which requires it to answer presence checks at any time without
    // disturbing the session and states that the PSK exchange is independent
    // of the ISO-DEP state.
    g_last_check_time = ticks();
  }
  xfer->result = result;
  xfer->event_reported = false;
  xfer->state = NFC_XFER_DONE;
}

bool nfc_transceive_process(void) {
  nfc_xfer_t *xfer = &g_st25_driver.xfer;

  if (xfer->state != NFC_XFER_PENDING) {
    return false;
  }

  ReturnCode err = (xfer->kind == NFC_XFER_PSK)
                       ? rfalGetTransceiveStatus()
                       : rfalNfcDataExchangeGetStatus();

  if (err == RFAL_ERR_BUSY) {
    return true;
  }

  nfc_transceive_finish(err == RFAL_ERR_NONE ? TS_OK : TS_ENOEN);

  return false;
}

bool nfc_transceive_take_event(void) {
  if (g_st25_driver.xfer.state != NFC_XFER_DONE ||
      g_st25_driver.xfer.event_reported) {
    return false;
  }
  g_st25_driver.xfer.event_reported = true;
  return true;
}

static ts_t nfc_dev_read_info(nfc_dev_info_t *dev_info) {
  TSH_DECLARE;
  TSH_CHECK(rfalNfcIsDevActivated(rfalNfcGetState()), TS_ENOEN);

  rfalNfcDevice *nfc_device;
  ReturnCode ret = rfalNfcGetActiveDevice(&nfc_device);
  TSH_CHECK(ret == RFAL_ERR_NONE, TS_ENOEN);

  dev_info->tag_type = NFCA_UNKNOWN_TYPE;
  switch (nfc_device->type) {
    case RFAL_NFC_LISTEN_TYPE_NFCA:
      dev_info->type = NFC_DEV_TYPE_A;
      if (nfc_device->dev.nfca.type == RFAL_NFCA_T4T) {
        dev_info->tag_type = NFCA_T4T;
      } else if (nfc_device->dev.nfca.type == RFAL_NFCA_T2T) {
        dev_info->tag_type = NFCA_T2T;
      }
      break;
    case RFAL_NFC_LISTEN_TYPE_NFCB:
      dev_info->type = NFC_DEV_TYPE_B;
      dev_info->tag_type = NFCA_T4T;
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

  TSH_CHECK(nfc_device->nfcidLen <= NFC_MAX_UID_LEN, TS_ENOEN);
  memcpy(dev_info->uid, nfc_device->nfcid, nfc_device->nfcidLen);
  dev_info->uid_len = nfc_device->nfcidLen;

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

#endif
