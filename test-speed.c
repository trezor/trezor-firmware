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

#include <stdio.h>
#include <time.h>

#include "ecdsa.h"
#include "rand.h"

int main()
{
	uint8_t sig[70], priv_key[32], msg[256];
	uint32_t sig_len, i, msg_len;
	int cnt = 0;

	init_rand();

	// random message len between 1 and 256
	msg_len = (random32() & 0xFF) + 1;
	// create random message
	for (i = 0; i < msg_len; i++) {
		msg[i] = random32() & 0xFF;
	}
	// create random privkey
	for (i = 0; i < 8; i++) {
		uint32_t r = random32();
		priv_key[4 * i    ] = r & 0xFF;
		priv_key[4 * i + 1] = (r >> 8) & 0xFF;
		priv_key[4 * i + 2] = (r >> 16) & 0xFF;
		priv_key[4 * i + 3] = (r >> 24) & 0xFF;
	}

	clock_t t = clock();
	for (;;) {
		// use our ECDSA signer to sign the message with the key
		ecdsa_sign(priv_key, msg, msg_len, sig, &sig_len);
		cnt++;
		if ((cnt % 100) == 0) printf("Speed: %f sig/s\n", 1.0f * cnt / ((float)(clock() - t) / CLOCKS_PER_SEC));
	}
	return 0;
}
