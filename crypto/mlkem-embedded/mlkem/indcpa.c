// SPDX-License-Identifier: Apache-2.0 or CC0-1.0
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "params.h"
#include "indcpa.h"
#include "polyvec.h"
#include "poly.h"
#include "ntt.h"
#include "symmetric.h"
#include "randombytes.h"
#include "matacc.h"

/*************************************************
 * Name:        indcpa_keypair_derand
 *
 * Description: Generates public and private key for the CPA-secure
 *              public-key encryption scheme underlying Mlkem
 *
 * Arguments:   - uint8_t *pk: pointer to output public key
 *                             (of length MLKEM_INDCPA_PUBLICKEYBYTES bytes)
 *              - uint8_t *sk: pointer to output private key
 *                             (of length MLKEM_INDCPA_SECRETKEYBYTES bytes)
 *              - const uint8_t *coins: pointer to input randomness
 *                             (of length MLKEM_SYMBYTES bytes)
 **************************************************/
void indcpa_keypair_derand(uint8_t pk[MLKEM_INDCPA_PUBLICKEYBYTES],
                           uint8_t sk[MLKEM_INDCPA_SECRETKEYBYTES],
                           const uint8_t coins[MLKEM_SYMBYTES]) {
    unsigned int i;
    uint8_t buf[2 * MLKEM_SYMBYTES];
    const uint8_t *publicseed = buf;
    const uint8_t *noiseseed = buf + MLKEM_SYMBYTES;
    uint8_t nonce = 0;
    polyvec skpv;
    poly pkp;

    /* (rho, sigma) = G(d || k) with the parameter k appended to the seed, as
     * required by FIPS 203, Algorithm 13 (K-PKE.KeyGen). The upstream code
     * implements the initial public draft, which computes G(d). */
    uint8_t coins_k[MLKEM_SYMBYTES + 1];
    memcpy(coins_k, coins, MLKEM_SYMBYTES);
    coins_k[MLKEM_SYMBYTES] = MLKEM_K;
    hash_g(buf, coins_k, MLKEM_SYMBYTES + 1);

    for (i = 0; i < MLKEM_K; i++) {
        poly_getnoise_eta1(&skpv.vec[i], noiseseed, nonce++);
    }

    polyvec_ntt(&skpv);

    // matrix-vector multiplication
    for (i = 0; i < MLKEM_K; i++) {
        matacc(&pkp, &skpv, i, publicseed, 0);

        poly_invntt_tomont(&pkp);
        poly_addnoise_eta1(&pkp, noiseseed, nonce++);
        poly_ntt(&pkp);
        poly_reduce(&pkp);

        poly_tobytes(pk + i * MLKEM_POLYBYTES, &pkp);
    }

    polyvec_tobytes(sk, &skpv);
    memcpy(pk + MLKEM_POLYVECBYTES, publicseed, MLKEM_SYMBYTES);
}

/*************************************************
 * Name:        indcpa_enc
 *
 * Description: Encryption function of the CPA-secure
 *              public-key encryption scheme underlying Mlkem.
 *
 * Arguments:   - uint8_t *c: pointer to output ciphertext
 *                            (of length MLKEM_INDCPA_BYTES bytes)
 *              - const uint8_t *m: pointer to input message
 *                                  (of length MLKEM_INDCPA_MSGBYTES bytes)
 *              - const uint8_t *pk: pointer to input public key
 *                                   (of length MLKEM_INDCPA_PUBLICKEYBYTES)
 *              - const uint8_t *coins: pointer to input random coins used as seed
 *                                      (of length MLKEM_SYMBYTES) to deterministically
 *                                      generate all randomness
 **************************************************/
