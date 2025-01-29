
#include <sys/irq.h>
#include <sys/systick.h>
#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include "../inc/io/nfc.h"
#include "nfc_internal.h"
#include "rfal_platform.h"
#include "ndef.h"

#include "../rfal/include/rfal_isoDep.h"
#include "../rfal/include/rfal_nfc.h"
#include "../rfal/include/rfal_nfca.h"
#include "../rfal/include/rfal_rf.h"
#include "../rfal/include/rfal_t2t.h"
#include "../rfal/include/rfal_utils.h"
#include "prodtest_common.h"

#include "stm32u5xx_hal.h"

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-variable"

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-but-set-variable"

typedef struct {
  bool initialized;
  // SPI driver
  SPI_HandleTypeDef hspi;
  // NFC IRQ pin callback
  void (*nfc_irq_callback)(void);
  EXTI_HandleTypeDef hEXTI;

  rfalNfcDiscoverParam disc_params;
} st25r3916b_driver_t;

static st25r3916b_driver_t g_st25r3916b_driver = {
    .initialized = false,
};

static void parse_tag_header(uint8_t *data, uint16_t dataLen);

/* Definition of possible states the demo state machine could have */
#define DEMO_ST_CE_NOTINIT 0         /*!< Demo State:  Not initialized     */
#define DEMO_ST_CE_START_DISCOVERY 1 /*!< Demo State:  Start Discovery     */
#define DEMO_ST_CE_DISCOVERY 2       /*!< Demo State:  Discovery           */
#define DEMO_ST_CE_TAG_OPERATION 3   /*!< Demo State:  Discovery           */

/* Definition of possible states the demo state machine could have */
#define DEMO_ST_NOTINIT 0         /*!< Demo State:  Not initialized        */
#define DEMO_ST_START_DISCOVERY 1 /*!< Demo State:  Start Discovery        */
#define DEMO_ST_DISCOVERY 2       /*!< Demo State:  Discovery              */

#define DEMO_NFCV_BLOCK_LEN 4 /*!< NFCV Block len                      */
#define DEMO_NFCV_USE_SELECT_MODE \
  false /*!< NFCV demonstrate select mode        */

/*
******************************************************************************
* GLOBAL DEFINES
******************************************************************************
*/



/* Definition of possible states the demo state machine could have */
#define DEMO_ST_NOTINIT 0         /*!< Demo State:  Not initialized | Stopped */
#define DEMO_ST_START_DISCOVERY 1 /*!< Demo State:  Start Discovery */
#define DEMO_ST_DISCOVERY 2       /*!< Demo State:  Discovery                 */

#define DEMO_NFCV_BLOCK_LEN 4 /*!< NFCV Block len                         */

#define DEMO_NFCV_USE_SELECT_MODE \
  false                           /*!< NFCV demonstrate select mode           */
#define DEMO_NFCV_WRITE_TAG false /*!< NFCV demonstrate Write Single Block */

/* Definition of various Listen Mode constants */
#if defined(DEMO_LISTEN_MODE_TARGET)
#define DEMO_LM_SEL_RES \
  0x40U /*!<NFC-A SEL_RES configured for the NFC-DEP protocol    */
#define DEMO_LM_NFCID2_BYTE1 \
  0x01U /*!<NFC-F SENSF_RES configured for the NFC-DEP protocol  */
#define DEMO_LM_SC_BYTE1 \
  0xFFU /*!<NFC-F System Code byte 1                             */
#define DEMO_LM_SC_BYTE2 \
  0xFFU /*!<NFC-F System Code byte 2                             */
#define DEMO_LM_PAD0 \
  0xFFU /*!<NFC-F PAD0                                           */
#else
#define DEMO_LM_SEL_RES \
  0x20U /*!<NFC-A SEL_RES configured for Type 4A Tag Platform    */
#define DEMO_LM_NFCID2_BYTE1 \
  0x02U /*!<NFC-F SENSF_RES configured for Type 3 Tag Platform   */
#define DEMO_LM_SC_BYTE1 \
  0x12U /*!<NFC-F System Code byte 1                             */
#define DEMO_LM_SC_BYTE2 \
  0xFCU /*!<NFC-F System Code byte 2                             */
