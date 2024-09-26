//
//  fwu.c
//  nrf52-dfu
//
//  C library for the Nordic firmware update protocol.
//
//  Created by Andreas Schweizer on 30.11.2018.
//  Copyright © 2018-2019 Classy Code GmbH
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.
//

#ifdef KERNEL_MODE

#include <trezor_rtl.h>

#include "fwu.h"

// TODO too big, split in separate files!

typedef enum {
  FWU_PS_IDLE = 0,
  FWU_PS_PING = 10,
  FWU_PS_RCPT_NOTIF = 20,
  FWU_PS_MTU = 30,
  FWU_PS_OBJ1_SELECT = 40,
  FWU_PS_OBJ1_CREATE = 50,
  FWU_PS_OBJ1_WRITE = 60,
  FWU_PS_OBJ1_CRC_GET = 70,
  FWU_PS_OBJ1_EXECUTE = 80,
  FWU_PS_OBJ2_SELECT = 90,
  FWU_PS_OBJ2_WAIT_FOR_CHUNK = 91,
  FWU_PS_OBJ2_CREATE = 100,
  FWU_PS_OBJ2_WRITE = 110,
  FWU_PS_OBJ2_CRC_GET = 120,
  FWU_PS_OBJ2_EXECUTE = 130,
  FWU_PS_FAIL = 254,
  FWU_PS_DONE = 255,
} EFwuProcessState;

// Process requests, triggering process state transitions.
typedef enum {
  FWU_PR_NONE = 0,
  FWU_PR_START = 1,
  FWU_PR_RECEIVED_RESPONSE,
  FWU_PR_REQUEST_FAILED,
  FWU_PR_REQUEST_SENT,
} EFwuProcessRequest;

typedef enum {
  FWU_CS_IDLE = 0,
  FWU_CS_SEND = 1,     // sending data from the private request buffer
  FWU_CS_RECEIVE = 2,  // receiving data into the private response buffer
  FWU_CS_FAIL = 3,
  FWU_CS_DONE = 4,
} EFwuCommandState;

// Command requests, triggering command state transitions.
typedef enum {
  FWU_CR_NONE = 0,
  FWU_CR_SEND = 1,
  FWU_CR_SENDONLY = 2,
  FWU_CR_EOM_RECEIVED = 3,
  FWU_CR_RX_OVERFLOW = 4,
  FWU_CR_INVALID_ESCAPE_SEQ,
} EFwuCommandRequest;

#define FWU_EOM 0xC0
#define FWU_RESPONSE_START 0x60
#define FWU_RESPONSE_SUCCESS 0x01

// PING 09 01 C0 -> 60 09 01 01 C0
static uint8_t sPingRequest[] = {0x09, 0x01};
static uint8_t sPingRequestLen = 2;

// SET RECEIPT 02 00 00 C0 -> 60 02 01 C0
static uint8_t sSetReceiptRequest[] = {0x02, 0x00, 0x00};
static uint8_t sSetReceiptRequestLen = 3;

// Get the preferred MTU size on the request.
// GET MTU 07 -> 60 07 01 83 00 C0
static uint8_t sGetMtuRequest[] = {0x07};
static uint8_t sGetMtuRequestLen = 1;

// Triggers the last transferred object of the specified type to be selected
//  and queries information (max size, cur offset, cur CRC) about the object.
//  If there's no object of the specified type, the object type is still
//  selected, CRC and offset are 0 in this case.
// SELECT OBJECT 06 01 C0 -> 60 06 01 00 01 00 00 00 00 00 00 00 00 00 00 C0
static uint8_t sSelectObjectRequest[] = {0x06, 0x01};
static uint8_t sSelectObjectRequestLen = 2;

// Creating a command or data object; the target reserves the space, resets the
//  progress since the last Execute command and selects the new object.)
// CREATE OBJECT 01 01 87 00 00 00 C0 -> 60 01 01 C0
static uint8_t sCreateObjectRequest[] = {0x01, 0x01, 0x87, 0x00, 0x00, 0x00};
static uint8_t sCreateObjectRequestLen = 6;

