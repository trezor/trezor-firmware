// SPDX-License-Identifier: CC0-1.0
#ifndef KECCAKF1600_H
#define KECCAKF1600_H

#include <stdint.h>

void KeccakF1600_StateExtractBytes(uint64_t *state, unsigned char *data, unsigned int offset, unsigned int length);
void KeccakF1600_StateXORBytes(uint64_t *state, const unsigned char *data, unsigned int offset, unsigned int length);
void KeccakF1600_StatePermute(uint64_t *state);

#endif