#define DEMO_LM_PAD0 \
  0x00U /*!<NFC-F PAD0                                           */
#endif

/*
 ******************************************************************************
 * GLOBAL MACROS
 ******************************************************************************
 */

/*
 ******************************************************************************
 * LOCAL VARIABLES
 ******************************************************************************
 */

/* P2P communication data */
static uint8_t NFCID3[] = {0x01, 0xFE, 0x03, 0x04, 0x05,
                           0x06, 0x07, 0x08, 0x09, 0x0A};
static uint8_t GB[] = {0x46, 0x66, 0x6d, 0x01, 0x01, 0x11, 0x02,
                       0x02, 0x07, 0x80, 0x03, 0x02, 0x00, 0x03,
                       0x04, 0x01, 0x32, 0x07, 0x01, 0x03};

/* APDUs communication data */
#if RFAL_FEATURE_ISO_DEP_POLL
static uint8_t ndefSelectApp[] = {0x00, 0xA4, 0x04, 0x00, 0x07, 0xD2, 0x76,
                                  0x00, 0x00, 0x85, 0x01, 0x01, 0x00};
static uint8_t ccSelectFile[] = {0x00, 0xA4, 0x00, 0x0C, 0x02, 0xE1, 0x03};
static uint8_t readBinary[] = {0x00, 0xB0, 0x00, 0x00, 0x0F};

/* For a Payment application a Select PPSE would be needed:
   ppseSelectApp[] = { 0x00, 0xA4, 0x04, 0x00, 0x0E, 0x32, 0x50, 0x41, 0x59,
   0x2E, 0x53, 0x59, 0x53, 0x2E, 0x44, 0x44, 0x46, 0x30, 0x31, 0x00 } */
#endif /* RFAL_FEATURE_ISO_DEP_POLL */

#if RFAL_FEATURE_NFC_DEP
/* P2P communication data */
static uint8_t ndefLLCPSYMM[] = {0x00, 0x00};
static uint8_t ndefInit[] = {0x05, 0x20, 0x06, 0x0F, 0x75, 0x72, 0x6E,
                             0x3A, 0x6E, 0x66, 0x63, 0x3A, 0x73, 0x6E,
                             0x3A, 0x73, 0x6E, 0x65, 0x70, 0x02, 0x02,
                             0x07, 0x80, 0x05, 0x01, 0x02};
static uint8_t ndefUriSTcom[] = {
    0x13, 0x20, 0x00, 0x10, 0x02, 0x00, 0x00, 0x00, 0x19, 0xc1, 0x01, 0x00,
    0x00, 0x00, 0x12, 0x55, 0x00, 0x68, 0x74, 0x74, 0x70, 0x3a, 0x2f, 0x2f,
    0x77, 0x77, 0x77, 0x2e, 0x73, 0x74, 0x2e, 0x63, 0x6f, 0x6d};
#endif /* RFAL_FEATURE_NFC_DEP */

#if RFAL_SUPPORT_CE && RFAL_FEATURE_LISTEN_MODE
#if RFAL_SUPPORT_MODE_LISTEN_NFCA
/* NFC-A CE config */
/* 4-byte UIDs with first byte 0x08 would need random number for the subsequent
 * 3 bytes. 4-byte UIDs with first byte 0x*F are Fixed number, not unique, use
 * for this demo 7-byte UIDs need a manufacturer ID and need to assure
 * uniqueness of the rest.*/
static uint8_t ceNFCA_NFCID[] = {
    0x5F, 'S', 'T', 'M'}; /* =_STM, 5F 53 54 4D NFCID1 / UID (4 bytes) */
static uint8_t ceNFCA_SENS_RES[] = {0x02,
                                    0x00}; /* SENS_RES / ATQA for 4-byte UID */
static uint8_t ceNFCA_SEL_RES = DEMO_LM_SEL_RES; /* SEL_RES / SAK */
#endif /* RFAL_SUPPORT_MODE_LISTEN_NFCA */

static uint8_t ceNFCF_nfcid2[] = {
    DEMO_LM_NFCID2_BYTE1, 0xFE, 0x11, 0x22, 0x33, 0x44, 0x55, 0x66};

