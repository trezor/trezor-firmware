
#include <sys/irq.h>
#include <sys/systick.h>
#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include "../inc/io/nfc.h"
#include "card_emulation.h"
#include "ndef.h"
#include "nfc_internal.h"
#include "rfal_platform.h"

#include "../rfal/include/rfal_isoDep.h"
#include "../rfal/include/rfal_nfc.h"
#include "../rfal/include/rfal_nfca.h"
#include "../rfal/include/rfal_rf.h"
#include "../rfal/include/rfal_t2t.h"
#include "../rfal/include/rfal_utils.h"

#include "stm32u5xx_hal.h"

typedef struct {
  bool initialized;
  // SPI driver
  SPI_HandleTypeDef hspi;
  // NFC IRQ pin callback
  void (*nfc_irq_callback)(void);

  // Event callbacks
  void (*nfc_state_idle_cb)(void);
  void (*nfc_state_activated_cb)(void);

  EXTI_HandleTypeDef hEXTI;

  rfalNfcDiscoverParam disc_params;
} st25r3916b_driver_t;

static st25r3916b_driver_t g_st25r3916b_driver = {
    .initialized = false,
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

// static void parse_tag_header(uint8_t *data, uint16_t dataLen);
static char *hex2Str(unsigned char *data, size_t dataLen);

#define LM_SEL_RES \
  0x20U /*!<NFC-A SEL_RES configured for Type 4A Tag Platform    */
#define LM_NFCID2_BYTE1 \
  0x02U /*!<NFC-F SENSF_RES configured for Type 3 Tag Platform   */
#define LM_SC_BYTE1 \
  0x12U /*!<NFC-F System Code byte 1                             */
#define LM_SC_BYTE2 \
  0xFCU /*!<NFC-F System Code byte 2                             */
#define LM_PAD0 \
  0x00U /*!<NFC-F PAD0                                           */

/* P2P communication data */
static uint8_t NFCID3[] = {0x01, 0xFE, 0x03, 0x04, 0x05,
                           0x06, 0x07, 0x08, 0x09, 0x0A};
static uint8_t GB[] = {0x46, 0x66, 0x6d, 0x01, 0x01, 0x11, 0x02,
                       0x02, 0x07, 0x80, 0x03, 0x02, 0x00, 0x03,
                       0x04, 0x01, 0x32, 0x07, 0x01, 0x03};

/* NFC-A CE config */
/* 4-byte UIDs with first byte 0x08 would need random number for the subsequent
 * 3 bytes. 4-byte UIDs with first byte 0x*F are Fixed number, not unique, use
 * for this demo 7-byte UIDs need a manufacturer ID and need to assure
 * uniqueness of the rest.*/
static uint8_t ceNFCA_NFCID[] = {
    0x1, 0x2, 0x3, 0x4}; /* =_STM, 5F 53 54 4D NFCID1 / UID (4 bytes) */
static uint8_t ceNFCA_SENS_RES[] = {0x02,
                                    0x00};  /* SENS_RES / ATQA for 4-byte UID */
static uint8_t ceNFCA_SEL_RES = LM_SEL_RES; /* SEL_RES / SAK */

static uint8_t ceNFCF_nfcid2[] = {
    LM_NFCID2_BYTE1, 0xFE, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66};

/* NFC-F CE config */
static uint8_t ceNFCF_SC[] = {LM_SC_BYTE1, LM_SC_BYTE2};
static uint8_t ceNFCF_SENSF_RES[] = {
    0x01, /* SENSF_RES                                */
    0x02,    0xFE,    0x11, 0x22, 0x33,
    0x44,    0x55,    0x66, /* NFCID2 */
    LM_PAD0, LM_PAD0, 0x00, 0x00, 0x00,
    0x7F,    0x7F,    0x00, /* PAD0, PAD1, MRTIcheck, MRTIupdate, PAD2
                             */
    0x00,    0x00};         /* RD                                       */

static ReturnCode nfc_transcieve_blocking(uint8_t *txBuf, uint16_t txBufSize,
                                          uint8_t **rxBuf, uint16_t **rcvLen,
                                          uint32_t fwt);
static void nfc_card_emulator_loop(rfalNfcDevice *nfcDev);

#define MAX_HEX_STR 4
#define MAX_HEX_STR_LENGTH 512
char hexStr[MAX_HEX_STR][MAX_HEX_STR_LENGTH];
uint8_t hexStrIdx = 0;

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
  drv->hspi.Init.NSS = SPI_NSS_SOFT;  // For RFAL lib purpose, use software NSS
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

  ReturnCode ret;
  ret = rfalNfcInitialize();

  // Set default discovery parameters
  rfalNfcDefaultDiscParams(&drv->disc_params);

  if (ret != RFAL_ERR_NONE) {
    return NFC_ERROR;
  }

  drv->initialized = true;

  return NFC_OK;
}

