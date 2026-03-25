/**
 ******************************************************************************
 * @file    card_emulation.c
 * @author  MMY Application Team
 * @brief   Body function to manage card emul mode
 ******************************************************************************
 ** This notice applies to any and all portions of this file
 * that are not between comment pairs USER CODE BEGIN and
 * USER CODE END. Other portions of this file, whether
 * inserted by the user or by software development tools
 * are owned by their respective copyright owners.
 *
 * COPYRIGHT(c) 2018 STMicroelectronics
 ******************************************************************************
 */
#ifdef KERNEL_MODE

/* Includes ------------------------------------------------------------------*/
#include "card_emulation.h"
#include "rfal_nfca.h"
#include "rfal_nfcf.h"
#include "rfal_rf.h"

/** @addtogroup X-CUBE-NFC6_Applications
 *  @{
 */

/** @addtogroup CardEmulation
 *  @{
 */

/** @addtogroup CE_CardEmul
 * @{
 */

/* Private typedef -----------------------------------------------------------*/
/** @defgroup CE_CardEmul_Private_Typedef
 * @{
 */
enum States {
  STATE_IDLE = 0,         /*!< Emulated Tag state idle                  */
  STATE_APP_SELECTED = 1, /*!< Emulated Tag state application selected  */
  STATE_CC_SELECTED = 2,  /*!< Emulated Tag state CCFile selected       */
  STATE_FID_SELECTED = 3, /*!< Emulated Tag state FileID selected       */
};
/**
 * @}
 */

/* Private define ------------------------------------------------------------*/
/** @defgroup CE_CardEmul_Private_Define
 * @{
 */

#define NDEF_SIZE 2048  /*!< Max NDEF size emulated. Range: 0005h - 7FFFh    */
#define T4T_CLA_00 0x00 /*!< CLA value for type 4 command */
#define T4T_INS_SELECT \
  0xA4 /*!< INS value for select command                    */
#define T4T_INS_READ \
  0xB0 /*!< INS value for reabbinary command                */
#define T4T_INS_UPDATE \
  0xD6                  /*!< INS value for update command                    */
#define FID_CC 0xE103   /*!< File ID number for CCFile                       */
#define FID_NDEF 0x0001 /*!< File ID number for NDEF file */
#define T3T_BLOCK_SIZE \
  0x10 /*!< Block size in Type 3 Tag                        */
/**
 * @}
 */

/* Private macro -------------------------------------------------------------*/
/* Private variables ---------------------------------------------------------*/
/** @defgroup CE_CardEmul_Private_Variables
 * @{
 */
static uint8_t gNfcfNfcid[RFAL_NFCF_NFCID2_LEN];
static uint8_t ndefFile[NDEF_SIZE]; /*!< Buffer to store NDEF File */
static int8_t nState = STATE_IDLE;  /*!< Type 4 tag emulation status  */
static int32_t nSelectedIdx = -1;   /*!< current file selected   */
static int32_t nFiles = 2; /*!< Number of file emulated                   */

/**
 * CCLEN : Indicates the size of this CC File <BR>
 * T4T_VNo : Indicates the Mapping Version <BR>
 * MLe high : Max R-APDU size <BR>
 * MLc high : Max C-APDU size <BR>
 * NDEF FCI T: Indicates the NDEF-File_Ctrl_TLV <BR>
 * NDEF FCI L: The length of the V-field <BR>
 * NDEF FCI V1: NDEF File Identifier <BR>
 * NDEF FCI V2: NDEF File size <BR>
 * NDEF FCI V3: NDEF Read AC <BR>
 * NDEF FCI V4: NDEF Write AC <BR>
 */
static uint8_t ccfile[] = {
    0x00,
    0x0F, /* CCLEN      */
    0x20, /* T4T_VNo    */
    0x00,
    0x7F, /* MLe        */
    0x00,
    0x7F, /* MLc        */
    0x04, /* T          */
    0x06, /* L          */
    (FID_NDEF & 0xFF00) >> 8,
    (FID_NDEF & 0x00FF), /* V1         */
    (NDEF_SIZE & 0xFF00) >> 8,
    (NDEF_SIZE & 0x00FF), /* V2         */
    0x00,                 /* V3         */
    0x00                  /* V4         */
};