#if RFAL_SUPPORT_MODE_LISTEN_NFCF
/* NFC-F CE config */
static uint8_t ceNFCF_SC[] = {DEMO_LM_SC_BYTE1, DEMO_LM_SC_BYTE2};
static uint8_t ceNFCF_SENSF_RES[] = {
    0x01, /* SENSF_RES                                */
    0x02,         0xFE,         0x11, 0x22, 0x33,
    0x44,         0x55,         0x66, /* NFCID2 */
    DEMO_LM_PAD0, DEMO_LM_PAD0, 0x00, 0x00, 0x00,
    0x7F,         0x7F,         0x00, /* PAD0, PAD1, MRTIcheck, MRTIupdate, PAD2
                                       */
    0x00,         0x00}; /* RD                                       */
#endif                   /* RFAL_SUPPORT_MODE_LISTEN_NFCF */
#endif                   /* RFAL_SUPPORT_CE && RFAL_FEATURE_LISTEN_MODE */

/*
 ******************************************************************************
 * LOCAL VARIABLES
 ******************************************************************************
 */

// static void demoNotif(rfalNfcState st);
// static bool demoInit();
// static void demoCycle();
// static void demoP2P(rfalNfcDevice *nfcDev);
// static void demoAPDU(void);
// static void demoNfcv(rfalNfcvListenDevice *nfcvDev);
// static void demoNfcf(rfalNfcfListenDevice *nfcfDev);
// static void demoT2t(void);
// static void demoCE(rfalNfcDevice *nfcDev);
ReturnCode demoTransceiveBlocking(uint8_t *txBuf, uint16_t txBufSize,
                                  uint8_t **rxBuf, uint16_t **rcvLen,
                                  uint32_t fwt);



#define MAX_HEX_STR 4
#define MAX_HEX_STR_LENGTH 512
char hexStr[MAX_HEX_STR][MAX_HEX_STR_LENGTH];
uint8_t hexStrIdx = 0;



char *hex2Str(unsigned char *data, size_t dataLen) {
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

typedef struct{
  uint8_t UID[7];
  uint8_t BCC[1];
  uint8_t SYSTEM_AREA[2];
  union{
    uint8_t CC[4];
    struct{
      uint8_t CC_MAGIC_NUMBER;
      uint8_t CC_VERSION;
      uint8_t CC_SIZE;
      uint8_t CC_ACCESS_CONDITION;
    };
  };
} type2_header_t;

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

nfc_status_t nfc_register_card_emu(nfc_card_emul_tech_t tech) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  // In case the NFC state machine is active, deactivate to idle before
  // registering a new card emulation technology.
  if (rfalNfcGetState() != RFAL_NFC_STATE_IDLE) {
    rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_IDLE);
    do {
      rfalNfcWorker();
    } while (rfalNfcGetState() != RFAL_NFC_STATE_IDLE);
  }

  drv->disc_params.devLimit = 1;
  memcpy(&drv->disc_params.nfcid3, NFCID3, sizeof(NFCID3));
  memcpy(&drv->disc_params.GB, GB, sizeof(GB));
  drv->disc_params.GBLen = sizeof(GB);
  drv->disc_params.p2pNfcaPrio = true;
  drv->disc_params.totalDuration = 1000U;

  switch (tech) {
    case NFC_CARD_EMU_TECH_A:
      memcpy(drv->disc_params.lmConfigPA.SENS_RES, ceNFCA_SENS_RES,
             RFAL_LM_SENS_RES_LEN); /* Set SENS_RES / ATQA */
      memcpy(drv->disc_params.lmConfigPA.nfcid, ceNFCA_NFCID,
             RFAL_LM_NFCID_LEN_04); /* Set NFCID / UID */
      drv->disc_params.lmConfigPA.nfcidLen =
          RFAL_LM_NFCID_LEN_04; /* Set NFCID length to 4 bytes */
      drv->disc_params.lmConfigPA.SEL_RES =
          ceNFCA_SEL_RES; /* Set SEL_RES / SAK */
      drv->disc_params.techs2Find |= RFAL_NFC_LISTEN_TECH_A;
      break;
    case NFC_CARD_EMU_TECH_V:
      drv->disc_params.techs2Find |= RFAL_NFC_POLL_TECH_V;
      break;
    default:
      return NFC_ERROR;
  }

  return NFC_OK;
}

