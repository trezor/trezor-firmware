// SPDX-License-Identifier: Apache-2.0 or CC0-1.0
#include <stdint.h>
#include "params.h"
#include "poly.h"
#include "ntt.h"
#include "reduce.h"
#include "cbd.h"
#include "symmetric.h"
#include "verify.h"

/*************************************************
* Name:        poly_compress
*
* Description: Compression and subsequent serialization of a polynomial
*
* Arguments:   - uint8_t *r: pointer to output byte array
*                            (of length MLKEM_POLYCOMPRESSEDBYTES)
*              - const poly *a: pointer to input polynomial
**************************************************/
void poly_compress(uint8_t r[MLKEM_POLYCOMPRESSEDBYTES], const poly *a) {
    unsigned int i, j;
    int32_t u;
    uint32_t d0;
    uint8_t t[8];

    #if (MLKEM_POLYCOMPRESSEDBYTES == 128)

    for (i = 0; i < MLKEM_N / 8; i++) {
        for (j = 0; j < 8; j++) {
            // map to positive standard representatives
            u  = a->coeffs[8 * i + j];
            u += (u >> 15) & MLKEM_Q;
            /*    t[j] = ((((uint16_t)u << 4) + MLKEM_Q/2)/MLKEM_Q) & 15; */
            d0 = u << 4;
            d0 += 1665;
            d0 *= 80635;
            d0 >>= 28;
            t[j] = d0 & 0xf;
        }

        r[0] = t[0] | (t[1] << 4);
        r[1] = t[2] | (t[3] << 4);
        r[2] = t[4] | (t[5] << 4);
        r[3] = t[6] | (t[7] << 4);
        r += 4;
    }
    #elif (MLKEM_POLYCOMPRESSEDBYTES == 160)
    for (i = 0; i < MLKEM_N / 8; i++) {
        for (j = 0; j < 8; j++) {
            // map to positive standard representatives
            u  = a->coeffs[8 * i + j];
            u += (u >> 15) & MLKEM_Q;
            /*    t[j] = ((((uint32_t)u << 5) + MLKEM_Q/2)/MLKEM_Q) & 31; */
            d0 = u << 5;
            d0 += 1664;
            d0 *= 40318;
            d0 >>= 27;
            t[j] = d0 & 0x1f;
        }

        r[0] = (t[0] >> 0) | (t[1] << 5);
        r[1] = (t[1] >> 3) | (t[2] << 2) | (t[3] << 7);
        r[2] = (t[3] >> 1) | (t[4] << 4);
        r[3] = (t[4] >> 4) | (t[5] << 1) | (t[6] << 6);
        r[4] = (t[6] >> 2) | (t[7] << 3);
        r += 5;
    }
    #else
#error "MLKEM_POLYCOMPRESSEDBYTES needs to be in {128, 160}"
    #endif
}

/*************************************************
* Name:        poly_decompress
*
* Description: De-serialization and subsequent decompression of a polynomial;
*              approximate inverse of poly_compress
*
* Arguments:   - poly *r: pointer to output polynomial
*              - const uint8_t *a: pointer to input byte array
*                                  (of length MLKEM_POLYCOMPRESSEDBYTES bytes)
**************************************************/
void poly_decompress(poly *r, const uint8_t a[MLKEM_POLYCOMPRESSEDBYTES]) {
    unsigned int i;

    #if (MLKEM_POLYCOMPRESSEDBYTES == 128)
    for (i = 0; i < MLKEM_N / 2; i++) {
        r->coeffs[2 * i + 0] = (((uint16_t)(a[0] & 15) * MLKEM_Q) + 8) >> 4;
        r->coeffs[2 * i + 1] = (((uint16_t)(a[0] >> 4) * MLKEM_Q) + 8) >> 4;
        a += 1;
    }
    #elif (MLKEM_POLYCOMPRESSEDBYTES == 160)
    unsigned int j;
    uint8_t t[8];
    for (i = 0; i < MLKEM_N / 8; i++) {
        t[0] = (a[0] >> 0);
        t[1] = (a[0] >> 5) | (a[1] << 3);
        t[2] = (a[1] >> 2);
        t[3] = (a[1] >> 7) | (a[2] << 1);
        t[4] = (a[2] >> 4) | (a[3] << 4);
        t[5] = (a[3] >> 1);
        t[6] = (a[3] >> 6) | (a[4] << 2);
        t[7] = (a[4] >> 3);
        a += 5;

        for (j = 0; j < 8; j++) {
            r->coeffs[8 * i + j] = ((uint32_t)(t[j] & 31) * MLKEM_Q + 16) >> 5;
        }
    }
    #else
#error "MLKEM_POLYCOMPRESSEDBYTES needs to be in {128, 160}"
    #endif
}

