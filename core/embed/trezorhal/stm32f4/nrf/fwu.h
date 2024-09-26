//
//  fwu.h
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

#ifndef __FWU_H__
#define __FWU_H__ 1

#include <trezor_types.h>

struct SFwu;

#define FWU_REQUEST_BUF_SIZE 67
#define FWU_RESPONSE_BUF_SIZE 16

typedef enum {
  FWU_STATUS_UNDEFINED = 0,
  FWU_STATUS_FAILURE = 1,
  FWU_STATUS_COMPLETION = 2,
} EFwuProcessStatus;

typedef enum {
  FWU_RSP_OK = 0,
  FWU_RSP_TOO_SHORT = 1,
  FWU_RSP_START_MARKER_MISSING = 2,
  FWU_RSP_END_MARKER_MISSING = 3,
  FWU_RSP_REQUEST_REFERENCE_INVALID = 4,
  FWU_RSP_ERROR_RESPONSE = 5,
  FWU_RSP_TIMEOUT = 6,
  FWU_RSP_PING_ID_MISMATCH = 7,
  FWU_RSP_RX_OVERFLOW = 8,
  FWU_RSP_INIT_COMMAND_TOO_LARGE = 9,
  FWU_RSP_CHECKSUM_ERROR = 10,
  FWU_RSP_DATA_OBJECT_TOO_LARGE = 11,
  FWU_RSP_RX_INVALID_ESCAPE_SEQ = 12,
} EFwuResponseStatus;

typedef void (*FTxFunction)(struct SFwu *fwu, uint8_t *buf, uint8_t len);

typedef struct SFwu {
  // --- public - define these before calling fwuInit ---
  // .dat
  uint8_t *commandObject;
  uint32_t commandObjectLen;
  // .bin
  uint8_t *dataObject;
  uint32_t dataObjectLen;
  // Sending bytes to the target
  FTxFunction txFunction;
  // Timeout when waiting for a response from the target
  uint32_t responseTimeoutMillisec;
  // --- public - result codes
  // Overall process status code
  EFwuProcessStatus processStatus;
  // Response status code
  EFwuResponseStatus responseStatus;
  // --- private, don't modify ---
  uint32_t privateDataObjectOffset;
  uint32_t privateDataObjectSize;
  uint32_t privateDataObjectMaxSize;
  uint8_t privateProcessState;
  uint8_t privateCommandState;
  uint8_t privateCommandSendOnly;
  uint32_t privateCommandTimeoutRemainingMillisec;
  uint8_t privateRequestBuf[FWU_REQUEST_BUF_SIZE + 1];
  uint8_t privateRequestLen;
  uint8_t privateRequestIx;
  uint8_t privateResponseBuf[FWU_RESPONSE_BUF_SIZE];
  uint8_t privateResponseEscapeCharacter;
  uint8_t privateResponseLen;
  uint32_t privateResponseTimeElapsedMillisec;
  uint8_t privateSendBufSpace;
  uint8_t privateProcessRequest;
  uint8_t privateCommandRequest;
  uint16_t privateMtuSize;
  // sending a large object buffer
  uint8_t *privateObjectBuf;
  uint32_t privateObjectLen;
  uint32_t privateObjectIx;
  uint32_t privateObjectCrc;
} TFwu;

// First function to call to set up the internal state in the FWU structure.
void fwuInit(TFwu *fwu);

// Execute the firmware update.
void fwuExec(TFwu *fwu);

// Call regularly to allow asynchronous processing to continue.
EFwuProcessStatus fwuYield(TFwu *fwu, uint32_t elapsedMillisec);

// Call after data from the target has been received.
void fwuDidReceiveData(TFwu *fwu, uint8_t *bytes, uint8_t len);

// Inform the FWU module that it may send maxLen bytes of data to the target.
void fwuCanSendData(TFwu *fwu, uint8_t maxLen);

// Call to send a chunk of the data object to the target.
void fwuSendChunk(TFwu *fwu, uint8_t *buf, uint32_t len);

// Call to check if a chunk of the data object can be sent to the target.
bool fwuIsReadyForChunk(TFwu *fwu);

#endif  // __FWU_H__