nfc_status_t nfc_deinit() {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  if (!drv->initialized) {
    return NFC_OK;
  }

  // Deactivate rfal STM.
  rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_IDLE);
  while (rfalNfcGetState() != RFAL_NFC_STATE_IDLE) {
    rfalNfcWorker();
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

void rfal_callback(rfalNfcState st) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  switch (st) {
    case RFAL_NFC_STATE_IDLE:
      if (drv->nfc_state_idle_cb != NULL) {
        drv->nfc_state_idle_cb();
      }
      break;

    case RFAL_NFC_STATE_ACTIVATED:
      if (drv->nfc_state_activated_cb != NULL) {
        drv->nfc_state_activated_cb();
      }
      break;
    default:
      // State not reported
      break;
  }
}

nfc_status_t nfc_register_tech(nfc_tech_t tech) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  drv->disc_params.devLimit = 1;
  memcpy(&drv->disc_params.nfcid3, NFCID3, sizeof(NFCID3));
  memcpy(&drv->disc_params.GB, GB, sizeof(GB));
  drv->disc_params.GBLen = sizeof(GB);
  drv->disc_params.p2pNfcaPrio = true;
  drv->disc_params.totalDuration = 1000U;
  drv->disc_params.notifyCb = rfal_callback;

  if (drv->initialized == false) {
    return NFC_NOT_INITIALIZED;
  }

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
    card_emulation_init(ceNFCF_nfcid2);
    memcpy(drv->disc_params.lmConfigPA.SENS_RES, ceNFCA_SENS_RES,
           RFAL_LM_SENS_RES_LEN); /* Set SENS_RES / ATQA */
    memcpy(drv->disc_params.lmConfigPA.nfcid, ceNFCA_NFCID,
           RFAL_LM_NFCID_LEN_04); /* Set NFCID / UID */
    drv->disc_params.lmConfigPA.nfcidLen =
        RFAL_LM_NFCID_LEN_04; /* Set NFCID length to 4 bytes */
    drv->disc_params.lmConfigPA.SEL_RES =
        ceNFCA_SEL_RES; /* Set SEL_RES / SAK */
    drv->disc_params.techs2Find |= RFAL_NFC_LISTEN_TECH_A;
  }

  if (tech & NFC_CARD_EMU_TECH_F) {
    /* Set configuration for NFC-F CE */
    memcpy(drv->disc_params.lmConfigPF.SC, ceNFCF_SC,
           RFAL_LM_SENSF_SC_LEN); /* Set System Code */
    memcpy(&ceNFCF_SENSF_RES[RFAL_NFCF_CMD_LEN], ceNFCF_nfcid2,
           RFAL_NFCID2_LEN); /* Load NFCID2 on SENSF_RES */
    memcpy(drv->disc_params.lmConfigPF.SENSF_RES, ceNFCF_SENSF_RES,
           RFAL_LM_SENSF_RES_LEN); /* Set SENSF_RES / Poll Response */
    drv->disc_params.techs2Find |= RFAL_NFC_LISTEN_TECH_F;
  }

  return NFC_OK;
}