/*************************************************
* Name:        poly_packcompress
*
* Description: Serialization and subsequent compression of a polynomial of a polyvec,
*              writes to a byte string representation of the whole polyvec.
*              Used to compress a polyvec one poly at a time in a loop.
*
* Arguments:   - unsigned char *r:  pointer to output byte string representation of a polyvec (of length MLKEM_POLYVECCOMPRESSEDBYTES)
*              - const poly *a:     pointer to input polynomial
*              - int i:             index of to be serialized polynomial in serialized polyec
**************************************************/
void poly_packcompress(unsigned char *r, poly *a, int i) {
    int j, k;
    uint64_t d0;

    #if (MLKEM_POLYVECCOMPRESSEDBYTES == (MLKEM_K * 352))
    uint16_t t[8];

    for (j = 0; j < MLKEM_N / 8; j++) {
        for (k = 0; k < 8; k++) {
            t[k]  = a->coeffs[8 * j + k];
            t[k] += ((int16_t)t[k] >> 15) & MLKEM_Q;
            /*      t[k]  = ((((uint32_t)t[k] << 11) + MLKEM_Q/2)/MLKEM_Q) & 0x7ff; */
            d0 = t[k];
            d0 <<= 11;
            d0 += 1664;
            d0 *= 645084;
            d0 >>= 31;
            t[k] = d0 & 0x7ff;
        }

        r[352 * i + 11 * j + 0] =  t[0] & 0xff;
        r[352 * i + 11 * j + 1] = (t[0] >>  8) | ((t[1] & 0x1f) << 3);
        r[352 * i + 11 * j + 2] = (t[1] >>  5) | ((t[2] & 0x03) << 6);
        r[352 * i + 11 * j + 3] = (t[2] >>  2) & 0xff;
        r[352 * i + 11 * j + 4] = (t[2] >> 10) | ((t[3] & 0x7f) << 1);
        r[352 * i + 11 * j + 5] = (t[3] >>  7) | ((t[4] & 0x0f) << 4);
        r[352 * i + 11 * j + 6] = (t[4] >>  4) | ((t[5] & 0x01) << 7);
        r[352 * i + 11 * j + 7] = (t[5] >>  1) & 0xff;
        r[352 * i + 11 * j + 8] = (t[5] >>  9) | ((t[6] & 0x3f) << 2);
        r[352 * i + 11 * j + 9] = (t[6] >>  6) | ((t[7] & 0x07) << 5);
        r[352 * i + 11 * j + 10] = (t[7] >>  3);
    }
    #elif (MLKEM_POLYVECCOMPRESSEDBYTES == (MLKEM_K * 320))
    uint16_t t[4];

    for (j = 0; j < MLKEM_N / 4; j++) {
        for (k = 0; k < 4; k++) {
            t[k]  = a->coeffs[4 * j + k];
            t[k] += ((int16_t)t[k] >> 15) & MLKEM_Q;
            /*      t[k]  = ((((uint32_t)t[k] << 10) + MLKEM_Q/2)/ MLKEM_Q) & 0x3ff; */
            d0 = t[k];
            d0 <<= 10;
            d0 += 1665;
            d0 *= 1290167;
            d0 >>= 32;
            t[k] = d0 & 0x3ff;
        }
        r[320 * i + 5 * j + 0] =   t[0] & 0xff;
        r[320 * i + 5 * j + 1] =  (t[0] >>  8) | ((t[1] & 0x3f) << 2);
        r[320 * i + 5 * j + 2] = ((t[1] >>  6) | ((t[2] & 0x0f) << 4)) & 0xff;
        r[320 * i + 5 * j + 3] = ((t[2] >>  4) | ((t[3] & 0x03) << 6)) & 0xff;
        r[320 * i + 5 * j + 4] =  (t[3] >>  2) & 0xff;
    }
    #else
#error "MLKEM_POLYVECCOMPRESSEDBYTES needs to in (MLKEM_K * {352, 320})"
    #endif
}