static uint32_t pdwFileSize[] = {sizeof(ccfile),
                                 NDEF_SIZE}; /*!< Current emulated files size */

/**
 * NDEF length <BR>
 * NDEF Header: MB,ME,SR,Well known Type <BR>
 * NDEF type length <BR>
 * NDEF payload length <BR>
 * NDEF Type : URI <BR>
 * NDEF URI abreviation field : http://www. <BR>
 * NDEF URI string : st.com/st25-demo <BR>
 */
static const uint8_t ndef_uri[] = {
    0x00, 0x15, /* NDEF length                */
    0xD1,       /* NDEF Header                */
    0x01,       /* NDEF type length           */
    0x11,       /* NDEF payload length        */
    0x55,       /* NDEF Type                  */
    0x01,       /* NDEF URI abreviation field */
    0x74, 0x72, 0x65, 0x7A, 0x6F, 0x72, 0x2E, 0x69, 0x6F}; /* NDEF URI string */

__WEAK const uint8_t *NdefFile = ndef_uri;
__WEAK uint32_t NdefFileLen = sizeof(ndef_uri);

/**
 * Ver : Indicates the NDEF mapping version <BR>
 * Nbr : Indicates the number of blocks that can be read <BR>
 * Nbw : Indicates the number of blocks that can be written <BR>
 * NmaxB : Indicates the maximum number of blocks available for NDEF data <BR>
 * WriteFlag : Indicates whether a previous NDEF write procedure has finished or
 * not <BR> RWFlag : Indicates data can be updated or not <BR> Ln : Is the size
 * of the actual stored NDEF data in bytes <BR> Checksum : allows the
 * Reader/Writer to check whether the Attribute Data are correct <BR>
 */
static uint8_t InformationBlock[] = {
    0x10,                   /* Ver        */
    0x08,                   /* Nbr        */
    0x08,                   /* Nbw        */
    0x00, 0x0F,             /* NmaxB      */
    0x00, 0x00, 0x00, 0x00, /* RFU        */
    0x00,                   /* WriteFlag  */
    0x01,                   /* RWFlag     */
    0x00, 0x00, 0x15,       /* Ln         */
    0x00, 0x45              /* Checksum   */
};
/**
 * @}
 */

/* Private function prototypes -----------------------------------------------*/

/* Private functions ---------------------------------------------------------*/
/** @defgroup CE_CardEmul_Private_Functions
 * @{
 */

/**
 *****************************************************************************
 * @brief  Compare 2 commands supplied in parameters
 *
 * @param[in]  cmd : pointer to the received command.
 * @param[in]  find : pointer to the avalaible command.
 * @param[in]  len : length of the available command.
 *
 * @retval True : Same command.
 * @retval False : Different command.
 *****************************************************************************
 */
static bool cmd_compare(uint8_t *cmd, uint8_t *find, uint16_t len) {
  for (int i = 0; i < 20; i++) {
    if (!memcmp(&cmd[i], find, len)) {
      return true;
    }
  }
  return false;
}

/**
 *****************************************************************************
 * @brief  Manage the T4T Select answer to the reader
 *
 * @param[in]  cmdData    : pointer to the received command.
 * @param[out] rspData    : pointer to the answer to send.
 *
 * @return Answer size.
 *****************************************************************************
 */
