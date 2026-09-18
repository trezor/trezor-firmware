// SPDX-License-Identifier: Apache-2.0 or CC0-1.0
#ifndef KEM_H
#define KEM_H

#include <stdint.h>
#include "params.h"

#define CRYPTO_SECRETKEYBYTES  MLKEM_SECRETKEYBYTES
#define CRYPTO_PUBLICKEYBYTES  MLKEM_PUBLICKEYBYTES
#define CRYPTO_CIPHERTEXTBYTES MLKEM_CIPHERTEXTBYTES
#define CRYPTO_BYTES           MLKEM_SSBYTES

#if   (MLKEM_K == 2)
#define CRYPTO_ALGNAME "Mlkem512"
#elif (MLKEM_K == 3)
#define CRYPTO_ALGNAME "Mlkem768"
#elif (MLKEM_K == 4)
#define CRYPTO_ALGNAME "Mlkem1024"
#endif

#define crypto_kem_keypair_derand MLKEM_NAMESPACE(keypair_derand)
int crypto_kem_keypair_derand(uint8_t *pk, uint8_t *sk, const uint8_t *coins);

#define crypto_kem_keypair MLKEM_NAMESPACE(keypair)
int crypto_kem_keypair(uint8_t *pk, uint8_t *sk);

#define crypto_kem_enc_derand MLKEM_NAMESPACE(enc_derand)
int crypto_kem_enc_derand(uint8_t *ct, uint8_t *ss, const uint8_t *pk, const uint8_t *coins);

#define crypto_kem_enc MLKEM_NAMESPACE(enc)
int crypto_kem_enc(uint8_t *ct, uint8_t *ss, const uint8_t *pk);

#define crypto_kem_dec MLKEM_NAMESPACE(dec)
int crypto_kem_dec(uint8_t *ss, const uint8_t *ct, const uint8_t *sk);

#endif