// CRC GET 03 C0 -> 60 03 01 87 00 00 00 38 f4 97 72 C0
static uint8_t sGetCrcRequest[] = {0x03};
static uint8_t sGetCrcRequestLen = 1;

// Execute an object after it has been fully transmitted.
// EXECUTE OBJECT 04 C0 -> 60 04 01 C0
static uint8_t sExecuteObjectRequest[] = {0x04};
static uint8_t sExecuteObjectRequestLen = 1;

static void fwuYieldProcessFsm(TFwu *fwu, uint32_t elapsedMillisec);
static void fwuYieldCommandFsm(TFwu *fwu, uint32_t elapsedMillisec);

static EFwuResponseStatus fwuTestReceivedPacketValid(TFwu *fwu);

// Don't send more than FWU_REQUEST_BUF_SIZE bytes.
// Don't include the EOM.
static void fwuPrepareSendBuffer(TFwu *fwu, uint8_t *data, uint8_t len);

static void fwuPrepareLargeObjectSendBuffer(TFwu *fwu, uint8_t requestCode);

// static void fwuDebugPrintStatus(TFwu *fwu, char *msg);

static void updateCrc(TFwu *fwu, uint8_t b);
static void fwuSignalFailure(TFwu *fwu, EFwuResponseStatus reason);
static inline uint16_t fwuLittleEndianToHost16(uint8_t *bytes);
static inline uint32_t fwuLittleEndianToHost32(uint8_t *bytes);
static inline void fwuHostToLittleEndian32(uint32_t v, uint8_t *bytes);

// First function to call to set up the internal state in the FWU structure.
void fwuInit(TFwu *fwu) {
  fwu->privateProcessState = FWU_PS_IDLE;
  fwu->privateProcessRequest = FWU_PR_NONE;
  fwu->privateCommandState = FWU_CS_IDLE;

  fwu->processStatus = FWU_STATUS_UNDEFINED;
  fwu->responseStatus = FWU_RSP_OK;
}

// Execute the firmware update.
void fwuExec(TFwu *fwu) {
  // Start with sending a PING command to the target to see if it's there...
  fwu->privateProcessRequest = FWU_PR_START;
}

// Call regularly to allow asynchronous processing to continue.
EFwuProcessStatus fwuYield(TFwu *fwu, uint32_t elapsedMillisec) {
  // Nothing to do if processing has failed or successfully completed...
  if (fwu->processStatus == FWU_STATUS_FAILURE ||
      fwu->privateProcessState == FWU_PS_FAIL) {
    return FWU_STATUS_FAILURE;
  } else if (fwu->processStatus == FWU_STATUS_COMPLETION ||
             fwu->privateProcessState == FWU_PS_DONE) {
    return FWU_STATUS_COMPLETION;
  }

  // Processing is ongoing, yield to FSMs.
  fwuYieldCommandFsm(fwu, elapsedMillisec);
  fwuYieldProcessFsm(fwu, elapsedMillisec);

  return fwu->processStatus;
}

// Call after data from the target has been received.
void fwuDidReceiveData(TFwu *fwu, uint8_t *bytes, uint8_t len) {
  while (len > 0) {
    if (fwu->privateResponseLen == FWU_RESPONSE_BUF_SIZE) {
      fwu->privateCommandRequest = FWU_CR_RX_OVERFLOW;
      return;
    }
    uint8_t c = *bytes++;
    if (c == FWU_EOM) {
      fwu->privateCommandRequest = FWU_CR_EOM_RECEIVED;
    }

    if (c == 0xDB) {
      fwu->privateResponseEscapeCharacter = 1;
    } else {
      if (fwu->privateResponseEscapeCharacter) {
        fwu->privateResponseEscapeCharacter = 0;
        if (c == 0xDC) {
          c = 0xC0;
        } else if (c == 0xDD) {
          c = 0xDB;
        } else {
          fwu->privateCommandRequest = FWU_CR_INVALID_ESCAPE_SEQ;
          return;
        }
      }
      fwu->privateResponseBuf[fwu->privateResponseLen++] = c;
    }
    len--;
  }
}