static uint16_t card_emulation_t4t_select(uint8_t *cmdData, uint8_t *rspData) {
  bool success = false;
  /*
   * Cmd: CLA(1) | INS(1) | P1(1) | P2(1) | Lc(1) | Data(n) | [Le(1)]
   * Rsp: [FCI(n)] | SW12
   *
   * Select App by Name NDEF:       00 A4 04 00 07 D2 76 00 00 85 01 01 00
   * Select App by Name NDEF 4 ST:  00 A4 04 00 07 A0 00 00 00 03 00 00 00
   * Select CC FID:                 00 A4 00 0C 02 xx xx
   * Select NDEF FID:               00 A4 00 0C 02 xx xx
   */

  uint8_t aid[] = {0xD2, 0x76, 0x00, 0x00, 0x85, 0x01, 0x01};
  uint8_t fidCC[] = {FID_CC >> 8, FID_CC & 0xFF};
  uint8_t fidNDEF[] = {FID_NDEF >> 8, FID_NDEF & 0xFF};
  uint8_t selectFileId[] = {0xA4, 0x00, 0x0C, 0x02, 0x00, 0x01};

  if (cmd_compare(cmdData, aid, sizeof(aid))) { /* Select Appli */
    nState = STATE_APP_SELECTED;
    success = true;
  } else if ((nState >= STATE_APP_SELECTED) &&
             cmd_compare(cmdData, fidCC, sizeof(fidCC))) { /* Select CC */
    nState = STATE_CC_SELECTED;
    nSelectedIdx = 0;
    success = true;
  } else if ((nState >= STATE_APP_SELECTED) &&
             (cmd_compare(cmdData, fidNDEF, sizeof(fidNDEF)) ||
              cmd_compare(cmdData, selectFileId,
                          sizeof(selectFileId)))) { /* Select NDEF */
    nState = STATE_FID_SELECTED;
    nSelectedIdx = 1;
    success = true;
  } else {
    nState = STATE_IDLE;
  }

  rspData[0] = (success ? (char)0x90 : 0x6A);
  rspData[1] = (success ? (char)0x00 : 0x82);

  return 2;
}

/**
 *****************************************************************************
 * @brief  Manage the T4T Read answer to the reader
 *
 * @param[in]  cmdData    : pointer to the received command.
 * @param[out] rspData    : pointer to the answer to send.
 * @param[in]  rspDataLen : size of the answer buffer.
 *
 * @return Answer size.
 *****************************************************************************
 */
static uint16_t card_emulation_t4t_read(uint8_t *cmdData, uint8_t *rspData,
                                        uint16_t rspDataLen) {
  /*
   * Cmd: CLA(1) | INS(1) | P1(1).. offset inside file high | P2(1).. offset
   * inside file high | Le(1).. nBytes to read Rsp: BytesRead | SW12
   */
  unsigned short offset = (cmdData[2] << 8) | cmdData[3];
  unsigned short toRead = cmdData[4];
  uint8_t *ppbMemory;

  if (rspDataLen < 2) {
    // platformErrorHandle();  /* Must ensure appropriate buffer */
  }

  /* Any file selected */
  if (nSelectedIdx < 0 || nSelectedIdx >= nFiles) {
    rspData[0] = ((char)0x6A);
    rspData[1] = ((char)0x82);
    return 2;
  }

  /* offset + length exceed file size */
  if ((unsigned long)(offset + toRead) > pdwFileSize[nSelectedIdx]) {
    toRead = pdwFileSize[nSelectedIdx] - offset;
  }

  if (rspDataLen < (toRead + 2)) {
    rspData[0] = ((char)0x6F);
    rspData[1] = ((char)0x00);
    return 2;
  }

  ppbMemory = (nSelectedIdx == 0 ? ccfile : ndefFile);
  /* read data */
  memcpy(rspData, &ppbMemory[offset], toRead);

  rspData[toRead] = ((char)0x90);
  rspData[toRead + 1] = ((char)0x00);
  return toRead + 2;
}

/**
 *****************************************************************************
 * @brief  Manage the T4T Update answer to the reader
 *
 * @param[in]  cmdData : pointer to the received command.
 * @param[in]  rspData : pointer to the answer to send.
 *
 * @return Answer size.
 *****************************************************************************
 */