/*************************************************
* Name:        poly_unpackdecompress
*
* Description: Deserialization and subsequent compression of a polynomial of a polyvec,
*              Used to uncompress a polyvec one poly at a time in a loop.
*
* Arguments:   - const poly *r:     pointer to output polynomial
*              - unsigned char *a:  pointer to input byte string representation of a polyvec (of length MLKEM_POLYVECCOMPRESSEDBYTES)
*              - int i:             index of poly in polyvec to decompress
**************************************************/
void poly_unpackdecompress(poly *r, const unsigned char *a, int i) {
    int j;
    #if (MLKEM_POLYVECCOMPRESSEDBYTES == (MLKEM_K * 352))
    for (j = 0; j < MLKEM_N / 8; j++) {
        r->coeffs[8 * j + 0] =  (((a[352 * i + 11 * j + 0]       | (((uint32_t)a[352 * i + 11 * j + 1] & 0x07) << 8)) * MLKEM_Q) + 1024) >> 11;
        r->coeffs[8 * j + 1] = ((((a[352 * i + 11 * j + 1] >> 3) | (((uint32_t)a[352 * i + 11 * j + 2] & 0x3f) << 5)) * MLKEM_Q) + 1024) >> 11;
        r->coeffs[8 * j + 2] = ((((a[352 * i + 11 * j + 2] >> 6) | (((uint32_t)a[352 * i + 11 * j + 3] & 0xff) << 2) | (((uint32_t)a[352 * i + 11 * j + 4] & 0x01) << 10)) * MLKEM_Q) + 1024) >> 11;
        r->coeffs[8 * j + 3] = ((((a[352 * i + 11 * j + 4] >> 1) | (((uint32_t)a[352 * i + 11 * j + 5] & 0x0f) << 7)) * MLKEM_Q) + 1024) >> 11;
        r->coeffs[8 * j + 4] = ((((a[352 * i + 11 * j + 5] >> 4) | (((uint32_t)a[352 * i + 11 * j + 6] & 0x7f) << 4)) * MLKEM_Q) + 1024) >> 11;
        r->coeffs[8 * j + 5] = ((((a[352 * i + 11 * j + 6] >> 7) | (((uint32_t)a[352 * i + 11 * j + 7] & 0xff) << 1) | (((uint32_t)a[352 * i + 11 * j + 8] & 0x03) <<  9)) * MLKEM_Q) + 1024) >> 11;
        r->coeffs[8 * j + 6] = ((((a[352 * i + 11 * j + 8] >> 2) | (((uint32_t)a[352 * i + 11 * j + 9] & 0x1f) << 6)) * MLKEM_Q) + 1024) >> 11;
        r->coeffs[8 * j + 7] = ((((a[352 * i + 11 * j + 9] >> 5) | (((uint32_t)a[352 * i + 11 * j + 10] & 0xff) << 3)) * MLKEM_Q) + 1024) >> 11;
    }
    #elif (MLKEM_POLYVECCOMPRESSEDBYTES == (MLKEM_K * 320))
    for (j = 0; j < MLKEM_N / 4; j++) {
        r->coeffs[4 * j + 0] =  (((a[320 * i + 5 * j + 0]       | (((uint32_t)a[320 * i + 5 * j + 1] & 0x03) << 8)) * MLKEM_Q) + 512) >> 10;
        r->coeffs[4 * j + 1] = ((((a[320 * i + 5 * j + 1] >> 2) | (((uint32_t)a[320 * i + 5 * j + 2] & 0x0f) << 6)) * MLKEM_Q) + 512) >> 10;
        r->coeffs[4 * j + 2] = ((((a[320 * i + 5 * j + 2] >> 4) | (((uint32_t)a[320 * i + 5 * j + 3] & 0x3f) << 4)) * MLKEM_Q) + 512) >> 10;
        r->coeffs[4 * j + 3] = ((((a[320 * i + 5 * j + 3] >> 6) | (((uint32_t)a[320 * i + 5 * j + 4] & 0xff) << 2)) * MLKEM_Q) + 512) >> 10;
    }
    #else
#error "MLKEM_POLYVECCOMPRESSEDBYTES needs to be in {320*MLKEM_K, 352*MLKEM_K}"
    #endif
}

