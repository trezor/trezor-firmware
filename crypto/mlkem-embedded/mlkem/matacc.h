// SPDX-License-Identifier: Apache-2.0
#ifndef MATACC_H
#define MATACC_H

#include "params.h"

#define matacc MLKEM_NAMESPACE(matacc)
void matacc(poly *r, const polyvec *b, unsigned char i, const unsigned char *seed, int transposed);

#endif
