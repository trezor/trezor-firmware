/**
 * Copyright (c) 2013 Tomas Dzetkulic
 * Copyright (c) 2013 Pavol Rusnak
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
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#include <stdint.h>
#include "aux.h"

// process sha256 chunk (of length 64 bytes)
void process_chunk(const uint8_t *chunk, uint32_t *hash)
{
	static const uint32_t k0[64] = {
		0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
		0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
		0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
		0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
		0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
		0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
		0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
		0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
	};
	uint32_t i, s0, s1, a, b, c, d, e, f, g, h, ch, temp, maj, w[64];

	for (i = 0;i < 16;i++) {
		w[i] = read_be(chunk + 4 * i);
	}
	for (;i < 64;i++) {
		s0 = ror(w[i-15], 7) ^ ror(w[i-15], 18) ^ (w[i-15]>>3);
		s1 = ror(w[i-2], 17) ^ ror(w[i-2], 19) ^ (w[i-2]>>10);
		w[i] = w[i-16] + s0 + w[i-7] + s1;
	}
	a = hash[0];
	b = hash[1];
	c = hash[2];
	d = hash[3];
	e = hash[4];
	f = hash[5];
	g = hash[6];
	h = hash[7];
	for (i = 0;i < 64;i++) {
		s1 = ror(e, 6) ^ ror(e, 11) ^ ror(e, 25);
		ch = (e & f) ^ ((~ e) & g);
		temp = h + s1 + ch + k0[i] + w[i];
		d = d + temp;
		s0 = ror(a, 2) ^ ror(a, 13) ^ ror(a, 22);
		maj = (a & (b ^ c)) ^ (b & c);
		temp = temp + s0 + maj;
		h = g;
		g = f;
		f = e;
		e = d;
		d = c;
		c = b;
		b = a;
		a = temp;
	}
	hash[0] += a;
	hash[1] += b;
	hash[2] += c;
	hash[3] += d;
	hash[4] += e;
	hash[5] += f;
	hash[6] += g;
	hash[7] += h;
}

// compute sha256 of a message with len length in bytes
// hash is a pointer to at least 32byte array
void sha256(const uint8_t *msg, const uint32_t len, uint8_t *hash)
{
	// initial hash vales
	static const uint32_t h0[8] = {
		0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
	};
	uint32_t l = len, i, h[8];
	uint8_t last_chunks[128]; //for storing last 1 or 2 chunks
	for (i = 0;i < 8; i++) {
		h[i] = h0[i];
	}
	// process complete message chunks
	while (l >= 64) {
		process_chunk(msg, h);
		l -= 64;
		msg += 64;
	}
	// process rest of the message
	for (i = 0;i < l; i++) {
		last_chunks[i] = msg[i];
	}
	// add '1' bit
	last_chunks[i++] = 0x80;
	// pad message with zeroes
	for (;(i & 63) != 56; i++) {
		last_chunks[i]=0;
	}
	// add message length in bits
	l = 8 * len;
	write_be(last_chunks + i, 0);
	write_be(last_chunks + i + 4, l);
	// process remaining 1 or 2 chunks
	process_chunk(last_chunks, h);
	if (i > 64) {
		process_chunk(last_chunks + 64, h);
	}
	// write the result
	for (i = 0;i < 8; i++) {
		write_be(hash + 4 * i, h[i]);
	}
}