nfc_status_t nfc_register_event_callback(nfc_event_t event_type,
                                         void (*cb_fn)(void)) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  switch (event_type) {
    case NFC_STATE_IDLE:
      drv->nfc_state_idle_cb = cb_fn;
      break;
    case NFC_STATE_ACTIVATED:
      drv->nfc_state_activated_cb = cb_fn;
      break;
    default:
      return NFC_ERROR;
  }

  return NFC_OK;
}

nfc_status_t nfc_unregister_event_callback() {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;
  drv->disc_params.notifyCb = NULL;

  return NFC_OK;
}

nfc_status_t nfc_activate_stm() {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  ReturnCode err;
  err = rfalNfcDiscover(&(drv->disc_params));
  if (err != RFAL_ERR_NONE) {
    return NFC_ERROR;
  }

  return NFC_OK;
}

nfc_status_t nfc_deactivate_stm() {
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

nfc_status_t nfc_feed_worker() {
  static rfalNfcDevice *nfcDevice;

  rfalNfcWorker(); /* Run RFAL worker periodically */

  if (rfalNfcIsDevActivated(rfalNfcGetState())) {
    rfalNfcGetActiveDevice(&nfcDevice);

    switch (nfcDevice->type) {
      /*******************************************************************************/
      case RFAL_NFC_LISTEN_TYPE_NFCA:

        switch (nfcDevice->dev.nfca.type) {
          case RFAL_NFCA_T1T:
            break;

          case RFAL_NFCA_T4T:
            break;

          case RFAL_NFCA_T4T_NFCDEP:
          case RFAL_NFCA_NFCDEP:
            break;
          default:
            break;
        }

      /*******************************************************************************/
      case RFAL_NFC_LISTEN_TYPE_NFCB:
        break;

      /*******************************************************************************/
      case RFAL_NFC_LISTEN_TYPE_NFCF:
        break;

      /*******************************************************************************/
      case RFAL_NFC_LISTEN_TYPE_NFCV:
        break;

      /*******************************************************************************/
      case RFAL_NFC_LISTEN_TYPE_ST25TB:
        break;

      /*******************************************************************************/
      case RFAL_NFC_LISTEN_TYPE_AP2P:
      case RFAL_NFC_POLL_TYPE_AP2P:
        break;

      /*******************************************************************************/

      /*******************************************************************************/

      // Card emulators need to promptly respond to the reader commands, so when
      // activated rfal worker is called seveal times untill back to back
      // communication with the reader is completed. This may prolong the
      // run_feed_worker service time compared to standard reader mode.
      case RFAL_NFC_POLL_TYPE_NFCA:
      case RFAL_NFC_POLL_TYPE_NFCF:

        if (nfcDevice->rfInterface == RFAL_NFC_INTERFACE_NFCDEP) {
          // not supported yet
        } else {
          nfc_card_emulator_loop(nfcDevice);
        }
        break;

        break;

        break;
      /*******************************************************************************/
      default:
        break;
    }

    rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_DISCOVERY);
  }

  return NFC_OK;
}