void indcpa_enc(uint8_t c[MLKEM_INDCPA_BYTES],
                const uint8_t m[MLKEM_INDCPA_MSGBYTES],
                const uint8_t pk[MLKEM_INDCPA_PUBLICKEYBYTES],
                const uint8_t coins[MLKEM_SYMBYTES]) {
    polyvec sp;
    poly b;
    poly *pkp = &b;
    poly *k = &b;
    poly *v = &sp.vec[0];
    const unsigned char *seed = pk + MLKEM_POLYVECBYTES;
    int i;
    unsigned char nonce = 0;

    for (i = 0; i < MLKEM_K; i++) {
        poly_getnoise_eta1(sp.vec + i, coins, nonce++);
    }

    polyvec_ntt(&sp);

    // matrix-vector multiplication
    for (i = 0; i < MLKEM_K; i++) {
        matacc(&b, &sp, i, seed, 1);
        poly_invntt_tomont(&b);

        poly_addnoise_eta2(&b, coins, nonce++);
        poly_reduce(&b);

        poly_packcompress(c, &b, i);
    }

    poly_frombytes(pkp, pk);
    poly_basemul(v, pkp, &sp.vec[0]);
    for (i = 1 ; i < MLKEM_K; i++) {
        poly_frombytes(pkp, pk + i * MLKEM_POLYBYTES);
        poly_basemul_acc(v, pkp, &sp.vec[i]);
    }
    poly_invntt_tomont(v);
    poly_addnoise_eta2(v, coins, nonce++);

    poly_frommsg(k, m);
    poly_add(v, v, k);
    poly_reduce(v);

    poly_compress(c + MLKEM_POLYVECCOMPRESSEDBYTES, v);
}

/*************************************************
 * Name:        indcpa_dec
 *
 * Description: Decryption function of the CPA-secure
 *              public-key encryption scheme underlying Mlkem.
 *
 * Arguments:   - uint8_t *m: pointer to output decrypted message
 *                            (of length MLKEM_INDCPA_MSGBYTES)
 *              - const uint8_t *c: pointer to input ciphertext
 *                                  (of length MLKEM_INDCPA_BYTES)
 *              - const uint8_t *sk: pointer to input secret key
 *                                   (of length MLKEM_INDCPA_SECRETKEYBYTES)
 **************************************************/
void __attribute__ ((noinline)) indcpa_dec(uint8_t m[MLKEM_INDCPA_MSGBYTES],
        const uint8_t c[MLKEM_INDCPA_BYTES],
        const uint8_t sk[MLKEM_INDCPA_SECRETKEYBYTES]) {
    poly mp, bp;
    poly *v = &bp;

    poly_unpackdecompress(&bp, c, 0);
    poly_ntt(&bp);
    poly_frombytes_basemul(&mp, &bp, sk);

    for (int i = 1; i < MLKEM_K; i++) {
        poly_unpackdecompress(&bp, c, i);
        poly_ntt(&bp);
        poly_frombytes_basemul_acc(&mp,  &bp, sk + i * MLKEM_POLYBYTES);
    }
    poly_invntt_tomont(&mp);

    poly_decompress(v, c + MLKEM_POLYVECCOMPRESSEDBYTES);
    poly_sub(&mp, v, &mp);
    poly_reduce(&mp);

    poly_tomsg(m, &mp);
}

unsigned char indcpa_enc_cmp(const unsigned char *ct,
                             const unsigned char *m,
                             const unsigned char *pk,
                             const unsigned char *coins) {
    uint64_t rc = 0;
    polyvec sp;
    poly b;
    poly *pkp = &b;
    poly *k = &b;
    poly *v = &sp.vec[0];
    const unsigned char *seed = pk + MLKEM_POLYVECBYTES;
    int i;
    unsigned char nonce = 0;

    for (i = 0; i < MLKEM_K; i++) {
        poly_getnoise_eta1(sp.vec + i, coins, nonce++);
    }

    polyvec_ntt(&sp);

    // matrix-vector multiplication
    for (i = 0; i < MLKEM_K; i++) {
        matacc(&b, &sp, i, seed, 1);
        poly_invntt_tomont(&b);

        poly_addnoise_eta2(&b, coins, nonce++);
        poly_reduce(&b);

        rc |= cmp_poly_packcompress(ct, &b, i);
    }

    poly_frombytes(pkp, pk);
    poly_basemul(v, pkp, &sp.vec[0]);
    for (i = 1 ; i < MLKEM_K; i++) {
        poly_frombytes(pkp, pk + i * MLKEM_POLYBYTES);
        poly_basemul_acc(v, pkp, &sp.vec[i]);
    }
    poly_invntt_tomont(v);
    poly_addnoise_eta2(v, coins, nonce++);

    poly_frommsg(k, m);
    poly_add(v, v, k);
    poly_reduce(v);

    rc |= cmp_poly_compress(ct + MLKEM_POLYVECCOMPRESSEDBYTES, v);

    rc = ~rc + 1;
    rc >>= 63;
    return (unsigned char)rc;
}