nfc_status_t nfc_register_poller(nfc_poller_tech_t tech) {
  st25r3916b_driver_t *drv = &g_st25r3916b_driver;

  // In case the NFC state machine is active, deactivate to idle before
  // registering a new card emulation technology.
  if (rfalNfcGetState() != RFAL_NFC_STATE_IDLE) {
    rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_IDLE);
    do {
      rfalNfcWorker();
    } while (rfalNfcGetState() != RFAL_NFC_STATE_IDLE);
  }

  drv->disc_params.devLimit = 1;
  memcpy(&drv->disc_params.nfcid3, NFCID3, sizeof(NFCID3));
  memcpy(&drv->disc_params.GB, GB, sizeof(GB));
  drv->disc_params.GBLen = sizeof(GB);
  drv->disc_params.p2pNfcaPrio = true;
  drv->disc_params.totalDuration = 1000U;

  switch (tech) {
    case NFC_POLLER_TECH_A:
      drv->disc_params.techs2Find |= RFAL_NFC_POLL_TECH_A;
      break;
    case NFC_POLLER_TECH_B:
      drv->disc_params.techs2Find |= RFAL_NFC_POLL_TECH_B;
      break;
    case NFC_POLLER_TECH_F:
      drv->disc_params.techs2Find |= RFAL_NFC_POLL_TECH_F;
      break;
    case NFC_POLLER_TECH_V:
      drv->disc_params.techs2Find |= RFAL_NFC_POLL_TECH_V;
      break;
    default:
      return NFC_ERROR;
  }

  ReturnCode err;
  err = rfalNfcDiscover(&drv->disc_params);
  if (err != RFAL_ERR_NONE) {
    return NFC_ERROR;
  }

  return NFC_OK;
}

nfc_status_t nfc_run_worker() {
  static rfalNfcDevice *nfcDevice;

  rfalNfcWorker(); /* Run RFAL worker periodically */

  if (rfalNfcIsDevActivated(rfalNfcGetState())) {
    rfalNfcGetActiveDevice(&nfcDevice);

    switch (nfcDevice->type) {
      /*******************************************************************************/
      case RFAL_NFC_LISTEN_TYPE_NFCA:

        switch (nfcDevice->dev.nfca.type) {
          case RFAL_NFCA_T1T:
            vcp_println("ISO14443A/Topaz (NFC-A T1T) TAG found. UID: %s\r\n",
                        hex2Str(nfcDevice->nfcid, nfcDevice->nfcidLen));

            break;

          case RFAL_NFCA_T4T:
            vcp_println("NFCA Passive ISO-DEP device found. UID: %s\r\n",
                        hex2Str(nfcDevice->nfcid, nfcDevice->nfcidLen));

            break;

          case RFAL_NFCA_T4T_NFCDEP:
          case RFAL_NFCA_NFCDEP:
            break;
          default:
            vcp_println("ISO14443A/NFC-A card found. UID: %s\r\n",
                        hex2Str(nfcDevice->nfcid, nfcDevice->nfcidLen));

            ReturnCode err;
            uint16_t rcvLen;
            uint8_t blockNum = 0;
            uint8_t rxBuf[16];

            vcp_println("Tag ID len: %d", nfcDevice->nfcidLen);

            // Read first 16 bytes (1st block)
            err = rfalT2TPollerRead(0, rxBuf, sizeof(rxBuf), &rcvLen);
            parse_tag_header(rxBuf, sizeof(rxBuf));

            uint8_t memory_area_data[160] = {0};
            for (uint8_t i = 0; i < 10; i++) {
              err = rfalT2TPollerRead(4+i*4, memory_area_data+i*16, 16 , &rcvLen);
            }

            ndef_record_t record;
            parse_ndef_record(memory_area_data+2, 160, &record);
            vcp_println("Record payload: %s", record.payload);






            break;
        }

      /*******************************************************************************/
      case RFAL_NFC_LISTEN_TYPE_NFCB:

        vcp_println("NFC TYPE B card found. UID: %s\r\n",
                    hex2Str(nfcDevice->nfcid, nfcDevice->nfcidLen));

        break;

      /*******************************************************************************/
      case RFAL_NFC_LISTEN_TYPE_NFCF:

        vcp_println("NFC TYPE F card found. UID: %s\r\n",
                    hex2Str(nfcDevice->nfcid, nfcDevice->nfcidLen));

        break;

      /*******************************************************************************/
      case RFAL_NFC_LISTEN_TYPE_NFCV:

        vcp_println("NFC TYPE V card found. UID: %s\r\n",
                    hex2Str(nfcDevice->nfcid, nfcDevice->nfcidLen));

        break;

      /*******************************************************************************/
      case RFAL_NFC_LISTEN_TYPE_ST25TB:

        vcp_println("ST25TB card found. UID: %s\r\n",
                    hex2Str(nfcDevice->nfcid, nfcDevice->nfcidLen));
        break;

      /*******************************************************************************/
      case RFAL_NFC_LISTEN_TYPE_AP2P:
      case RFAL_NFC_POLL_TYPE_AP2P:
        break;

      /*******************************************************************************/
      case RFAL_NFC_POLL_TYPE_NFCA:
        break;
      case RFAL_NFC_POLL_TYPE_NFCF:
        break;
      /*******************************************************************************/
      default:
        break;
    }

    rfalNfcDeactivate(RFAL_NFC_DEACTIVATE_DISCOVERY);

  }

  return NFC_OK;
}