// Inform the FWU module that it may send maxLen bytes of data to the target.
void fwuCanSendData(TFwu *fwu, uint8_t maxLen) {
  fwu->privateSendBufSpace = maxLen;
}

void fwuSendChunk(TFwu *fwu, uint8_t *buf, uint32_t len) {
  if (fwu->privateProcessState == FWU_PS_OBJ2_WAIT_FOR_CHUNK &&
      fwu->privateDataObjectSize == len) {
    fwu->dataObject = buf;
    fwu->privateProcessState = FWU_PS_OBJ2_CREATE;
  }
}

bool fwuIsReadyForChunk(TFwu *fwu) {
  return fwu->privateProcessState == FWU_PS_OBJ2_WAIT_FOR_CHUNK;
}

static void fwuYieldProcessFsm(TFwu *fwu, uint32_t elapsedMillisec) {
  uint8_t tmpPrivateProcessRequest = fwu->privateProcessRequest;
  fwu->privateProcessRequest = FWU_PR_NONE;

  // No processing in final states
  if (fwu->privateProcessState == FWU_PS_DONE ||
      fwu->privateProcessState == FWU_PS_FAIL) {
    return;
  }

  // Failure handling
  if (tmpPrivateProcessRequest == FWU_PR_REQUEST_FAILED) {
    fwu->privateProcessState = FWU_PS_FAIL;
    fwu->processStatus = FWU_STATUS_FAILURE;
    return;
  }

  // Executing the firmware update process.
  switch (fwu->privateProcessState) {
    case FWU_PS_IDLE:
      if (tmpPrivateProcessRequest == FWU_PR_START) {
        // Send a PING and switch to the PING state to wait for the response.
        fwuPrepareSendBuffer(fwu, sPingRequest, sPingRequestLen);
        fwu->privateProcessState = FWU_PS_PING;
      }
      break;

      // PING: Check if the nRF52 DFU code is listening
    case FWU_PS_PING:
      // Wait for the PING response, then verify it.
      if (tmpPrivateProcessRequest == FWU_PR_RECEIVED_RESPONSE) {
        // ID match?
        if (fwu->privateRequestBuf[1] == fwu->privateResponseBuf[3]) {
          // Send a SET_RECEIPT and switch to the corresponding state to wait
          // for the response.
          fwuPrepareSendBuffer(fwu, sSetReceiptRequest, sSetReceiptRequestLen);
          fwu->privateProcessState = FWU_PS_RCPT_NOTIF;
        } else {
          fwuSignalFailure(fwu, FWU_RSP_PING_ID_MISMATCH);
        }
      }
      break;

      // RCPT_NOTIF: Define Receipt settings
    case FWU_PS_RCPT_NOTIF:
      // Wait for the SET_RECEIPT response.
      if (tmpPrivateProcessRequest == FWU_PR_RECEIVED_RESPONSE) {
        // Send a SET_RECEIPT and switch to the corresponding state to wait for
        // the response.
        fwuPrepareSendBuffer(fwu, sGetMtuRequest, sGetMtuRequestLen);
        fwu->privateProcessState = FWU_PS_MTU;
      }
      break;

      // FWU_PS_MTU: Get maximum transmission unit size
    case FWU_PS_MTU:
      if (tmpPrivateProcessRequest == FWU_PR_RECEIVED_RESPONSE) {
        fwu->privateMtuSize =
            fwuLittleEndianToHost16(&fwu->privateResponseBuf[3]);
        // Send a SET_RECEIPT and switch to the corresponding state to wait for
        // the response.
        sSelectObjectRequest[1] = 0x01;  // select object 1 (command object)
        fwuPrepareSendBuffer(fwu, sSelectObjectRequest,
                             sSelectObjectRequestLen);
        fwu->privateProcessState = FWU_PS_OBJ1_SELECT;
      }
      break;

      // FWU_PS_OBJ1_SELECT: Select the INIT command object
    case FWU_PS_OBJ1_SELECT:
      if (tmpPrivateProcessRequest == FWU_PR_RECEIVED_RESPONSE) {
        uint32_t maxSize = fwuLittleEndianToHost32(&fwu->privateResponseBuf[3]);
        if (maxSize < fwu->commandObjectLen) {
          fwuSignalFailure(fwu, FWU_RSP_INIT_COMMAND_TOO_LARGE);
        } else {
          sCreateObjectRequest[1] = 0x01;  // create type 1 object (COMMAND)
          fwuHostToLittleEndian32(fwu->commandObjectLen,
                                  &sCreateObjectRequest[2]);
          fwuPrepareSendBuffer(fwu, sCreateObjectRequest,
                               sCreateObjectRequestLen);
          fwu->privateProcessState = FWU_PS_OBJ1_CREATE;
        }
      }
      break;

      // FWU_PS_OBJ1_CREATE: Create the INIT command object
    case FWU_PS_OBJ1_CREATE:
      if (tmpPrivateProcessRequest == FWU_PR_RECEIVED_RESPONSE) {
        fwu->privateProcessState = FWU_PS_OBJ1_WRITE;
        fwu->privateObjectBuf = fwu->commandObject;
        fwu->privateObjectLen = fwu->commandObjectLen;
        fwu->privateObjectIx = 0;
        fwu->privateObjectCrc = 0xffffffff;
        fwuPrepareLargeObjectSendBuffer(fwu, 0x08);
      }
      break;

      // FWU_PS_OBJ1_WRITE: Write the INIT command object
    case FWU_PS_OBJ1_WRITE:
      if (tmpPrivateProcessRequest == FWU_PR_REQUEST_SENT) {
        // more to send?
        if (fwu->privateObjectIx == fwu->privateObjectLen) {
          // no - request the CRC of the written data...
          fwuPrepareSendBuffer(fwu, sGetCrcRequest, sGetCrcRequestLen);
          fwu->privateProcessState = FWU_PS_OBJ1_CRC_GET;
        } else {
          fwuPrepareLargeObjectSendBuffer(fwu, 0x08);
        }
      }
      break;

      // FWU_PS_OBJ1_CRC_GET: Checksum verification
    case FWU_PS_OBJ1_CRC_GET:
      if (tmpPrivateProcessRequest == FWU_PR_RECEIVED_RESPONSE) {
        // uint32_t actualLen =
        // fwuLittleEndianToHost32(&fwu->privateResponseBuf[3]);
        uint32_t actualCks =
            fwuLittleEndianToHost32(&fwu->privateResponseBuf[7]);
        if (actualCks == ~fwu->privateObjectCrc) {
          // Checksum is OK; execute the command!
          fwuPrepareSendBuffer(fwu, sExecuteObjectRequest,
                               sExecuteObjectRequestLen);
          fwu->privateProcessState = FWU_PS_OBJ1_EXECUTE;
        } else {
          fwuSignalFailure(fwu, FWU_RSP_CHECKSUM_ERROR);
        }
      }
      break;

    case FWU_PS_OBJ1_EXECUTE:
      if (tmpPrivateProcessRequest == FWU_PR_RECEIVED_RESPONSE) {
        sSelectObjectRequest[1] = 0x02;    // select object 2 (DATA object)
        fwu->privateDataObjectOffset = 0;  // from the beginning
        fwuPrepareSendBuffer(fwu, sSelectObjectRequest,
                             sSelectObjectRequestLen);
        fwu->privateProcessState = FWU_PS_OBJ2_SELECT;
      }
      break;

      // FWU_PS_OBJ2_SELECT: Select the DATA object
    case FWU_PS_OBJ2_SELECT:
      if (tmpPrivateProcessRequest == FWU_PR_RECEIVED_RESPONSE) {
        fwu->privateDataObjectMaxSize =
            fwuLittleEndianToHost32(&fwu->privateResponseBuf[3]);
        fwu->privateObjectCrc =
            0xffffffff;  // do it here because it's global for the entire blob
        // We'll create and execute multiple data objects, so it's ok if the
        // actual size is greater than max size.
        fwu->privateDataObjectSize =
            (fwu->dataObjectLen -
             fwu->privateDataObjectOffset);  // nof bytes remaining
        if (fwu->privateDataObjectSize > fwu->privateDataObjectMaxSize) {
          fwu->privateDataObjectSize = fwu->privateDataObjectMaxSize;
        }
        sCreateObjectRequest[1] = 0x02;  // create type 2 object (COMMAND)
        fwuHostToLittleEndian32(fwu->privateDataObjectSize,
                                &sCreateObjectRequest[2]);
        fwuPrepareSendBuffer(fwu, sCreateObjectRequest,
                             sCreateObjectRequestLen);
        fwu->privateProcessState = FWU_PS_OBJ2_WAIT_FOR_CHUNK;
      }
      break;
    case FWU_PS_OBJ2_WAIT_FOR_CHUNK:
      break;
      // FWU_PS_OBJ2_CREATE: Create the DATA object
    case FWU_PS_OBJ2_CREATE:
      if (tmpPrivateProcessRequest == FWU_PR_RECEIVED_RESPONSE) {
        fwu->privateProcessState = FWU_PS_OBJ2_WRITE;
        fwu->privateObjectBuf = fwu->dataObject;
        fwu->privateObjectLen = fwu->privateDataObjectSize;
        fwu->privateObjectIx = 0;
        fwuPrepareLargeObjectSendBuffer(fwu, 0x08);
      }
      break;

      // FWU_PS_OBJ2_WRITE: Write the DATA object
    case FWU_PS_OBJ2_WRITE:
      if (tmpPrivateProcessRequest == FWU_PR_REQUEST_SENT) {
        // more to send?
        if (fwu->privateObjectIx == fwu->privateObjectLen) {
          // no - request the CRC of the written data...
          fwuPrepareSendBuffer(fwu, sGetCrcRequest, sGetCrcRequestLen);
          fwu->privateProcessState = FWU_PS_OBJ2_CRC_GET;
        } else {
          fwuPrepareLargeObjectSendBuffer(fwu, 0x08);
        }
      }
      break;

      // FWU_PS_OBJ2_CRC_GET: Checksum verification
    case FWU_PS_OBJ2_CRC_GET:
      if (tmpPrivateProcessRequest == FWU_PR_RECEIVED_RESPONSE) {
        // uint32_t actualLen =
        // fwuLittleEndianToHost32(&fwu->privateResponseBuf[3]);
        uint32_t actualCks =
            fwuLittleEndianToHost32(&fwu->privateResponseBuf[7]);
        if (actualCks == ~fwu->privateObjectCrc) {
          // Checksum is OK; execute the command!
          fwuPrepareSendBuffer(fwu, sExecuteObjectRequest,
                               sExecuteObjectRequestLen);
          fwu->privateProcessState = FWU_PS_OBJ2_EXECUTE;

        } else {
          fwuSignalFailure(fwu, FWU_RSP_CHECKSUM_ERROR);
        }
      }
      break;

    case FWU_PS_OBJ2_EXECUTE:
      if (tmpPrivateProcessRequest == FWU_PR_RECEIVED_RESPONSE) {
        fwu->privateDataObjectOffset += fwu->privateDataObjectSize;
        if (fwu->privateDataObjectOffset == fwu->dataObjectLen) {
          fwu->privateProcessState = FWU_PS_DONE;
          fwu->processStatus = FWU_STATUS_COMPLETION;

        } else {
          // We'll create and execute multiple data objects, so it's ok if the
          // actual size is greater than max size.
          fwu->privateDataObjectSize =
              (fwu->dataObjectLen -
               fwu->privateDataObjectOffset);  // nof bytes remaining
          if (fwu->privateDataObjectSize > fwu->privateDataObjectMaxSize) {
            fwu->privateDataObjectSize = fwu->privateDataObjectMaxSize;
          }
          sCreateObjectRequest[1] = 0x02;  // create type 2 object (COMMAND)
          fwuHostToLittleEndian32(fwu->privateDataObjectSize,
                                  &sCreateObjectRequest[2]);
          fwuPrepareSendBuffer(fwu, sCreateObjectRequest,
                               sCreateObjectRequestLen);
          fwu->privateProcessState = FWU_PS_OBJ2_WAIT_FOR_CHUNK;
        }
      }
      break;

    default:
      fwu->privateProcessState = FWU_PS_FAIL;
      break;
  }
}

