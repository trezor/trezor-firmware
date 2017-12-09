// Copyright (c) 2014-2017, The Monero Project
// 
// All rights reserved.
// 
// Redistribution and use in source and binary forms, with or without modification, are
// permitted provided that the following conditions are met:
// 
// 1. Redistributions of source code must retain the above copyright notice, this list of
//    conditions and the following disclaimer.
// 
// 2. Redistributions in binary form must reproduce the above copyright notice, this list
//    of conditions and the following disclaimer in the documentation and/or other
//    materials provided with the distribution.
// 
// 3. Neither the name of the copyright holder nor the names of its contributors may be
//    used to endorse or promote products derived from this software without specific
//    prior written permission.
// 
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
// EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
// MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
// THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
// PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
// INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
// STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
// THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
// 
// Parts of this file are originally copyright (c) 2012-2013 The Cryptonote developers

#ifndef __BLAKE256_H__
#define __BLAKE256_H__

#include <stdint.h>

#define BLAKE224_DIGEST_LENGTH 28
#define BLAKE256_DIGEST_LENGTH 32

typedef struct {
  uint32_t h[8], s[4], t[2];
  int buflen, nullt;
  uint8_t buf[64];
} BLAKE256_CTX;

typedef struct {
  BLAKE256_CTX inner;
  BLAKE256_CTX outer;
} HMAC_BLAKE256_CTX;

void blake256_Init(BLAKE256_CTX *);
void blake224_Init(BLAKE256_CTX *);

void blake256_Update(BLAKE256_CTX *, const uint8_t *, size_t);
void blake224_Update(BLAKE256_CTX *, const uint8_t *, size_t);

void blake256_Final(BLAKE256_CTX *, uint8_t *);
void blake224_Final(BLAKE256_CTX *, uint8_t *);

void blake256(const uint8_t *, size_t, uint8_t *);
void blake224(const uint8_t *, size_t, uint8_t *);

/* HMAC functions: */

void hmac_blake256_Init(HMAC_BLAKE256_CTX *, const uint8_t *, size_t);
void hmac_blake224_Init(HMAC_BLAKE256_CTX *, const uint8_t *, size_t);

void hmac_blake256_Update(HMAC_BLAKE256_CTX *, const uint8_t *, size_t);
void hmac_blake224_Update(HMAC_BLAKE256_CTX *, const uint8_t *, size_t);

void hmac_blake256_Final(HMAC_BLAKE256_CTX *, uint8_t *);
void hmac_blake224_Final(HMAC_BLAKE256_CTX *, uint8_t *);

void hmac_blake256(const uint8_t *, size_t, const uint8_t *, size_t, uint8_t *);
void hmac_blake224(const uint8_t *, size_t, const uint8_t *, size_t, uint8_t *);

#endif /* __BLAKE256_H__ */