static uint16_t card_emulation_t4t_update(uint8_t *cmdData, uint8_t *rspData) {
  uint32_t offset = (cmdData[2] << 8) | cmdData[3];
  uint32_t length = cmdData[4];

  if (nSelectedIdx != 1) {
    rspData[0] = ((char)0x6A);
    rspData[1] = ((char)0x82);
    return 2;
  }

  if ((unsigned long)(offset + length) > pdwFileSize[nSelectedIdx]) {
    rspData[0] = ((char)0x62);
    rspData[1] = ((char)0x82);
    return 2;
  }

  memcpy((ndefFile + offset), &cmdData[5], length);

  rspData[0] = ((char)0x90);
  rspData[1] = ((char)0x00);
  return 2;
}

/**
 *****************************************************************************
 * @brief  Manage the T4T Read answer to the reader
 *
 * @param[in]  cmdData    : pointer to the received command.
 * @param[out] rspData    : pointer to the answer to send.
 * @param[in]  rspDataLen : size of the answer buffer.
 *
 * @return Answer size.
 *****************************************************************************
 */
static uint16_t card_emulation_t3t_check(uint8_t *cmdData, uint8_t *rspData,
                                         uint16_t rspDataLen) {
  /*
   * Cmd: cmd | NFCID2 | NoS | Service code list | NoB | Block list
   * Rsp: rsp | NFCID2 | Status Flag 1 | Status Flag 2 | NoB | Block Data
   */
  uint8_t *block;
  uint16_t blocknb[256];
  uint32_t idx = 0;
  uint32_t cnt = 0;
  uint32_t nbmax = 0;

  /* Command response */
  rspData[idx++] = RFAL_NFCF_CMD_READ_WITHOUT_ENCRYPTION + 1;

  /* NFCID 2 bytes */
  if (memcmp(gNfcfNfcid, &cmdData[RFAL_NFCF_LENGTH_LEN + RFAL_NFCF_CMD_LEN],
             RFAL_NFCF_NFCID2_LEN) == 0) {
    memcpy(&rspData[idx], &gNfcfNfcid, RFAL_NFCF_NFCID2_LEN);
    idx += RFAL_NFCF_NFCID2_LEN;
  } else {
    /* If NFCID2 in command is different, no answer */
    return 0;
  }

  /* Check for command errors */
  if ((cmdData[10] != 1) || ((cmdData[11] != 0x09) && (cmdData[11] != 0x0B)) ||
      (cmdData[13] == 0) || (cmdData[13] > InformationBlock[1])) {
    rspData[idx++] = 0xFF;
    rspData[idx++] = 0xFF;
    return idx;
  } else {
    rspData[idx++] = 0x00;
    rspData[idx++] = 0x00;
  }

  /* Verify CHECK response length */
  if (rspDataLen < (11 + (cmdData[13] * T3T_BLOCK_SIZE))) {
    // platformErrorHandle();  /* Must ensure appropriate buffer */
  }

  /* Nob */
  rspData[idx++] = cmdData[13];

  /* Retrieving block to read */
  block = &cmdData[14];
  for (cnt = 0; cnt < cmdData[13]; cnt++) {
    /* TS T3T 5.6.1.5 Service Code List Order value SHALL be between 0 and NoS-1
     */
    if (((*block) & 0x0F) >= cmdData[10]) {
      rspData[idx - 3] = 0xFF;
      rspData[idx - 2] = 0x80; /* TS T3T table 13 - proprietary value to
                                  indicate specific error conditions.*/
      return (idx - 1);
    }
    /* Check block list element size */
    if (*block & 0x80) {
      /* 2-byte Block List element */
      blocknb[cnt] = *(block + 1);
      block += 2;
    } else {
      /* 3-byte Block List element */
      blocknb[cnt] = *(block + 2); /* Little Endian Format */
      blocknb[cnt] <<= 8;
      blocknb[cnt] |= *(block + 1);
      block += 3;
    }

    /* Return error if Blocknb > NmaxB */
    nbmax = InformationBlock[3];
    nbmax = (nbmax << 8) | InformationBlock[4];
    if (blocknb[cnt] > nbmax) {
      rspData[idx - 3] = 0xFF;
      rspData[idx - 2] = 0x70;
      return (idx - 1);
    }
  }

  for (cnt = 0; cnt < cmdData[13]; cnt++) {
    if (blocknb[cnt] == 0x0000) {
      /* Read information block */
      memcpy(&rspData[idx], InformationBlock, sizeof(InformationBlock));
      idx += sizeof(InformationBlock);
    } else {
      /* Read ndef block */
      memcpy(&rspData[idx],
             &ndefFile[2 + ((blocknb[cnt] - 1) * T3T_BLOCK_SIZE)],
             T3T_BLOCK_SIZE);
      idx += T3T_BLOCK_SIZE;
    }
  }

  return idx;
}

