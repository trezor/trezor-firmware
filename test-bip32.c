/**
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

#include "bip32.h"

// test vectors from https://en.bitcoin.it/wiki/BIP_0032_TestVectors

void xprv_print(xprv *in)
{
	int i;

	printf("chain : "); for (i = 0; i < 32; i++) printf("%02x", in->chain_code[i]); printf("\n");
	printf("priv  : "); for (i = 0; i < 32; i++) printf("%02x", in->private_key[i]); printf("\n");
	printf("pub   : "); for (i = 0; i < 33; i++) printf("%02x", in->public_key[i]); printf("\n");
	printf("addr  : "); printf("%s\n", in->address);
	printf("\n");
}

int main()
{
	xprv node;

	xprv_from_seed((uint8_t *)"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f", 16, &node);

	printf("[Chain m] got\n");
	xprv_print(&node);
	printf("[Chain m] expected\n");
	printf("chain : 873dff81c02f525623fd1fe5167eac3a55a049de3d314bb42ee227ffed37d508\n");
	printf("priv  : e8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35\n");
	printf("pub   : 0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2\n");
	printf("addr  : 15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma\n");
	printf("\n");

	xprv_descent_prime(&node, 0);

	printf("[Chain m/0'] got\n");
	xprv_print(&node);
	printf("[Chain m/0'] expected\n");
	printf("chain : 47fdacbd0f1097043b78c63c20c34ef4ed9a111d980047ad16282c7ae6236141\n");
	printf("priv  : edb2e14f9ee77d26dd93b4ecede8d16ed408ce149b6cd80b0715a2d911a0afea\n");
	printf("pub   : 035a784662a4a20a65bf6aab9ae98a6c068a81c52e4b032c0fb5400c706cfccc56\n");
	printf("addr  : 19Q2WoS5hSS6T8GjhK8KZLMgmWaq4neXrh\n");
	printf("\n");

	xprv_descent(&node, 1);

	printf("[Chain m/0'/1] got\n");
	xprv_print(&node);
	printf("[Chain m/0'/1] expected\n");
	printf("chain : 2a7857631386ba23dacac34180dd1983734e444fdbf774041578e9b6adb37c19\n");
	printf("priv  : 3c6cb8d0f6a264c91ea8b5030fadaa8e538b020f0a387421a12de9319dc93368\n");
	printf("pub   : 03501e454bf00751f24b1b489aa925215d66af2234e3891c3b21a52bedb3cd711c\n");
	printf("addr  : 1JQheacLPdM5ySCkrZkV66G2ApAXe1mqLj\n");
	printf("\n");

	return 0;
}