/*************************************************
* Name:        cmp_poly_compress
*
* Description: Serializes and consequently compares polynomial to a serialized polynomial
*
* Arguments:   - const unsigned char *r:    pointer to serialized polynomial to compare with
*              - poly *a:                   pointer to input polynomial to serialize and compare
* Returns:                                  boolean indicating whether the polynomials are equal
**************************************************/
int cmp_poly_compress(const unsigned char *r, poly *a) {
    unsigned char rc = 0;
    int16_t u;
    uint32_t d0;
    uint8_t t[8];
    int i, j, k = 0;

    #if (MLKEM_POLYCOMPRESSEDBYTES == 128)
    for (i = 0; i < MLKEM_N / 8; i++) {
        for (j = 0; j < 8; j++) {
            // map to positive standard representatives
            u  = a->coeffs[8 * i + j];
            u += (u >> 15) & MLKEM_Q;
            /*    t[j] = ((((uint16_t)u << 4) + MLKEM_Q/2)/MLKEM_Q) & 15; */
            d0 = u << 4;
            d0 += 1665;
            d0 *= 80635;
            d0 >>= 28;
            t[j] = d0 & 0xf;
        }
        rc |= r[k]      ^ (t[0] | (t[1] << 4));
        rc |= r[k + 1]  ^ (t[2] | (t[3] << 4));
        rc |= r[k + 2]  ^ (t[4] | (t[5] << 4));
        rc |= r[k + 3]  ^ (t[6] | (t[7] << 4));
        k += 4;
    }
    #elif (MLKEM_POLYCOMPRESSEDBYTES == 160)
    for (i = 0; i < MLKEM_N / 8; i++) {
        for (j = 0; j < 8; j++) {
            // map to positive standard representatives
            u  = a->coeffs[8 * i + j];
            u += (u >> 15) & MLKEM_Q;
            /*      t[j] = ((((uint32_t)u << 5) + MLKEM_Q/2)/MLKEM_Q) & 31; */
            d0 = u << 5;
            d0 += 1664;
            d0 *= 40318;
            d0 >>= 27;
            t[j] = d0 & 0x1f;
        }

        rc |= r[k]   ^ (t[0]       | (t[1] << 5));
        rc |= r[k + 1] ^ ((t[1] >> 3) | (t[2] << 2) | (t[3] << 7));
        rc |= r[k + 2] ^ ((t[3] >> 1) | (t[4] << 4));
        rc |= r[k + 3] ^ ((t[4] >> 4) | (t[5] << 1) | (t[6] << 6));
        rc |= r[k + 4] ^ ((t[6] >> 2) | (t[7] << 3));
        k += 5;
    }
    #else
#error "MLKEM_POLYCOMPRESSEDBYTES needs to be in {128, 160}"
    #endif
    return rc;
}

