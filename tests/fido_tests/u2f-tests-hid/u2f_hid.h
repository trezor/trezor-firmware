// Copyright 2014 Google Inc. All rights reserved.
//
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file or at
// https://developers.google.com/open-source/licenses/bsd

#ifndef __U2F_HID_H_INCLUDED__
#define __U2F_HID_H_INCLUDED__

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifndef __NO_PRAGMA_PACK
#pragma pack(push, 1)
#endif

// HID frame definition
typedef struct {
  uint32_t cid;
  union {
    uint8_t type;
    struct {
      uint8_t cmd;
      uint8_t bcnth;
      uint8_t bcntl;
      uint8_t data[64 - 7];
    } init;
    struct {
      uint8_t seq;
      uint8_t data[64 - 5];
    } cont;
  };
} U2FHID_FRAME;

// HID frame accessors
#define TYPE_MASK  0x80
#define TYPE_INIT  0x80
#define TYPE_CONT  0x00

#define FRAME_TYPE(x)  ((x).type & TYPE_MASK)
#define FRAME_SEQ(x)  ((x).cont.seq & ~TYPE_MASK)
#define FRAME_CMD(x)  ((x).init.cmd & ~TYPE_MASK)
#define MSG_LEN(x)  ((x).init.bcnth * 256u + (x).init.bcntl)

// Commands
#define U2FHID_PING  (TYPE_INIT | 1)
#define U2FHID_MSG  (TYPE_INIT | 3)
#define U2FHID_LOCK  (TYPE_INIT | 4)
#define U2FHID_INIT  (TYPE_INIT | 6)
#define U2FHID_WINK  (TYPE_INIT | 8)
#define U2FHID_SYNC  (TYPE_INIT | 0x3c)
#define U2FHID_ERROR  (TYPE_INIT | 0x3f)

// Errors
#define ERR_NONE  0
#define ERR_INVALID_CMD  1
#define ERR_INVALID_PAR  2
#define ERR_INVALID_LEN  3
#define ERR_INVALID_SEQ  4
#define ERR_MSG_TIMEOUT  5
#define ERR_CHANNEL_BUSY  6
#define ERR_LOCK_REQUIRED  10
#define ERR_INVALID_CID  11
#define ERR_OTHER  127

// Init command parameters
#define CID_BROADCAST  -1
#define INIT_NONCE_SIZE  8

typedef struct {
  uint8_t nonce[INIT_NONCE_SIZE];
  uint32_t cid;
  uint8_t versionInterface;
  uint8_t versionMajor;
  uint8_t versionMinor;
  uint8_t versionBuild;
  uint8_t capFlags;
} U2FHID_INIT_RESP;

#define U2FHID_IF_VERSION  2

#define CAPFLAG_WINK  0x01
#define CAPFLAG_LOCK  0x02

#ifndef __NO_PRAGMA_PACK
#pragma pack(pop)
#endif

#ifdef __cplusplus
}
#endif

#endif  // __U2F_HID_H_INCLUDED__