static void parse_tag_header(uint8_t *data, uint16_t dataLen){

  type2_header_t hdr;

  memcpy(hdr.UID, data, 3);
  hdr.BCC[0] = data[3];
  memcpy(hdr.UID + 3, data+4, 4);
  memcpy(hdr.SYSTEM_AREA, data+8, 2);
  memcpy(hdr.CC, data+12, 4);

  vcp_println("UID: %s", hex2Str(hdr.UID, sizeof(hdr.UID)));
  vcp_println("BCC: %s (%s)", hex2Str(hdr.BCC, sizeof(hdr.BCC)), (0x88 == (hdr.UID[0] ^ hdr.UID[1] ^ hdr.UID[2] ^ hdr.BCC[0]))? " CHECKSUM PASSED" : "CHECKSUM FAILED");
  vcp_println("SYSTEM_AREA: %s", hex2Str(hdr.SYSTEM_AREA, sizeof(hdr.SYSTEM_AREA)));
  vcp_println("CC: %s", hex2Str(hdr.CC, sizeof(hdr.CC)));
  vcp_println(" -> CC_MAGIC_NUMBER: %02X", hdr.CC_MAGIC_NUMBER);
  vcp_println(" -> CC_VERSION: %02X", hdr.CC_VERSION);
  vcp_println(" -> CC_SIZE: %02X (%d bytes)", hdr.CC_SIZE, hdr.CC_SIZE*8);
  vcp_println(" -> CC_ACCESS_CONDITION: %02X", hdr.CC_ACCESS_CONDITION);

}


/*!
 *****************************************************************************
 * \brief Demo Blocking Transceive
 *
 * Helper function to send data in a blocking manner via the rfalNfc module
 *
 * \warning A protocol transceive handles long timeouts (several seconds),
 * transmission errors and retransmissions which may lead to a long period of
 * time where the MCU/CPU is blocked in this method.
 * This is a demo implementation, for a non-blocking usage example please
 * refer to the Examples available with RFAL
 *
 * \param[in]  txBuf      : data to be transmitted
 * \param[in]  txBufSize  : size of the data to be transmited
 * \param[out] rxData     : location where the received data has been placed
 * \param[out] rcvLen     : number of data bytes received
 * \param[in]  fwt        : FWT to be used (only for RF frame interface,
 *                                          otherwise use RFAL_FWT_NONE)
 *
 *  \return RFAL_ERR_PARAM     : Invalid parameters
 *  \return RFAL_ERR_TIMEOUT   : Timeout error
 *  \return RFAL_ERR_FRAMING   : Framing error detected
 *  \return RFAL_ERR_PROTO     : Protocol error detected
 *  \return RFAL_ERR_NONE      : No error, activation successful
 *
 *****************************************************************************
 */
ReturnCode demoTransceiveBlocking(uint8_t *txBuf, uint16_t txBufSize,
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
