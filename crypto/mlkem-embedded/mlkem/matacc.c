// SPDX-License-Identifier: Apache-2.0
#include "ntt.h"
#include "poly.h"
#include "polyvec.h"
#include "symmetric.h"
#include "matacc.h"

static void doublebasemul(int16_t r[4], const int16_t b[4], const int16_t a[4], int k, int add) {
    if (!add) {
        basemul(r, a, b, zetas[64 + k]);
        basemul(&r[2], &a[2], &b[2], -zetas[64 + k]);
    } else {
        basemul_acc(r, a, b, zetas[64 + k]);
        basemul_acc(&r[2], &a[2], &b[2], -zetas[64 + k]);
    }
}

/*************************************************
 * Name:        matacc_inner
 *
 * Description: Multiplies a polynomial of A or A^T, generated on-the-fly,
 *              with a polynomials polynomial and accumulates into the result.
 *
 * Arguments:   - poly *r:                    pointer to output polynomial to accumulate in
 *              - poly *b:                    pointer to input polynomial to multiply with
 *              - unsigned char i:            byte to indicate the index < KYBER_K of the row of A or A^T
 *              - unsigned char j:            byte to indicate the index < KYBER_K of the column of A or A^T
 *              - const unsigned char *seed:  pointer to the public seed used to generate A
 *              - int transposed:             boolean indicating whether A or A^T is generated
 *              - int add:                    boolean indicating whether this is accumulating into r (add=0 will initialize r to 0)
 **************************************************/
static void matacc_inner(poly *r, const poly *b, unsigned char i, unsigned char j, const unsigned char *seed, int transposed, int add) {
    xof_state state;
    unsigned int ctr, ctr2;
    int16_t ax[4];
    uint8_t buf[XOF_BLOCKBYTES];

    if (transposed) {
        xof_absorb(&state, seed, i, j);
    } else {
        xof_absorb(&state, seed, j, i);
    }

    ctr = 0;
    ctr2 = 0;
    do {
        xof_squeezeblocks(buf, 1, &state);
        unsigned int pos;
        uint16_t val0, val1;

        pos = 0;
        while (ctr < MLKEM_N && pos + 3 <= XOF_BLOCKBYTES) {
            val0 = ((buf[pos + 0] >> 0) | ((uint16_t)buf[pos + 1] << 8)) & 0xFFF;
            val1 = ((buf[pos + 1] >> 4) | ((uint16_t)buf[pos + 2] << 4)) & 0xFFF;
            pos += 3;

            if (val0 < MLKEM_Q) {
                ax[ctr2] = val0;
                ctr++;
                ctr2++;
            }
            if (ctr2 == 4) {
                doublebasemul(r->coeffs + ctr - 4, b->coeffs + ctr - 4, ax, (ctr - 4) / 4, add);
                ctr2 = 0;
            }

            if (ctr < MLKEM_N && val1 < MLKEM_Q) {
                ax[ctr2] = val1;
                ctr++;
                ctr2++;
            }
            if (ctr2 == 4) {
                doublebasemul(r->coeffs + ctr - 4, b->coeffs + ctr - 4, ax, (ctr - 4) / 4, add);
                ctr2 = 0;
            }
        }

    } while (ctr < MLKEM_N);
}

/*************************************************
 * Name:        matacc
 *
 * Description: Multiplies a row of A or A^T, generated on-the-fly,
 *              with a vector of polynomials and accumulates into the result.
 *
 * Arguments:   - poly *r:                    pointer to output polynomial to accumulate in
 *              - polyvec *b:                 pointer to input vector of polynomials to multiply with
 *              - unsigned char i:            byte to indicate the index < MLKEM_K of the row of A or A^T
 *              - const unsigned char *seed:  pointer to the public seed used to generate A
 *              - int transposed:             boolean indicating whether A or A^T is generated
 **************************************************/
void matacc(poly *r, const polyvec *b, unsigned char i, const unsigned char *seed, int transposed) {
    int j = 0;
    matacc_inner(r, &b->vec[j], i, j, seed, transposed, 0);

    for (j = 1; j < MLKEM_K; j++) {
        matacc_inner(r, &b->vec[j], i, j, seed, transposed, 1);
    }
}