/*************************************************
* Name:        cmp_poly_packcompress
*
* Description: Serializes and consequently compares poly of polyvec to a serialized polyvec
*              Should be called in a loop over all poly's of a polyvec.
*
* Arguments:   - const unsigned char *r:    pointer to serialized polyvec to compare with
*              - poly *a:                   pointer to input polynomial of polyvec to serialize and compare
*              - int i:                     index of poly in polyvec to compare with
* Returns:                                  boolean indicating whether the polyvecs are equal
**************************************************/
int cmp_poly_packcompress(const unsigned char *r, poly *a, int i) {
    unsigned char rc = 0;
    int j, k;
    uint64_t d0;

    #if (MLKEM_POLYVECCOMPRESSEDBYTES == (MLKEM_K * 352))
    uint16_t t[8];
    for (j = 0; j < MLKEM_N / 8; j++) {
        for (k = 0; k < 8; k++) {
            t[k]  = a->coeffs[8 * j + k];
            t[k] += ((int16_t)t[k] >> 15) & MLKEM_Q;
            /*      t[k]  = ((((uint32_t)t[k] << 11) + MLKEM_Q/2)/MLKEM_Q) & 0x7ff; */
            d0 = t[k];
            d0 <<= 11;
            d0 += 1664;
            d0 *= 645084;
            d0 >>= 31;
            t[k] = d0 & 0x7ff;
        }

        rc |= r[352 * i + 11 * j + 0] ^ (t[0] & 0xff);
        rc |= r[352 * i + 11 * j + 1] ^ ((t[0] >>  8) | ((t[1] & 0x1f) << 3));
        rc |= r[352 * i + 11 * j + 2] ^ ((t[1] >>  5) | ((t[2] & 0x03) << 6));
        rc |= r[352 * i + 11 * j + 3] ^ ((t[2] >>  2) & 0xff);
        rc |= r[352 * i + 11 * j + 4] ^ ((t[2] >> 10) | ((t[3] & 0x7f) << 1));
        rc |= r[352 * i + 11 * j + 5] ^ ((t[3] >>  7) | ((t[4] & 0x0f) << 4));
        rc |= r[352 * i + 11 * j + 6] ^ ((t[4] >>  4) | ((t[5] & 0x01) << 7));
        rc |= r[352 * i + 11 * j + 7] ^ ((t[5] >>  1) & 0xff);
        rc |= r[352 * i + 11 * j + 8] ^ ((t[5] >>  9) | ((t[6] & 0x3f) << 2));
        rc |= r[352 * i + 11 * j + 9] ^ ((t[6] >>  6) | ((t[7] & 0x07) << 5));
        rc |= r[352 * i + 11 * j + 10] ^ ((t[7] >>  3));
    }
    #elif (MLKEM_POLYVECCOMPRESSEDBYTES == (MLKEM_K * 320))
    uint16_t t[4];
    for (j = 0; j < MLKEM_N / 4; j++) {
        for (k = 0; k < 4; k++) {
            t[k]  = a->coeffs[4 * j + k];
            t[k] += ((int16_t)t[k] >> 15) & MLKEM_Q;
            /*      t[k]  = ((((uint32_t)t[k] << 10) + MLKEM_Q/2)/ MLKEM_Q) & 0x3ff; */
            d0 = t[k];
            d0 <<= 10;
            d0 += 1665;
            d0 *= 1290167;
            d0 >>= 32;
            t[k] = d0 & 0x3ff;
        }

        rc |= r[320 * i + 5 * j + 0] ^ (t[0] & 0xff);
        rc |= r[320 * i + 5 * j + 1] ^ ((t[0] >>  8) | ((t[1] & 0x3f) << 2));
        rc |= r[320 * i + 5 * j + 2] ^ (((t[1] >>  6) | ((t[2] & 0x0f) << 4)) & 0xff);
        rc |= r[320 * i + 5 * j + 3] ^ (((t[2] >>  4) | ((t[3] & 0x03) << 6)) & 0xff);
        rc |= r[320 * i + 5 * j + 4] ^ ((t[3] >>  2) & 0xff);
    }
    #else
#error "MLKEM_POLYVECCOMPRESSEDBYTES needs to be in {320*MLKEM_K, 352*MLKEM_K}"
    #endif
    return rc;
}

