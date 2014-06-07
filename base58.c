/**
 * Copyright (c) 2013-2014 Tomas Dzetkulic
 * Copyright (c) 2013-2014 Pavol Rusnak
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

#include <string.h>
#include "base58.h"
#include "sha2.h"

int base58_encode_check(const uint8_t *data, int len, char *str)
{
	int outlen;
	switch (len) {
		case 78: // xpub/xprv 78
			outlen = 111;
			break;
		case 34: // WIF privkey 1+32+1
			outlen = 52;
			break;
		case 21: // address 1+20
			outlen = 34;
			break;
		default:
			return 0;
	}
	uint8_t mydata[82], hash[32];
	sha256_Raw(data, len, hash);
	sha256_Raw(hash, 32, hash);
	memcpy(mydata, data, len);
	memcpy(mydata + len, hash, 4); // checksum
	uint32_t rem, tmp;
	const char code[] = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
	int i, j;
	for (j = 0; j < outlen; j++) {
		rem = mydata[0] % 58;
		mydata[0] /= 58;
		for (i = 1; i < len + 4; i++) {
			tmp = rem * 24 + mydata[i]; // 2^8 == 4*58 + 24
			mydata[i] = rem * 4 + (tmp / 58);
			rem = tmp % 58;
		}
		str[j] = code[rem];
	}
	// remove duplicite 1s at the end
	while (outlen > 1 && str[outlen - 1] == code[0] && str[outlen - 2] == code[0]) {
		outlen--;
	}
	str[outlen] = 0;
	char s;
	// reverse string
	for (i = 0; i < outlen / 2; i++) {
		s = str[i];
		str[i] = str[outlen - 1 - i];
		str[outlen - 1 - i] = s;
	}
	return outlen;
}

int base58_decode_check(const char *str, uint8_t *data)
{
	const char decode[] = {
		-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
		-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
		-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1, -1,
		-1, -1, -1, -1, -1, -1, -1, -1, -1, -1, 0, 1, 2, 3,
		4, 5, 6, 7, 8, -1, -1, -1, -1, -1, -1, -1, 9, 10, 11,
		12, 13, 14, 15, 16, -1, 17, 18, 19, 20, 21, -1, 22,
		23, 24, 25, 26, 27, 28, 29, 30, 31, 32, -1, -1, -1,
		-1, -1, -1, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
		43, -1, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54,
		55, 56, 57
	};
	int outlen;
	switch (strlen(str)) {
		case 111: // xpub/xprv
			outlen = 78;
			break;
		case 52: // WIF privkey
			outlen = 35;
			break;
		case 27: // address
		case 28:
		case 29:
		case 30:
		case 31:
		case 32:
		case 33:
		case 34:
			outlen = 21;
			break;
		default:
			return 0;
	}
	uint8_t mydata[82], hash[32];
	memset(mydata, 0, sizeof(mydata));
	int i, j, k;
	while (*str) {
		i = *str;
		if (i < 0 || i >= (int)sizeof(decode)) { // invalid character
			return 0;
		}
		k = decode[i];
		if (k == -1) { // invalid character
			return 0;
		}
		for (j = outlen + 4 - 1; j >= 0; j--) {
			k += mydata[j] * 58;
			mydata[j] = k & 0xFF;
			k >>= 8;
		}
		str++;
	}
	sha256_Raw(mydata, outlen, hash);
	sha256_Raw(hash, 32, hash);
	if (memcmp(mydata + outlen, hash, 4)) { // wrong checksum
		return 0;
	}
	memcpy(data, mydata, outlen);
	return outlen;
}