/**
 *****************************************************************************
 * @brief  Manage the T3T Update answer to the reader
 *
 * @param[in]  cmdData : pointer to the received command.
 * @param[in]  rspData : pointer to the answer to send.
 *
 * @return Answer size.
 *****************************************************************************
 */
static uint16_t card_emulation_t3t_update(uint8_t *cmdData, uint8_t *rspData) {
  /*
   * Cmd: cmd | NFCID2 | NoS | Service code list | NoB | Block list | Block Data
   * Rsp: rsp | NFCID2 | Status Flag 1 | Status Flag 2
   */
  uint8_t *block;
  uint16_t blocknb[256];
  uint32_t idx = 0;
  uint32_t cnt = 0;
  uint32_t nbmax = 0;

  /* Command response */
  rspData[idx++] = RFAL_NFCF_CMD_WRITE_WITHOUT_ENCRYPTION + 1;

  /* NFCID 2 bytes */
  if (memcmp(gNfcfNfcid, &cmdData[RFAL_NFCF_LENGTH_LEN + RFAL_NFCF_CMD_LEN],
             RFAL_NFCF_NFCID2_LEN) == 0) {
    memcpy(&rspData[idx], gNfcfNfcid, RFAL_NFCF_NFCID2_LEN);
    idx += RFAL_NFCF_NFCID2_LEN;
  } else {
    /* If NFCID2 in command is different, no answer */
    return 0;
  }

  /* Check for command errors */
  if ((cmdData[10] != 1) || (cmdData[11] != 0x09) || (cmdData[13] == 0) ||
      (cmdData[13] > InformationBlock[2])) {
    rspData[idx++] = 0xFF;
    rspData[idx++] = 0xFF;
    return idx;
  } else {
    rspData[idx++] = 0x00;
    rspData[idx++] = 0x00;
  }

  /* Retrieving block to read */
  block = &cmdData[14];
  for (cnt = 0; cnt < cmdData[13]; cnt++) {
    /* Check block list element size */
    if (*block & 0x80) {
      /* 2-byte Block List element */
      blocknb[cnt] = *(block + 1);
      block += 2;
    } else {
      /* 3-byte Block List element */
      blocknb[cnt] = *(block + 2); /* Little Endian Format */
      blocknb[cnt] <<= 8;
      blocknb[cnt] |= *(block + 1);
      block += 3;
    }
    /* Return error if Blocknb > NmaxB */
    nbmax = InformationBlock[3];
    nbmax = (nbmax << 8) | InformationBlock[4];
    if (blocknb[cnt] > nbmax) {
      rspData[idx - 2] = 0xFF;
      rspData[idx - 1] = 0x70;
      return idx;
    }
  }

  for (cnt = 0; cnt < cmdData[13]; cnt++) {
    if (blocknb[cnt] == 0x0000) {
      /* Write information block */
      memcpy(InformationBlock, block, T3T_BLOCK_SIZE);
      block += T3T_BLOCK_SIZE;
    } else {
      /* Read ndef block */
      memcpy(&ndefFile[2 + ((blocknb[cnt] - 1) * T3T_BLOCK_SIZE)], block,
             T3T_BLOCK_SIZE);
      block += T3T_BLOCK_SIZE;
    }
  }

  /* Status flag answer */
  rspData[idx++] = 0x00;
  rspData[idx++] = 0x00;

  return idx;
}