/*************************************************
* Name:        poly_tobytes
*
* Description: Serialization of a polynomial
*
* Arguments:   - uint8_t *r: pointer to output byte array
*                            (needs space for MLKEM_POLYBYTES bytes)
*              - const poly *a: pointer to input polynomial
**************************************************/
void poly_tobytes(uint8_t r[MLKEM_POLYBYTES], const poly *a) {
    unsigned int i;
    uint16_t t0, t1;

    for (i = 0; i < MLKEM_N / 2; i++) {
        // map to positive standard representatives
        t0  = a->coeffs[2 * i];
        t0 += ((int16_t)t0 >> 15) & MLKEM_Q;
        t1 = a->coeffs[2 * i + 1];
        t1 += ((int16_t)t1 >> 15) & MLKEM_Q;
        r[3 * i + 0] = (t0 >> 0);
        r[3 * i + 1] = (t0 >> 8) | (t1 << 4);
        r[3 * i + 2] = (t1 >> 4);
    }
}

/*************************************************
* Name:        poly_frombytes
*
* Description: De-serialization of a polynomial;
*              inverse of poly_tobytes
*
* Arguments:   - poly *r: pointer to output polynomial
*              - const uint8_t *a: pointer to input byte array
*                                  (of MLKEM_POLYBYTES bytes)
**************************************************/
void poly_frombytes(poly *r, const uint8_t a[MLKEM_POLYBYTES]) {
    unsigned int i;
    for (i = 0; i < MLKEM_N / 2; i++) {
        r->coeffs[2 * i]   = ((a[3 * i + 0] >> 0) | ((uint16_t)a[3 * i + 1] << 8)) & 0xFFF;
        r->coeffs[2 * i + 1] = ((a[3 * i + 1] >> 4) | ((uint16_t)a[3 * i + 2] << 4)) & 0xFFF;
    }
}

/*************************************************
* Name:        poly_frombytes_basemul_montgomery
*
* Description: Multiplication of a polynomial with a de-serialization of another polynomial;
*              Conditionally accumulate.
*
* Arguments:   - poly *r:                pointer to output polynomial
*              - const poly *b:          pointer to input polynomial
*              - const unsigned char *a: pointer to input byte array (of MLKEM_POLYBYTES bytes)
*              - int add: flag to conditionally accumulate into r if add != 0
*
**************************************************/

void poly_frombytes_basemul_montgomery(poly *r, const poly *b, const unsigned char *a, int add) {
    unsigned int i;
    int16_t ap[4];
    for (i = 0; i < MLKEM_N / 4; i++) {
        ap[0]   = ((a[6 * i + 0] >> 0) | ((uint16_t)a[6 * i + 1] << 8)) & 0xFFF;
        ap[1] = ((a[6 * i + 1] >> 4) | ((uint16_t)a[6 * i + 2] << 4)) & 0xFFF;
        ap[2]   = ((a[6 * i + 3] >> 0) | ((uint16_t)a[6 * i + 4] << 8)) & 0xFFF;
        ap[3] = ((a[6 * i + 4] >> 4) | ((uint16_t)a[6 * i + 5] << 4)) & 0xFFF;

        if (!add) {
            basemul(&r->coeffs[4 * i], ap, &b->coeffs[4 * i], zetas[64 + i]);
            basemul(&r->coeffs[4 * i + 2], ap + 2, &b->coeffs[4 * i + 2], -zetas[64 + i]);
        } else {
            basemul_acc(&r->coeffs[4 * i], ap, &b->coeffs[4 * i], zetas[64 + i]);
            basemul_acc(&r->coeffs[4 * i + 2], ap + 2, &b->coeffs[4 * i + 2], -zetas[64 + i]);
        }

    }
}