static void fwuYieldCommandFsm(TFwu *fwu, uint32_t elapsedMillisec) {
  uint8_t toSend;

  // Automatically return from final states to IDLE.
  if (fwu->privateCommandState == FWU_CS_DONE ||
      fwu->privateCommandState == FWU_CS_FAIL) {
    fwu->privateCommandState = FWU_CS_IDLE;
  }

  // Timeout?
  if (fwu->privateCommandState != FWU_CS_IDLE) {
    if (fwu->privateCommandTimeoutRemainingMillisec < elapsedMillisec) {
      fwu->privateCommandTimeoutRemainingMillisec = 0;
    } else {
      fwu->privateCommandTimeoutRemainingMillisec -= elapsedMillisec;
    }
    if (fwu->privateCommandTimeoutRemainingMillisec == 0) {
      fwuSignalFailure(fwu, FWU_RSP_TIMEOUT);
      return;
    }
  }

  // Catch errors
  if (fwu->privateCommandRequest == FWU_CR_RX_OVERFLOW) {
    fwuSignalFailure(fwu, FWU_RSP_RX_OVERFLOW);
    return;
  }
  if (fwu->privateCommandRequest == FWU_CR_INVALID_ESCAPE_SEQ) {
    fwuSignalFailure(fwu, FWU_RSP_RX_INVALID_ESCAPE_SEQ);
    return;
  }

  switch (fwu->privateCommandState) {
    case FWU_CS_IDLE:
      // Ready and waiting for a transmission request.
      if (fwu->privateCommandRequest == FWU_CR_SEND ||
          fwu->privateCommandRequest == FWU_CR_SENDONLY) {
        fwu->privateCommandSendOnly =
            fwu->privateCommandRequest == FWU_CR_SENDONLY ? 1 : 0;
        fwu->privateCommandRequest = FWU_CR_NONE;
        fwu->privateCommandState = FWU_CS_SEND;
        fwu->privateCommandTimeoutRemainingMillisec =
            fwu->responseTimeoutMillisec;
      }
      break;
    case FWU_CS_SEND:
      // Continue sending data until the entire request has been sent.
      toSend = fwu->privateRequestLen - fwu->privateRequestIx;
      if (toSend == 0) {
        if (fwu->privateCommandSendOnly) {
          // This was a fire-and-forget request; we don't expect a response.
          fwu->privateProcessRequest = FWU_PR_REQUEST_SENT;
          fwu->privateCommandState = FWU_CS_DONE;
        } else {
          // The request has been sent; wait for response.
          fwu->privateCommandState = FWU_CS_RECEIVE;
        }
      } else if (fwu->privateSendBufSpace > 0) {
        uint8_t n = fwu->privateSendBufSpace;
        if (n > toSend) {
          n = toSend;
        }
        fwu->txFunction(fwu, &fwu->privateRequestBuf[fwu->privateRequestIx], n);
        fwu->privateRequestIx += n;
      }
      break;
    case FWU_CS_RECEIVE:
      // Continue receiving data until the end-of-message marker has been
      // received.
      if (fwu->privateCommandRequest == FWU_CR_EOM_RECEIVED) {
        fwu->privateCommandRequest = FWU_CR_NONE;
        EFwuResponseStatus responseStatus = fwuTestReceivedPacketValid(fwu);
        if (responseStatus == FWU_RSP_OK) {
          // Inform the process state machine that command reception has
          // completed.
          fwu->privateProcessRequest = FWU_PR_RECEIVED_RESPONSE;
          fwu->privateCommandState = FWU_CS_DONE;
        } else {
          fwu->responseStatus = responseStatus;
          fwu->privateCommandState = FWU_CS_FAIL;
        }
      }
      break;
    default:
      fwu->privateCommandState = FWU_CS_FAIL;
      break;
  }
}