/**
 *****************************************************************************
 * @brief card emulation initialize
 *
 * Initializes the CE mode
 *
 * @param[in]  nfcfNfcid : The NFCID to be used in T3T CE.
 *
 * @return None
 *****************************************************************************
 */
void card_emulation_init(const uint8_t *nfcfNfcid) {
  if (nfcfNfcid != NULL) {
    memcpy(gNfcfNfcid, nfcfNfcid, RFAL_NFCF_NFCID2_LEN);
  }

  memcpy(ndefFile, (uint8_t *)NdefFile, NdefFileLen);

  /* Update AIB Ln with actual NDEF length */
  InformationBlock[12] = NdefFile[0];
  InformationBlock[13] = NdefFile[1];
  uint16_t checksum = 0;
  for (int i = 0; i < 14; i++) {
    checksum += InformationBlock[i];
  }
  InformationBlock[14] = checksum >> 8;
  InformationBlock[15] = checksum & 0xFF;
}

/**
 *****************************************************************************
 * @brief  Demo CE T4T
 *
 * Parses the received command and computes the response to be sent back to
 * the Reader
 *
 * @param[in]  rxData : pointer to the received command.
 * @param[in]  rxDataLen : length of the received command.
 * @param[in]  txBuf : pointer to where the response will be placed.
 * @param[in]  txBufLen : size of txBuf.
 *
 * @return Response size.
 *****************************************************************************
 */
uint16_t card_emulation_t4t(uint8_t *rxData, uint16_t rxDataLen, uint8_t *txBuf,
                            uint16_t txBufLen) {
  if ((txBuf == NULL) || (txBufLen < 2)) {
    // platformErrorHandle();  /* Must ensure appropriate buffer */
    return 0;
  }

  if ((rxData != NULL) && (rxDataLen >= 4)) {
    if (rxData[0] == T4T_CLA_00) {
      switch (rxData[1]) {
        case T4T_INS_SELECT:
          return card_emulation_t4t_select(rxData, txBuf);

        case T4T_INS_READ:
          return card_emulation_t4t_read(rxData, txBuf, txBufLen);

        case T4T_INS_UPDATE:
          return card_emulation_t4t_update(rxData, txBuf);

        default:
          break;
      }
    }
  }

  /* Function not supported ...  */
  txBuf[0] = ((char)0x68);
  txBuf[1] = ((char)0x00);
  return 2;
}

/**
 *****************************************************************************
 * @brief  Demo CE T3T
 *
 * Parses the received command and computes the response to be sent back to
 * the Reader
 *
 * @param[in]  rxData : pointer to the received command.
 * @param[in]  rxDataLen : length of the received command.
 * @param[in]  txBuf : pointer to where the response will be placed.
 * @param[in]  txBufLen : size of txBuf.
 *
 * @return Response size.
 *****************************************************************************
 */
uint16_t card_emulation_t3t(uint8_t *rxData, uint16_t rxDataLen, uint8_t *txBuf,
                            uint16_t txBufLen) {
  if ((txBuf == NULL) || (txBufLen < 11)) {
    // platformErrorHandle();  /* Must ensure appropriate buffer */
    return 0;
  }

  if ((rxData != NULL) && (rxDataLen >= 4)) {
    switch (rxData[1]) {
      case RFAL_NFCF_CMD_READ_WITHOUT_ENCRYPTION:
        return card_emulation_t3t_check(rxData, txBuf, txBufLen);

      case RFAL_NFCF_CMD_WRITE_WITHOUT_ENCRYPTION:
        return card_emulation_t3t_update(rxData, txBuf);

      default:
        break;
    }
  }

  /* Function not supported ...  */
  txBuf[0] = ((char)0xFF);
  txBuf[1] = ((char)0xFF);
  return 2;
}

#endif

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

/************************ (C) COPYRIGHT STMicroelectronics *****END OF FILE****/