/*************************************************
* Name:        poly_frommsg
*
* Description: Convert 32-byte message to polynomial
*
* Arguments:   - poly *r: pointer to output polynomial
*              - const uint8_t *msg: pointer to input message
**************************************************/
void poly_frommsg(poly *r, const uint8_t msg[MLKEM_INDCPA_MSGBYTES]) {
    unsigned int i, j;

    #if (MLKEM_INDCPA_MSGBYTES != MLKEM_N/8)
#error "MLKEM_INDCPA_MSGBYTES must be equal to MLKEM_N/8 bytes!"
    #endif

    for (i = 0; i < MLKEM_N / 8; i++) {
        for (j = 0; j < 8; j++) {
            r->coeffs[8 * i + j] = 0;
            cmov_int16(r->coeffs + 8 * i + j, ((MLKEM_Q + 1) / 2), (msg[i] >> j) & 1);
        }
    }
}

/*************************************************
* Name:        poly_tomsg
*
* Description: Convert polynomial to 32-byte message
*
* Arguments:   - uint8_t *msg: pointer to output message
*              - const poly *a: pointer to input polynomial
**************************************************/
void poly_tomsg(uint8_t msg[MLKEM_INDCPA_MSGBYTES], const poly *a) {
    unsigned int i, j;
    uint32_t t;

    for (i = 0; i < MLKEM_N / 8; i++) {
        msg[i] = 0;
        for (j = 0; j < 8; j++) {
            t  = a->coeffs[8 * i + j];
            // t += ((int16_t)t >> 15) & MLKEM_Q;
            // t  = (((t << 1) + MLKEM_Q/2)/MLKEM_Q) & 1;
            t <<= 1;
            t += 1665;
            t *= 80635;
            t >>= 28;
            t &= 1;
            msg[i] |= t << j;
        }
    }
}

/*************************************************
* Name:        poly_noise_eta1
*
* Description: Sample a polynomial deterministically from a seed and a nonce,
*              with output polynomial close to centered binomial distribution
*              with parameter MLKEM_ETA1.
*              Conditionally accumulate.
*
* Arguments:   - poly *r: pointer to output polynomial
*              - const uint8_t *seed: pointer to input seed
*                                     (of length MLKEM_SYMBYTES bytes)
*              - uint8_t nonce: one-byte input nonce
*              - int add: flag to conditionally accumulate into r if add != 0
**************************************************/
void poly_noise_eta1(poly *r, const unsigned char *seed, unsigned char nonce, int add) {
    unsigned char buf[MLKEM_ETA1 * MLKEM_N / 4];

    prf(buf, MLKEM_ETA1 * MLKEM_N / 4, seed, nonce);
    poly_cbd_eta1(r, buf, add);
}

/*************************************************
* Name:        poly_noise_eta2
*
* Description: Sample a polynomial deterministically from a seed and a nonce,
*              with output polynomial close to centered binomial distribution
*              with parameter MLKEM_ETA2
*              Conditionally accumulate.
*
* Arguments:   - poly *r: pointer to output polynomial
*              - const uint8_t *seed: pointer to input seed
*                                     (of length MLKEM_SYMBYTES bytes)
*              - uint8_t nonce: one-byte input nonce
*              - int add: flag to conditionally accumulate into r if add != 0
**************************************************/
void poly_noise_eta2(poly *r, const unsigned char *seed, unsigned char nonce, int add) {
    uint8_t buf[MLKEM_ETA2 * MLKEM_N / 4];
    prf(buf, sizeof(buf), seed, nonce);
    poly_cbd_eta2(r, buf, add);
}

