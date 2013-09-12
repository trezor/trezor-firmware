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
#include "ecdsa.h"

// vectors from https://en.bitcoin.it/wiki/BIP_0032_TestVectors

const char *privs[] = {
"\xe8\xf3\x2e\x72\x3d\xec\xf4\x05\x1a\xef\xac\x8e\x2c\x93\xc9\xc5\xb2\x14\x31\x38\x17\xcd\xb0\x1a\x14\x94\xb9\x17\xc8\x43\x6b\x35",
"\xed\xb2\xe1\x4f\x9e\xe7\x7d\x26\xdd\x93\xb4\xec\xed\xe8\xd1\x6e\xd4\x08\xce\x14\x9b\x6c\xd8\x0b\x07\x15\xa2\xd9\x11\xa0\xaf\xea",
"\x3c\x6c\xb8\xd0\xf6\xa2\x64\xc9\x1e\xa8\xb5\x03\x0f\xad\xaa\x8e\x53\x8b\x02\x0f\x0a\x38\x74\x21\xa1\x2d\xe9\x31\x9d\xc9\x33\x68",
"\xcb\xce\x0d\x71\x9e\xcf\x74\x31\xd8\x8e\x6a\x89\xfa\x14\x83\xe0\x2e\x35\x09\x2a\xf6\x0c\x04\x2b\x1d\xf2\xff\x59\xfa\x42\x4d\xca",
"\x0f\x47\x92\x45\xfb\x19\xa3\x8a\x19\x54\xc5\xc7\xc0\xeb\xab\x2f\x9b\xdf\xd9\x6a\x17\x56\x3e\xf2\x8a\x6a\x4b\x1a\x2a\x76\x4e\xf4",
"\x47\x1b\x76\xe3\x89\xe5\x28\xd6\xde\x6d\x81\x68\x57\xe0\x12\xc5\x45\x50\x51\xca\xd6\x66\x08\x50\xe5\x83\x72\xa6\xc3\xe6\xe7\xc8",
};

const char *pubs[] = {
"0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2",
"035a784662a4a20a65bf6aab9ae98a6c068a81c52e4b032c0fb5400c706cfccc56",
"03501e454bf00751f24b1b489aa925215d66af2234e3891c3b21a52bedb3cd711c",
"0357bfe1e341d01c69fe5654309956cbea516822fba8a601743a012a7896ee8dc2",
"02e8445082a72f29b75ca48748a914df60622a609cacfce8ed0e35804560741d29",
"022a471424da5e657499d1ff51cb43c47481a03b1e77f951fe64cec9f5a48f7011",
};

int main()
{
	int i, k;
	uint8_t pub[33];

	for (k = 0; k < 6; k++) {
		ecdsa_get_public_key_compressed((uint8_t *)privs[k], pub);
		printf("got      : "); for (i = 0; i < 33; i++) printf("%02x", pub[i]); printf("\n");
		printf("expected : %s\n", pubs[k]);
	}

	return 0;
}
