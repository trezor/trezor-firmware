/**
 * Copyright (c) 2017 Saleem Rashid
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, E1PRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#include "base32.h"

static inline void base32_5to8(const uint8_t *in, uint8_t length, uint8_t *out);

void base32_encode_unsafe(const uint8_t *in, size_t inlen, uint8_t *out) {
	uint8_t remainder = inlen % 5;
	size_t limit = inlen - remainder;

	size_t i, j;
	for (i = 0, j = 0; i < limit; i += 5, j += 8) {
		base32_5to8(&in[i], 5, &out[j]);
	}

	if (remainder) base32_5to8(&in[i], remainder, &out[j]);
}

void base32_5to8(const uint8_t *in, uint8_t length, uint8_t *out) {
	if (length >= 1) {
		out[0]  = (in[0] >> 3);
		out[1]  = (in[0] &  7) << 2;
	}

	if (length >= 2) {
		out[1] |= (in[1] >> 6);
		out[2]  = (in[1] >> 1) & 31;
		out[3]  = (in[1] &  1) << 4;
	}

	if (length >= 3) {
		out[3] |= (in[2] >> 4);
		out[4]  = (in[2] & 15) << 1;
	}

	if (length >= 4) {
		out[4] |= (in[3] >> 7);
		out[5]  = (in[3] >> 2) & 31;
		out[6]  = (in[3] &  3) << 3;
	}

	if (length >= 5) {
		out[6] |= (in[4] >> 5);
		out[7]  = (in[4] & 31);
	}
}