/*************************************************
* Name:        poly_ntt
*
* Description: Computes negacyclic number-theoretic transform (NTT) of
*              a polynomial in place;
*              inputs assumed to be in normal order, output in bitreversed order
*
* Arguments:   - uint16_t *r: pointer to in/output polynomial
**************************************************/
void poly_ntt(poly *r) {
    ntt(r->coeffs);
    poly_reduce(r);
}

/*************************************************
* Name:        poly_invntt_tomont
*
* Description: Computes inverse of negacyclic number-theoretic transform (NTT)
*              of a polynomial in place;
*              inputs assumed to be in bitreversed order, output in normal order
*
* Arguments:   - uint16_t *a: pointer to in/output polynomial
**************************************************/
void poly_invntt_tomont(poly *r) {
    invntt(r->coeffs);
}

/*************************************************
* Name:        poly_basemul_montgomery
*
* Description: Multiplication of two polynomials in NTT domain
*
* Arguments:   - poly *r: pointer to output polynomial
*              - const poly *a: pointer to first input polynomial
*              - const poly *b: pointer to second input polynomial
**************************************************/
void poly_basemul_montgomery(poly *r, const poly *a, const poly *b, int add) {
    unsigned int i;
    if (!add) {
        for (i = 0; i < MLKEM_N / 4; i++) {
            basemul(&r->coeffs[4 * i], &a->coeffs[4 * i], &b->coeffs[4 * i], zetas[64 + i]);
            basemul(&r->coeffs[4 * i + 2], &a->coeffs[4 * i + 2], &b->coeffs[4 * i + 2], -zetas[64 + i]);
        }
    } else {
        for (i = 0; i < MLKEM_N / 4; i++) {
            basemul_acc(&r->coeffs[4 * i], &a->coeffs[4 * i], &b->coeffs[4 * i], zetas[64 + i]);
            basemul_acc(&r->coeffs[4 * i + 2], &a->coeffs[4 * i + 2], &b->coeffs[4 * i + 2], -zetas[64 + i]);
        }
    }
}

/*************************************************
* Name:        poly_tomont
*
* Description: Inplace conversion of all coefficients of a polynomial
*              from normal domain to Montgomery domain
*
* Arguments:   - poly *r: pointer to input/output polynomial
**************************************************/
void poly_tomont(poly *r) {
    unsigned int i;
    const int16_t f = (1ULL << 32) % MLKEM_Q;
    for (i = 0; i < MLKEM_N; i++) {
        r->coeffs[i] = montgomery_reduce((int32_t)r->coeffs[i] * f);
    }
}

/*************************************************
* Name:        poly_reduce
*
* Description: Applies Barrett reduction to all coefficients of a polynomial
*              for details of the Barrett reduction see comments in reduce.c
*
* Arguments:   - poly *r: pointer to input/output polynomial
**************************************************/
void poly_reduce(poly *r) {
    unsigned int i;
    for (i = 0; i < MLKEM_N; i++) {
        r->coeffs[i] = barrett_reduce(r->coeffs[i]);
    }
}

/*************************************************
* Name:        poly_add
*
* Description: Add two polynomials; no modular reduction is performed
*
* Arguments: - poly *r: pointer to output polynomial
*            - const poly *a: pointer to first input polynomial
*            - const poly *b: pointer to second input polynomial
**************************************************/
void poly_add(poly *r, const poly *a, const poly *b) {
    unsigned int i;
    for (i = 0; i < MLKEM_N; i++) {
        r->coeffs[i] = a->coeffs[i] + b->coeffs[i];
    }
}

/*************************************************
* Name:        poly_sub
*
* Description: Subtract two polynomials; no modular reduction is performed
*
* Arguments: - poly *r:       pointer to output polynomial
*            - const poly *a: pointer to first input polynomial
*            - const poly *b: pointer to second input polynomial
**************************************************/
void poly_sub(poly *r, const poly *a, const poly *b) {
    unsigned int i;
    for (i = 0; i < MLKEM_N; i++) {
        r->coeffs[i] = a->coeffs[i] - b->coeffs[i];
    }
}
