// SPDX-License-Identifier: Apache-2.0 or CC0-1.0
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "params.h"
#include "kem.h"
#include "indcpa.h"
#include "verify.h"
#include "symmetric.h"
#include "randombytes.h"
/*************************************************
* Name:        crypto_kem_keypair_derand
*
* Description: Generates public and private key
*              for CCA-secure Mlkem key encapsulation mechanism
*
* Arguments:   - uint8_t *pk: pointer to output public key
*                (an already allocated array of MLKEM_PUBLICKEYBYTES bytes)
*              - uint8_t *sk: pointer to output private key
*                (an already allocated array of MLKEM_SECRETKEYBYTES bytes)
*              - uint8_t *coins: pointer to input randomness
*                (an already allocated array filled with 2*MLKEM_SYMBYTES random bytes)
**
* Returns 0 (success)
**************************************************/
int crypto_kem_keypair_derand(uint8_t *pk,
                              uint8_t *sk,
                              const uint8_t *coins) {
    indcpa_keypair_derand(pk, sk, coins);
    memcpy(sk + MLKEM_INDCPA_SECRETKEYBYTES, pk, MLKEM_PUBLICKEYBYTES);
    hash_h(sk + MLKEM_SECRETKEYBYTES - 2 * MLKEM_SYMBYTES, pk, MLKEM_PUBLICKEYBYTES);
    /* Value z for pseudo-random output on reject */
    memcpy(sk + MLKEM_SECRETKEYBYTES - MLKEM_SYMBYTES, coins + MLKEM_SYMBYTES, MLKEM_SYMBYTES);
    return 0;
}

/*************************************************
* Name:        crypto_kem_keypair
*
* Description: Generates public and private key
*              for CCA-secure Mlkem key encapsulation mechanism
*
* Arguments:   - uint8_t *pk: pointer to output public key
*                (an already allocated array of MLKEM_PUBLICKEYBYTES bytes)
*              - uint8_t *sk: pointer to output private key
*                (an already allocated array of MLKEM_SECRETKEYBYTES bytes)
*
* Returns 0 (success)
**************************************************/
int crypto_kem_keypair(uint8_t *pk,
                       uint8_t *sk) {
    uint8_t coins[2 * MLKEM_SYMBYTES];
    randombytes(coins, 2 * MLKEM_SYMBYTES);
    crypto_kem_keypair_derand(pk, sk, coins);
    return 0;
}

/*************************************************
* Name:        crypto_kem_enc_derand
*
* Description: Generates cipher text and shared
*              secret for given public key
*
* Arguments:   - uint8_t *ct: pointer to output cipher text
*                (an already allocated array of MLKEM_CIPHERTEXTBYTES bytes)
*              - uint8_t *ss: pointer to output shared secret
*                (an already allocated array of MLKEM_SSBYTES bytes)
*              - const uint8_t *pk: pointer to input public key
*                (an already allocated array of MLKEM_PUBLICKEYBYTES bytes)
*              - const uint8_t *coins: pointer to input randomness
*                (an already allocated array filled with MLKEM_SYMBYTES random bytes)
**
* Returns 0 (success)
**************************************************/
int crypto_kem_enc_derand(uint8_t *ct,
                          uint8_t *ss,
                          const uint8_t *pk,
                          const uint8_t *coins) {
    uint8_t buf[2 * MLKEM_SYMBYTES];
    /* Will contain key, coins */
    uint8_t kr[2 * MLKEM_SYMBYTES];

    memcpy(buf, coins, MLKEM_SYMBYTES);

    /* Multitarget countermeasure for coins + contributory KEM */
    hash_h(buf + MLKEM_SYMBYTES, pk, MLKEM_PUBLICKEYBYTES);
    hash_g(kr, buf, 2 * MLKEM_SYMBYTES);

    /* coins are in kr+MLKEM_SYMBYTES */
    indcpa_enc(ct, buf, pk, kr + MLKEM_SYMBYTES);

    memcpy(ss, kr, MLKEM_SYMBYTES);
    return 0;
}

/*************************************************
* Name:        crypto_kem_enc
*
* Description: Generates cipher text and shared
*              secret for given public key
*
* Arguments:   - uint8_t *ct: pointer to output cipher text
*                (an already allocated array of MLKEM_CIPHERTEXTBYTES bytes)
*              - uint8_t *ss: pointer to output shared secret
*                (an already allocated array of MLKEM_SSBYTES bytes)
*              - const uint8_t *pk: pointer to input public key
*                (an already allocated array of MLKEM_PUBLICKEYBYTES bytes)
*
* Returns 0 (success)
**************************************************/
int crypto_kem_enc(uint8_t *ct,
                   uint8_t *ss,
                   const uint8_t *pk) {
    uint8_t coins[MLKEM_SYMBYTES];
    randombytes(coins, MLKEM_SYMBYTES);
    crypto_kem_enc_derand(ct, ss, pk, coins);
    return 0;
}

/*************************************************
* Name:        crypto_kem_dec
*
* Description: Generates shared secret for given
*              cipher text and private key
*
* Arguments:   - uint8_t *ss: pointer to output shared secret
*                (an already allocated array of MLKEM_SSBYTES bytes)
*              - const uint8_t *ct: pointer to input cipher text
*                (an already allocated array of MLKEM_CIPHERTEXTBYTES bytes)
*              - const uint8_t *sk: pointer to input private key
*                (an already allocated array of MLKEM_SECRETKEYBYTES bytes)
*
* Returns 0.
*
* On failure, ss will contain a pseudo-random value.
**************************************************/
int crypto_kem_dec(uint8_t *ss,
                   const uint8_t *ct,
                   const uint8_t *sk) {
    int fail;
    uint8_t buf[2 * MLKEM_SYMBYTES];
    /* Will contain key, coins */
    uint8_t kr[2 * MLKEM_SYMBYTES];
    const uint8_t *pk = sk + MLKEM_INDCPA_SECRETKEYBYTES;

    indcpa_dec(buf, ct, sk);

    /* Multitarget countermeasure for coins + contributory KEM */
    memcpy(buf + MLKEM_SYMBYTES, sk + MLKEM_SECRETKEYBYTES - 2 * MLKEM_SYMBYTES, MLKEM_SYMBYTES);
    hash_g(kr, buf, 2 * MLKEM_SYMBYTES);

    /* coins are in kr+MLKEM_SYMBYTES */
    fail = indcpa_enc_cmp(ct, buf, pk, kr + MLKEM_SYMBYTES);

    /* Compute rejection key */
    rkprf(ss, sk + MLKEM_SECRETKEYBYTES - MLKEM_SYMBYTES, ct);

    /* Copy true key to return buffer if fail is false */
    cmov(ss, kr, MLKEM_SYMBYTES, (uint8_t) (1 - fail));

    return 0;
}
