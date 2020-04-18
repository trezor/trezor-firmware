// Copyright 2014 Google Inc. All rights reserved.
//
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file or at
// https://developers.google.com/open-source/licenses/bsd

#ifndef __U2F_H_INCLUDED__
#define __U2F_H_INCLUDED__

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifndef __NO_PRAGMA_PACK
#pragma pack(push, 1)
#endif

// General constants

#define P256_SCALAR_SIZE  32  // nistp256 in bytes
#define P256_POINT_SIZE  ((P256_SCALAR_SIZE * 2) + 1)

#define MAX_ECDSA_SIG_SIZE  72  // asn1 DER format
#define MAX_KH_SIZE  128  // key handle
#define MAX_CERT_SIZE  2048  // attestation certificate

#define U2F_APPID_SIZE  32
#define U2F_NONCE_SIZE  32

#define UNCOMPRESSED_POINT 0x04

typedef struct {
  uint8_t format;
  uint8_t x[P256_SCALAR_SIZE];
  uint8_t y[P256_SCALAR_SIZE];
} P256_POINT;

// U2Fv2 instructions

#define U2F_INS_REGISTER  0x01
#define U2F_INS_AUTHENTICATE  0x02
#define U2F_INS_VERSION  0x03

// U2F_REGISTER instruction defines

#define U2F_REGISTER_ID  0x05  // magic constant
#define U2F_REGISTER_HASH_ID  0x00  // magic constant

typedef struct {
  uint8_t nonce[U2F_NONCE_SIZE];
  uint8_t appId[U2F_APPID_SIZE];
} U2F_REGISTER_REQ;

typedef struct {
  uint8_t registerId;
  P256_POINT pubKey;
  uint8_t keyHandleLen;
  uint8_t keyHandleCertSig[
      MAX_KH_SIZE +
      MAX_CERT_SIZE +
      MAX_ECDSA_SIG_SIZE];
} U2F_REGISTER_RESP;

// U2F_AUTHENTICATE instruction defines

// Authentication parameter byte
#define U2F_AUTH_ENFORCE  0x03  // Require user presence
#define U2F_AUTH_CHECK_ONLY  0x07  // Test but do not consume

typedef struct {
  uint8_t nonce[U2F_NONCE_SIZE];
  uint8_t appId[U2F_APPID_SIZE];
  uint8_t keyHandleLen;
  uint8_t keyHandle[MAX_KH_SIZE];
} U2F_AUTHENTICATE_REQ;

// Flags values
#define U2F_TOUCHED  0x01
#define U2F_ALTERNATE_INTERFACE  0x02

typedef struct {
  uint8_t flags;
  uint32_t ctr;
  uint8_t sig[MAX_ECDSA_SIG_SIZE];
} U2F_AUTHENTICATE_RESP;

#ifndef __NO_PRAGMA_PACK
#pragma pack(pop)
#endif

#ifdef __cplusplus
}
#endif

#endif  // __U2F_H_INCLUDED__