static EFwuResponseStatus fwuTestReceivedPacketValid(TFwu *fwu) {
  // 60 <cmd> <ok> C0
  if (fwu->privateResponseLen < 4) {
    return FWU_RSP_TOO_SHORT;
  }
  if (fwu->privateResponseBuf[0] != FWU_RESPONSE_START) {
    return FWU_RSP_START_MARKER_MISSING;
  }
  if (fwu->privateResponseBuf[1] != fwu->privateRequestBuf[0]) {
    return FWU_RSP_REQUEST_REFERENCE_INVALID;
  }
  if (fwu->privateResponseBuf[2] != FWU_RESPONSE_SUCCESS) {
    return FWU_RSP_ERROR_RESPONSE;
  }
  if (fwu->privateResponseBuf[fwu->privateResponseLen - 1] != FWU_EOM) {
    return FWU_RSP_END_MARKER_MISSING;
  }
  return FWU_RSP_OK;
}

static void fwuPrepareLargeObjectSendBuffer(TFwu *fwu, uint8_t requestCode) {
  uint16_t bytesTodo = fwu->privateObjectLen - fwu->privateObjectIx;
  uint16_t bufSpace = FWU_REQUEST_BUF_SIZE - 2;

  uint16_t i;
  uint8_t *p = &fwu->privateRequestBuf[0];

  *p++ = requestCode;
  fwu->privateRequestLen = 2;  // including requestCode and FWU_EOM
  fwu->privateRequestIx = 0;

  if (bytesTodo > 32) {
    bytesTodo = 32;
  }

  for (i = 0; i < bytesTodo && bufSpace >= 2; i++) {
    uint8_t b = fwu->privateObjectBuf[fwu->privateObjectIx];
    // SLIP escape characters: C0->DBDC, DB->DBDD
    if (b == 0xC0 || b == 0xDB) {
      *p++ = 0xDB;
      *p++ = (b == 0xC0) ? 0xDC : 0xDD;
      fwu->privateRequestLen += 2;
      bufSpace -= 2;
    } else {
      *p++ = b;
      fwu->privateRequestLen++;
      bufSpace--;
    }
    updateCrc(fwu, b);
    fwu->privateObjectIx++;
  }

  *p = FWU_EOM;
  fwu->privateCommandRequest = FWU_CR_SENDONLY;
}