static void nfc_card_emulator_loop(rfalNfcDevice *nfcDev) {
  ReturnCode err = RFAL_ERR_INTERNAL;
  uint8_t *rxData;
  uint16_t *rcvLen;
  uint8_t txBuf[150];
  uint16_t txLen;

  do {
    rfalNfcWorker();

    switch (rfalNfcGetState()) {
      case RFAL_NFC_STATE_ACTIVATED:
        err = nfc_transcieve_blocking(NULL, 0, &rxData, &rcvLen, 0);
        break;

      case RFAL_NFC_STATE_DATAEXCHANGE:
      case RFAL_NFC_STATE_DATAEXCHANGE_DONE:

        txLen = ((nfcDev->type == RFAL_NFC_POLL_TYPE_NFCA)
                     ? card_emulation_t4t(rxData, *rcvLen, txBuf, sizeof(txBuf))
                     : rfalConvBytesToBits(card_emulation_t3t(
                           rxData, rfalConvBitsToBytes(*rcvLen), txBuf,
                           sizeof(txBuf))));

        err = nfc_transcieve_blocking(txBuf, txLen, &rxData, &rcvLen,
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

nfc_status_t nfc_transceive(const uint8_t *txData, uint16_t txDataLen,
                            uint8_t *rxData, uint16_t *rxDataLen) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  if (drv->initialized == false) {
    return NFC_NOT_INITIALIZED;
  }

  if (rfalNfcGetState() != RFAL_NFC_STATE_IDLE) {
    return NFC_ERROR;
  }

  ReturnCode err;
  err = nfc_transcieve_blocking((uint8_t *)txData, txDataLen, &rxData,
                                &rxDataLen, RFAL_FWT_NONE);

  if (err != RFAL_ERR_NONE) {
    return NFC_ERROR;
  }

  return NFC_OK;
}

nfc_status_t nfc_def_write_ndef_uri() {
  // NDEF message
  uint8_t ndef_message[128] = {0};

  uint16_t buffer_len = create_ndef_uri("trezor.io/", ndef_message);

  for (uint8_t i = 0; i < buffer_len / 4; i++) {
    rfalT2TPollerWrite(4 + i, ndef_message + i * 4);
  }

  return NFC_OK;
}

nfc_status_t nfc_dev_read_info(nfc_dev_info_t *dev_info) {
  if (rfalNfcIsDevActivated(rfalNfcGetState())) {
    rfalNfcDevice *nfcDevice;
    rfalNfcGetActiveDevice(&nfcDevice);

    // Resolve device type
    switch (nfcDevice->type) {
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

    dev_info->uid_len = nfcDevice->nfcidLen;

    if (dev_info->uid_len > 10) {
      // Unexpected UID length
      return NFC_ERROR;
    }

    char *uid_str = hex2Str(nfcDevice->nfcid, nfcDevice->nfcidLen);
    memcpy(dev_info->uid, uid_str, nfcDevice->nfcidLen);

  } else {
    // No device activated
    return NFC_ERROR;
  }

  return NFC_OK;
}

// static void parse_tag_header(uint8_t *data, uint16_t dataLen) {
//   nfc_device_header_t2t_t hdr;

//   memcpy(hdr.UID, data, 3);
//   hdr.BCC[0] = data[3];
//   memcpy(hdr.UID + 3, data + 4, 4);
//   memcpy(hdr.SYSTEM_AREA, data + 8, 2);
//   memcpy(hdr.CC, data + 12, 4);

// }

static ReturnCode nfc_transcieve_blocking(uint8_t *txBuf, uint16_t txBufSize,
                                          uint8_t **rxData, uint16_t **rcvLen,
                                          uint32_t fwt) {
  ReturnCode err;

  err = rfalNfcDataExchangeStart(txBuf, txBufSize, rxData, rcvLen, fwt);
  if (err == RFAL_ERR_NONE) {
    do {
      rfalNfcWorker();
      err = rfalNfcDataExchangeGetStatus();
    } while (err == RFAL_ERR_BUSY);
  }
  return err;
}

static char *hex2Str(unsigned char *data, size_t dataLen) {
  {
    unsigned char *pin = data;
    const char *hex = "0123456789ABCDEF";
    char *pout = hexStr[hexStrIdx];
    uint8_t i = 0;
    uint8_t idx = hexStrIdx;
    if (dataLen == 0) {
      pout[0] = 0;
    } else {
      for (; i < dataLen - 1; ++i) {
        *pout++ = hex[(*pin >> 4) & 0xF];
        *pout++ = hex[(*pin++) & 0xF];
      }
      *pout++ = hex[(*pin >> 4) & 0xF];
      *pout++ = hex[(*pin) & 0xF];
      *pout = 0;
    }

    hexStrIdx++;
    hexStrIdx %= MAX_HEX_STR;

    return hexStr[idx];
  }
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

  u_diff = (timer - systick_ms());  // Calculate the diff between the timers
  s_diff = u_diff;                  // Convert the diff to a signed var

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