static void fwuPrepareSendBuffer(TFwu *fwu, uint8_t *data, uint8_t len) {
  // TODO assert privateCommandState == FWU_CS_IDLE | _DONE | _FAIL
  // TODO assert len <= FWU_REQUEST_BUF_SIZE

  uint8_t i;
  uint8_t *p = &fwu->privateRequestBuf[0];

  fwu->privateRequestIx = 0;
  fwu->privateRequestLen = len + 1;
  fwu->privateResponseLen = 0;

  // Copy the data into our internal buffer.
  for (i = 0; i < len; i++) {
    *p++ = *data++;
  }

  // Add the end-of-message marker.
  *p = FWU_EOM;

  // Ready to send!
  fwu->privateCommandRequest = FWU_CR_SEND;
}

static void updateCrc(TFwu *fwu, uint8_t b) {
  uint8_t i;
  uint32_t crc = fwu->privateObjectCrc;
  crc ^= b;
  for (i = 0; i < 8; i++) {
    uint32_t m = (crc & 1) ? 0xffffffff : 0;
    crc = (crc >> 1) ^ (0xedb88320u & m);
  }
  fwu->privateObjectCrc = crc;
}

static void fwuSignalFailure(TFwu *fwu, EFwuResponseStatus reason) {
  fwu->responseStatus = reason;
  fwu->privateCommandState = FWU_CS_FAIL;
  // Signal failure to process state machine
  fwu->privateProcessRequest = FWU_PR_REQUEST_FAILED;
}

static inline uint16_t fwuLittleEndianToHost16(uint8_t *bytes) {
  return bytes[0] | ((uint16_t)bytes[1] << 8);
}

static inline uint32_t fwuLittleEndianToHost32(uint8_t *bytes) {
  return bytes[0] | ((uint16_t)bytes[1] << 8) | ((uint32_t)bytes[2] << 16) |
         ((uint32_t)bytes[3] << 24);
}

static inline void fwuHostToLittleEndian32(uint32_t v, uint8_t *bytes) {
  uint8_t i;
  for (i = 0; i < 4; i++) {
    *bytes++ = v & 0xff;
    v = v >> 8;
  }
}

#endif
