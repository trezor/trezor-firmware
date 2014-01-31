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

#include <check.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#include "aes.h"
#include "bignum.h"
#include "bip32.h"
#include "bip39.h"
#include "ecdsa.h"
#include "pbkdf2.h"
#include "sha2.h"

uint8_t *fromhex(const char *str)
{
	static uint8_t buf[128];
	uint8_t c;
	size_t i;
	for (i = 0; i < strlen(str) / 2; i++) {
		c = 0;
		if (str[i*2] >= '0' && str[i*2] <= '9') c += (str[i*2] - '0') << 4;
		if (str[i*2] >= 'a' && str[i*2] <= 'f') c += (10 + str[i*2] - 'a') << 4;
		if (str[i*2+1] >= '0' && str[i*2+1] <= '9') c += (str[i*2+1] - '0');
		if (str[i*2+1] >= 'a' && str[i*2+1] <= 'f') c += (10 + str[i*2+1] - 'a');
		buf[i] = c;
	}
	return buf;
}

inline char *tohex(const uint8_t *bin, size_t l)
{
	char *buf = (char *)malloc(l * 2 + 1);
	static char digits[] = "0123456789abcdef";
	size_t i;
	for (i = 0; i < l; i++) {
		buf[i*2  ] = digits[(bin[i] >> 4) & 0xF];
		buf[i*2+1] = digits[bin[i] & 0xF];
	}
	buf[l * 2] = 0;
	return buf;
}

#define _ck_assert_mem(X, Y, L, OP) do { \
  const void* _ck_x = (X); \
  const void* _ck_y = (Y); \
  size_t _ck_l = (L); \
  ck_assert_msg(0 OP memcmp(_ck_y, _ck_x, _ck_l), \
    "Assertion '"#X#OP#Y"' failed: "#X"==\"%s\", "#Y"==\"%s\"", tohex(_ck_x, _ck_l), tohex(_ck_y, _ck_l)); \
} while (0)
#define ck_assert_mem_eq(X, Y, L) _ck_assert_mem(X, Y, L, ==)
#define ck_assert_mem_ne(X, Y, L) _ck_assert_mem(X, Y, L, !=)

// test vector 1 from https://en.bitcoin.it/wiki/BIP_0032_TestVectors
START_TEST(test_bip32_vector_1)
{
	HDNode node;

	// init m
	hdnode_from_seed(0x00, 0x0488B21E, fromhex("000102030405060708090a0b0c0d0e0f"), 16, &node);

	// [Chain m]
	ck_assert_int_eq(node.fingerprint, 0x00000000);
	ck_assert_mem_eq(node.chain_code,  fromhex("873dff81c02f525623fd1fe5167eac3a55a049de3d314bb42ee227ffed37d508"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("e8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2"), 33);
	ck_assert_str_eq(node.address,     "15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma");

	// [Chain m/0']
	hdnode_private_ckd_prime(&node, 0);
	ck_assert_int_eq(node.fingerprint, 0x3442193e);
	ck_assert_mem_eq(node.chain_code,  fromhex("47fdacbd0f1097043b78c63c20c34ef4ed9a111d980047ad16282c7ae6236141"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("edb2e14f9ee77d26dd93b4ecede8d16ed408ce149b6cd80b0715a2d911a0afea"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("035a784662a4a20a65bf6aab9ae98a6c068a81c52e4b032c0fb5400c706cfccc56"), 33);
	ck_assert_str_eq(node.address,     "19Q2WoS5hSS6T8GjhK8KZLMgmWaq4neXrh");

	// [Chain m/0'/1]
	hdnode_private_ckd(&node, 1);
	ck_assert_int_eq(node.fingerprint, 0x5c1bd648);
	ck_assert_mem_eq(node.chain_code,  fromhex("2a7857631386ba23dacac34180dd1983734e444fdbf774041578e9b6adb37c19"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("3c6cb8d0f6a264c91ea8b5030fadaa8e538b020f0a387421a12de9319dc93368"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("03501e454bf00751f24b1b489aa925215d66af2234e3891c3b21a52bedb3cd711c"), 33);
	ck_assert_str_eq(node.address,     "1JQheacLPdM5ySCkrZkV66G2ApAXe1mqLj");

	// [Chain m/0'/1/2']
	hdnode_private_ckd_prime(&node, 2);
	ck_assert_int_eq(node.fingerprint, 0xbef5a2f9);
	ck_assert_mem_eq(node.chain_code,  fromhex("04466b9cc8e161e966409ca52986c584f07e9dc81f735db683c3ff6ec7b1503f"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("cbce0d719ecf7431d88e6a89fa1483e02e35092af60c042b1df2ff59fa424dca"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("0357bfe1e341d01c69fe5654309956cbea516822fba8a601743a012a7896ee8dc2"), 33);
	ck_assert_str_eq(node.address,     "1NjxqbA9aZWnh17q1UW3rB4EPu79wDXj7x");

	// [Chain m/0'/1/2'/2]
	hdnode_private_ckd(&node, 2);
	ck_assert_int_eq(node.fingerprint, 0xee7ab90c);
	ck_assert_mem_eq(node.chain_code,  fromhex("cfb71883f01676f587d023cc53a35bc7f88f724b1f8c2892ac1275ac822a3edd"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("0f479245fb19a38a1954c5c7c0ebab2f9bdfd96a17563ef28a6a4b1a2a764ef4"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("02e8445082a72f29b75ca48748a914df60622a609cacfce8ed0e35804560741d29"), 33);
	ck_assert_str_eq(node.address,     "1LjmJcdPnDHhNTUgrWyhLGnRDKxQjoxAgt");

	// [Chain m/0'/1/2'/2/1000000000]
	hdnode_private_ckd(&node, 1000000000);
	ck_assert_int_eq(node.fingerprint, 0xd880d7d8);
	ck_assert_mem_eq(node.chain_code,  fromhex("c783e67b921d2beb8f6b389cc646d7263b4145701dadd2161548a8b078e65e9e"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("471b76e389e528d6de6d816857e012c5455051cad6660850e58372a6c3e6e7c8"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("022a471424da5e657499d1ff51cb43c47481a03b1e77f951fe64cec9f5a48f7011"), 33);
	ck_assert_str_eq(node.address,     "1LZiqrop2HGR4qrH1ULZPyBpU6AUP49Uam");
}
END_TEST

// test vector 2 from https://en.bitcoin.it/wiki/BIP_0032_TestVectors
START_TEST(test_bip32_vector_2)
{
	HDNode node;
	int r;

	// init m
	hdnode_from_seed(0x00, 0x0488B21E, fromhex("fffcf9f6f3f0edeae7e4e1dedbd8d5d2cfccc9c6c3c0bdbab7b4b1aeaba8a5a29f9c999693908d8a8784817e7b7875726f6c696663605d5a5754514e4b484542"), 64, &node);

	// [Chain m]
	ck_assert_int_eq(node.fingerprint, 0x00000000);
	ck_assert_mem_eq(node.chain_code,  fromhex("60499f801b896d83179a4374aeb7822aaeaceaa0db1f85ee3e904c4defbd9689"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("4b03d6fc340455b363f51020ad3ecca4f0850280cf436c70c727923f6db46c3e"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("03cbcaa9c98c877a26977d00825c956a238e8dddfbd322cce4f74b0b5bd6ace4a7"), 33);
	ck_assert_str_eq(node.address,     "1JEoxevbLLG8cVqeoGKQiAwoWbNYSUyYjg");

	// [Chain m/0]
	r = hdnode_private_ckd(&node, 0);
	ck_assert_int_eq(r, 1);
	ck_assert_int_eq(node.fingerprint, 0xbd16bee5);
	ck_assert_mem_eq(node.chain_code,  fromhex("f0909affaa7ee7abe5dd4e100598d4dc53cd709d5a5c2cac40e7412f232f7c9c"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("abe74a98f6c7eabee0428f53798f0ab8aa1bd37873999041703c742f15ac7e1e"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("02fc9e5af0ac8d9b3cecfe2a888e2117ba3d089d8585886c9c826b6b22a98d12ea"), 33);
	ck_assert_str_eq(node.address,     "19EuDJdgfRkwCmRzbzVBHZWQG9QNWhftbZ");

	// [Chain m/0/2147483647']
	r = hdnode_private_ckd_prime(&node, 2147483647);
	ck_assert_int_eq(r, 1);
	ck_assert_int_eq(node.fingerprint, 0x5a61ff8e);
	ck_assert_mem_eq(node.chain_code,  fromhex("be17a268474a6bb9c61e1d720cf6215e2a88c5406c4aee7b38547f585c9a37d9"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("877c779ad9687164e9c2f4f0f4ff0340814392330693ce95a58fe18fd52e6e93"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("03c01e7425647bdefa82b12d9bad5e3e6865bee0502694b94ca58b666abc0a5c3b"), 33);
	ck_assert_str_eq(node.address,     "1Lke9bXGhn5VPrBuXgN12uGUphrttUErmk");

	// [Chain m/0/2147483647'/1]
	r = hdnode_private_ckd(&node, 1);
	ck_assert_int_eq(r, 1);
	ck_assert_int_eq(node.fingerprint, 0xd8ab4937);
	ck_assert_mem_eq(node.chain_code,  fromhex("f366f48f1ea9f2d1d3fe958c95ca84ea18e4c4ddb9366c336c927eb246fb38cb"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("704addf544a06e5ee4bea37098463c23613da32020d604506da8c0518e1da4b7"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("03a7d1d856deb74c508e05031f9895dab54626251b3806e16b4bd12e781a7df5b9"), 33);
	ck_assert_str_eq(node.address,     "1BxrAr2pHpeBheusmd6fHDP2tSLAUa3qsW");

	// [Chain m/0/2147483647'/1/2147483646']
	r = hdnode_private_ckd_prime(&node, 2147483646);
	ck_assert_int_eq(r, 1);
	ck_assert_int_eq(node.fingerprint, 0x78412e3a);
	ck_assert_mem_eq(node.chain_code,  fromhex("637807030d55d01f9a0cb3a7839515d796bd07706386a6eddf06cc29a65a0e29"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("f1c7c871a54a804afe328b4c83a1c33b8e5ff48f5087273f04efa83b247d6a2d"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("02d2b36900396c9282fa14628566582f206a5dd0bcc8d5e892611806cafb0301f0"), 33);
	ck_assert_str_eq(node.address,     "15XVotxCAV7sRx1PSCkQNsGw3W9jT9A94R");

	// [Chain m/0/2147483647'/1/2147483646'/2]
	r = hdnode_private_ckd(&node, 2);
	ck_assert_int_eq(r, 1);
	ck_assert_int_eq(node.fingerprint, 0x31a507b8);
	ck_assert_mem_eq(node.chain_code,  fromhex("9452b549be8cea3ecb7a84bec10dcfd94afe4d129ebfd3b3cb58eedf394ed271"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("bb7d39bdb83ecf58f2fd82b6d918341cbef428661ef01ab97c28a4842125ac23"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("024d902e1a2fc7a8755ab5b694c575fce742c48d9ff192e63df5193e4c7afe1f9c"), 33);
	ck_assert_str_eq(node.address,     "14UKfRV9ZPUp6ZC9PLhqbRtxdihW9em3xt");

	// init m
	hdnode_from_seed(0x00, 0x0488B21E, fromhex("fffcf9f6f3f0edeae7e4e1dedbd8d5d2cfccc9c6c3c0bdbab7b4b1aeaba8a5a29f9c999693908d8a8784817e7b7875726f6c696663605d5a5754514e4b484542"), 64, &node);

	// test public derivation
	// [Chain m/0]
	r = hdnode_public_ckd(&node, 0);
	ck_assert_int_eq(r, 1);
	ck_assert_int_eq(node.fingerprint, 0xbd16bee5);
	ck_assert_mem_eq(node.chain_code,  fromhex("f0909affaa7ee7abe5dd4e100598d4dc53cd709d5a5c2cac40e7412f232f7c9c"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("0000000000000000000000000000000000000000000000000000000000000000"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("02fc9e5af0ac8d9b3cecfe2a888e2117ba3d089d8585886c9c826b6b22a98d12ea"), 33);
	ck_assert_str_eq(node.address,     "19EuDJdgfRkwCmRzbzVBHZWQG9QNWhftbZ");
}
END_TEST

int generate_k_rfc6979(bignum256 *secret, const uint8_t *priv_key, const uint8_t *hash);

#define test_deterministic(KEY, MSG, K) do { \
	SHA256_Raw((uint8_t *)MSG, strlen(MSG), buf); \
	res = generate_k_rfc6979(&k, fromhex(KEY), buf); \
	ck_assert_int_eq(res, 0); \
	bn_write_be(&k, buf); \
	ck_assert_mem_eq(buf, fromhex(K), 32); \
} while (0)

START_TEST(test_rfc6979)
{
	int res;
	bignum256 k;
	uint8_t buf[32];

	test_deterministic("cca9fbcc1b41e5a95d369eaa6ddcff73b61a4efaa279cfc6567e8daa39cbaf50", "sample", "2df40ca70e639d89528a6b670d9d48d9165fdc0febc0974056bdce192b8e16a3");
	test_deterministic("0000000000000000000000000000000000000000000000000000000000000001", "Satoshi Nakamoto", "8f8a276c19f4149656b280621e358cce24f5f52542772691ee69063b74f15d15");
	test_deterministic("fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364140", "Satoshi Nakamoto", "33a19b60e25fb6f4435af53a3d42d493644827367e6453928554f43e49aa6f90");
	test_deterministic("f8b8af8ce3c7cca5e300d33939540c10d45ce001b8f252bfbc57ba0342904181", "Alan Turing", "525a82b70e67874398067543fd84c83d30c175fdc45fdeee082fe13b1d7cfdf1");
	test_deterministic("0000000000000000000000000000000000000000000000000000000000000001", "All those moments will be lost in time, like tears in rain. Time to die...", "38aa22d72376b4dbc472e06c3ba403ee0a394da63fc58d88686c611aba98d6b3");
	test_deterministic("e91671c46231f833a6406ccbea0e3e392c76c167bac1cb013f6f1013980455c2", "There is a computer disease that anybody who works with computers knows about. It's a very serious disease and it interferes completely with the work. The trouble with computers is that you 'play' with them!", "1f4b84c23a86a221d233f2521be018d9318639d5b8bbd6374a8a59232d16ad3d");
}
END_TEST

START_TEST(test_sign_speed)
{
	uint8_t sig[64], priv_key[32], msg[256];
	int i, res;

	for (i = 0; i < sizeof(msg); i++) {
		msg[i] = i * 1103515245;
	}

	clock_t t = clock();

	memcpy(priv_key, fromhex("c55ece858b0ddd5263f96810fe14437cd3b5e1fbd7c6a2ec1e031f05e86d8bd5"), 32);
	for (i = 0 ; i < 250; i++) {
		res = ecdsa_sign(priv_key, msg, sizeof(msg), sig);
		ck_assert_int_eq(res, 0);
	}

	memcpy(priv_key, fromhex("509a0382ff5da48e402967a671bdcde70046d07f0df52cff12e8e3883b426a0a"), 32);
	for (i = 0 ; i < 250; i++) {
		res = ecdsa_sign(priv_key, msg, sizeof(msg), sig);
		ck_assert_int_eq(res, 0);
	}

	printf("Signing speed: %0.2f sig/s\n", 500.0f / ((float)(clock() - t) / CLOCKS_PER_SEC));
}
END_TEST

START_TEST(test_verify_speed)
{
	uint8_t sig[64], pub_key33[33], pub_key65[65], msg[256];
	int i, res;

	for (i = 0; i < sizeof(msg); i++) {
		msg[i] = i * 1103515245;
	}

	clock_t t = clock();

	memcpy(sig, fromhex("88dc0db6bc5efa762e75fbcc802af69b9f1fcdbdffce748d403f687f855556e610ee8035414099ac7d89cff88a3fa246d332dfa3c78d82c801394112dda039c2"), 64);
	memcpy(pub_key33, fromhex("024054fd18aeb277aeedea01d3f3986ff4e5be18092a04339dcf4e524e2c0a0974"), 33);
	memcpy(pub_key65, fromhex("044054fd18aeb277aeedea01d3f3986ff4e5be18092a04339dcf4e524e2c0a09746c7083ed2097011b1223a17a644e81f59aa3de22dac119fd980b36a8ff29a244"), 65);

	for (i = 0 ; i < 50; i++) {
		res = ecdsa_verify(pub_key65, sig, msg, sizeof(msg));
		ck_assert_int_eq(res, 0);
		res = ecdsa_verify(pub_key33, sig, msg, sizeof(msg));
		ck_assert_int_eq(res, 0);
	}

	memcpy(sig, fromhex("067040a2adb3d9deefeef95dae86f69671968a0b90ee72c2eab54369612fd524eb6756c5a1bb662f1175a5fa888763cddc3a07b8a045ef6ab358d8d5d1a9a745"), 64);
	memcpy(pub_key33, fromhex("03ff45a5561a76be930358457d113f25fac790794ec70317eff3b97d7080d45719"), 33);
	memcpy(pub_key65, fromhex("04ff45a5561a76be930358457d113f25fac790794ec70317eff3b97d7080d457196235193a15778062ddaa44aef7e6901b781763e52147f2504e268b2d572bf197"), 65);

	for (i = 0 ; i < 50; i++) {
		res = ecdsa_verify(pub_key65, sig, msg, sizeof(msg));
		ck_assert_int_eq(res, 0);
		res = ecdsa_verify(pub_key33, sig, msg, sizeof(msg));
		ck_assert_int_eq(res, 0);
	}

	printf("Verifying speed: %0.2f sig/s\n", 200.0f / ((float)(clock() - t) / CLOCKS_PER_SEC));
}
END_TEST

#define test_aes(KEY, BLKLEN, IN, OUT) do { \
	SHA256_Raw((uint8_t *)KEY, strlen(KEY), key); \
	aes_enc_key(key, 32, &ctx); \
	memcpy(in, fromhex(IN), BLKLEN); \
	aes_enc_blk(in, out, &ctx); \
	ck_assert_mem_eq(out, fromhex(OUT), BLKLEN); \
} while (0)

START_TEST(test_rijndael)
{
	aes_ctx ctx;
	uint8_t key[32], in[32], out[32];

	test_aes("mnemonic", 16, "00000000000000000000000000000000", "a3af8b7d326a2d47bd7576012e07d103");
//	test_aes("mnemonic", 24, "000000000000000000000000000000000000000000000000", "7b8704678f263c316ddd1746d8377a4046a99dd9e5687d59");
//	test_aes("mnemonic", 32, "0000000000000000000000000000000000000000000000000000000000000000", "7c0575db9badc9960441c6b8dcbd5ebdfec522ede5309904b7088d0e77c2bcef");

	test_aes("mnemonic", 16, "686f6a6461686f6a6461686f6a6461686f6a6461", "9c3bb85af2122cc2df449033338beb56");
//	test_aes("mnemonic", 24, "686f6a6461686f6a6461686f6a6461686f6a6461686f6a64", "0d7009c589869eaa1d7398bffc7660cce32207a520d6cafe");
//	test_aes("mnemonic", 32, "686f6a6461686f6a6461686f6a6461686f6a6461686f6a6461686f6a6461686f", "b1a4d05e3827611c5986ea4c207679a6934f20767434218029c4b3b7a53806a3");

	test_aes("mnemonic", 16, "ffffffffffffffffffffffffffffffff", "e720f4474b7dabe382eec0529e2b1128");
//	test_aes("mnemonic", 24, "ffffffffffffffffffffffffffffffffffffffffffffffff", "14dfe4c7a93e14616dce6c793110baee0b8bb404f3bec6c5");
//	test_aes("mnemonic", 32, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", "ccf498fd9a57f872a4d274549fab474cbacdbd9d935ca31b06e3025526a704fb");
}
END_TEST

// test vectors from http://stackoverflow.com/questions/15593184/pbkdf2-hmac-sha-512-test-vectors
START_TEST(test_pbkdf2)
{
	uint8_t k[64], s[64];

	strcpy((char *)s, "salt");
	pbkdf2((uint8_t *)"password", 8, s, 4, 1, k, 64);
	ck_assert_mem_eq(k, fromhex("867f70cf1ade02cff3752599a3a53dc4af34c7a669815ae5d513554e1c8cf252c02d470a285a0501bad999bfe943c08f050235d7d68b1da55e63f73b60a57fce"), 64);

	strcpy((char *)s, "salt");
	pbkdf2((uint8_t *)"password", 8, s, 4, 2, k, 64);
	ck_assert_mem_eq(k, fromhex("e1d9c16aa681708a45f5c7c4e215ceb66e011a2e9f0040713f18aefdb866d53cf76cab2868a39b9f7840edce4fef5a82be67335c77a6068e04112754f27ccf4e"), 64);

	strcpy((char *)s, "salt");
	pbkdf2((uint8_t *)"password", 8, s, 4, 4096, k, 64);
	ck_assert_mem_eq(k, fromhex("d197b1b33db0143e018b12f3d1d1479e6cdebdcc97c5c0f87f6902e072f457b5143f30602641b3d55cd335988cb36b84376060ecd532e039b742a239434af2d5"), 64);

	strcpy((char *)s, "saltSALTsaltSALTsaltSALTsaltSALTsalt");
	pbkdf2((uint8_t *)"passwordPASSWORDpassword", 3*8, s, 9*4, 4096, k, 64);
	ck_assert_mem_eq(k, fromhex("8c0511f4c6e597c6ac6315d8f0362e225f3c501495ba23b868c005174dc4ee71115b59f9e60cd9532fa33e0f75aefe30225c583a186cd82bd4daea9724a3d3b8"), 64);
}
END_TEST

START_TEST(test_mnemonic)
{
	static const char *vectors[] = {
		"00000000000000000000000000000000",
		"abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
		"c55257c360c07c72029aebc1b53c05ed0362ada38ead3e3e9efa3708e53495531f09a6987599d18264c1e1c92f2cf141630c7a3c4ab7c81b2f001698e7463b04",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"legal winner thank year wave sausage worth useful legal winner thank yellow",
		"2e8905819b8723fe2c1d161860e5ee1830318dbf49a83bd451cfb8440c28bd6fa457fe1296106559a3c80937a1c1069be3a3a5bd381ee6260e8d9739fce1f607",
		"80808080808080808080808080808080",
		"letter advice cage absurd amount doctor acoustic avoid letter advice cage above",
		"d71de856f81a8acc65e6fc851a38d4d7ec216fd0796d0a6827a3ad6ed5511a30fa280f12eb2e47ed2ac03b5c462a0358d18d69fe4f985ec81778c1b370b652a8",
		"ffffffffffffffffffffffffffffffff",
		"zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong",
		"ac27495480225222079d7be181583751e86f571027b0497b5b5d11218e0a8a13332572917f0f8e5a589620c6f15b11c61dee327651a14c34e18231052e48c069",
		"000000000000000000000000000000000000000000000000",
		"abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon agent",
		"035895f2f481b1b0f01fcf8c289c794660b289981a78f8106447707fdd9666ca06da5a9a565181599b79f53b844d8a71dd9f439c52a3d7b3e8a79c906ac845fa",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"legal winner thank year wave sausage worth useful legal winner thank year wave sausage worth useful legal will",
		"f2b94508732bcbacbcc020faefecfc89feafa6649a5491b8c952cede496c214a0c7b3c392d168748f2d4a612bada0753b52a1c7ac53c1e93abd5c6320b9e95dd",
		"808080808080808080808080808080808080808080808080",
		"letter advice cage absurd amount doctor acoustic avoid letter advice cage absurd amount doctor acoustic avoid letter always",
		"107d7c02a5aa6f38c58083ff74f04c607c2d2c0ecc55501dadd72d025b751bc27fe913ffb796f841c49b1d33b610cf0e91d3aa239027f5e99fe4ce9e5088cd65",
		"ffffffffffffffffffffffffffffffffffffffffffffffff",
		"zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo when",
		"0cd6e5d827bb62eb8fc1e262254223817fd068a74b5b449cc2f667c3f1f985a76379b43348d952e2265b4cd129090758b3e3c2c49103b5051aac2eaeb890a528",
		"0000000000000000000000000000000000000000000000000000000000000000",
		"abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art",
		"bda85446c68413707090a52022edd26a1c9462295029f2e60cd7c4f2bbd3097170af7a4d73245cafa9c3cca8d561a7c3de6f5d4a10be8ed2a5e608d68f92fcc8",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"legal winner thank year wave sausage worth useful legal winner thank year wave sausage worth useful legal winner thank year wave sausage worth title",
		"bc09fca1804f7e69da93c2f2028eb238c227f2e9dda30cd63699232578480a4021b146ad717fbb7e451ce9eb835f43620bf5c514db0f8add49f5d121449d3e87",
		"8080808080808080808080808080808080808080808080808080808080808080",
		"letter advice cage absurd amount doctor acoustic avoid letter advice cage absurd amount doctor acoustic avoid letter advice cage absurd amount doctor acoustic bless",
		"c0c519bd0e91a2ed54357d9d1ebef6f5af218a153624cf4f2da911a0ed8f7a09e2ef61af0aca007096df430022f7a2b6fb91661a9589097069720d015e4e982f",
		"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
		"zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo vote",
		"dd48c104698c30cfe2b6142103248622fb7bb0ff692eebb00089b32d22484e1613912f0a5b694407be899ffd31ed3992c456cdf60f5d4564b8ba3f05a69890ad",
		"77c2b00716cec7213839159e404db50d",
		"jelly better achieve collect unaware mountain thought cargo oxygen act hood bridge",
		"b5b6d0127db1a9d2226af0c3346031d77af31e918dba64287a1b44b8ebf63cdd52676f672a290aae502472cf2d602c051f3e6f18055e84e4c43897fc4e51a6ff",
		"b63a9c59a6e641f288ebc103017f1da9f8290b3da6bdef7b",
		"renew stay biology evidence goat welcome casual join adapt armor shuffle fault little machine walk stumble urge swap",
		"9248d83e06f4cd98debf5b6f010542760df925ce46cf38a1bdb4e4de7d21f5c39366941c69e1bdbf2966e0f6e6dbece898a0e2f0a4c2b3e640953dfe8b7bbdc5",
		"3e141609b97933b66a060dcddc71fad1d91677db872031e85f4c015c5e7e8982",
		"dignity pass list indicate nasty swamp pool script soccer toe leaf photo multiply desk host tomato cradle drill spread actor shine dismiss champion exotic",
		"ff7f3184df8696d8bef94b6c03114dbee0ef89ff938712301d27ed8336ca89ef9635da20af07d4175f2bf5f3de130f39c9d9e8dd0472489c19b1a020a940da67",
		"0460ef47585604c5660618db2e6a7e7f",
		"afford alter spike radar gate glance object seek swamp infant panel yellow",
		"65f93a9f36b6c85cbe634ffc1f99f2b82cbb10b31edc7f087b4f6cb9e976e9faf76ff41f8f27c99afdf38f7a303ba1136ee48a4c1e7fcd3dba7aa876113a36e4",
		"72f60ebac5dd8add8d2a25a797102c3ce21bc029c200076f",
		"indicate race push merry suffer human cruise dwarf pole review arch keep canvas theme poem divorce alter left",
		"3bbf9daa0dfad8229786ace5ddb4e00fa98a044ae4c4975ffd5e094dba9e0bb289349dbe2091761f30f382d4e35c4a670ee8ab50758d2c55881be69e327117ba",
		"2c85efc7f24ee4573d2b81a6ec66cee209b2dcbd09d8eddc51e0215b0b68e416",
		"clutch control vehicle tonight unusual clog visa ice plunge glimpse recipe series open hour vintage deposit universe tip job dress radar refuse motion taste",
		"fe908f96f46668b2d5b37d82f558c77ed0d69dd0e7e043a5b0511c48c2f1064694a956f86360c93dd04052a8899497ce9e985ebe0c8c52b955e6ae86d4ff4449",
		"eaebabb2383351fd31d703840b32e9e2",
		"turtle front uncle idea crush write shrug there lottery flower risk shell",
		"bdfb76a0759f301b0b899a1e3985227e53b3f51e67e3f2a65363caedf3e32fde42a66c404f18d7b05818c95ef3ca1e5146646856c461c073169467511680876c",
		"7ac45cfe7722ee6c7ba84fbc2d5bd61b45cb2fe5eb65aa78",
		"kiss carry display unusual confirm curtain upgrade antique rotate hello void custom frequent obey nut hole price segment",
		"ed56ff6c833c07982eb7119a8f48fd363c4a9b1601cd2de736b01045c5eb8ab4f57b079403485d1c4924f0790dc10a971763337cb9f9c62226f64fff26397c79",
		"4fa1a8bc3e6d80ee1316050e862c1812031493212b7ec3f3bb1b08f168cabeef",
		"exile ask congress lamp submit jacket era scheme attend cousin alcohol catch course end lucky hurt sentence oven short ball bird grab wing top",
		"095ee6f817b4c2cb30a5a797360a81a40ab0f9a4e25ecd672a3f58a0b5ba0687c096a6b14d2c0deb3bdefce4f61d01ae07417d502429352e27695163f7447a8c",
		"18ab19a9f54a9274f03e5209a2ac8a91",
		"board flee heavy tunnel powder denial science ski answer betray cargo cat",
		"6eff1bb21562918509c73cb990260db07c0ce34ff0e3cc4a8cb3276129fbcb300bddfe005831350efd633909f476c45c88253276d9fd0df6ef48609e8bb7dca8",
		"18a2e1d81b8ecfb2a333adcb0c17a5b9eb76cc5d05db91a4",
		"board blade invite damage undo sun mimic interest slam gaze truly inherit resist great inject rocket museum chief",
		"f84521c777a13b61564234bf8f8b62b3afce27fc4062b51bb5e62bdfecb23864ee6ecf07c1d5a97c0834307c5c852d8ceb88e7c97923c0a3b496bedd4e5f88a9",
		"15da872c95a13dd738fbf50e427583ad61f18fd99f628c417a61cf8343c90419",
		"beyond stage sleep clip because twist token leaf atom beauty genius food business side grid unable middle armed observe pair crouch tonight away coconut",
		"b15509eaa2d09d3efd3e006ef42151b30367dc6e3aa5e44caba3fe4d3e352e65101fbdb86a96776b91946ff06f8eac594dc6ee1d3e82a42dfe1b40fef6bcc3fd",
		0,
		0,
		0,
	};

	const char **a, **b, **c, *m;
	uint8_t seed[64];

	a = vectors;
	b = vectors + 1;
	c = vectors + 2;
	while (*a && *b && *c) {
		m = mnemonic_from_data(fromhex(*a), strlen(*a) / 2);
		ck_assert_str_eq(m, *b);
		mnemonic_to_seed(m, "TREZOR", seed);
		ck_assert_mem_eq(seed, fromhex(*c), strlen(*c) / 2);
		a += 3; b += 3; c += 3;
	}
}
END_TEST

START_TEST(test_address)
{
	char address[35];
	uint8_t pub_key[65];

	memcpy(pub_key, fromhex("0226659c1cf7321c178c07437150639ff0c5b7679c7ea195253ed9abda2e081a37"), 33);
	ecdsa_get_address(pub_key,   0, address); ck_assert_str_eq(address, "139MaMHp3Vjo8o4x8N1ZLWEtovLGvBsg6s");
	ecdsa_get_address(pub_key, 111, address); ck_assert_str_eq(address, "mhfJsQNnrXB3uuYZqvywARTDfuvyjg4RBh");
	ecdsa_get_address(pub_key,  52, address); ck_assert_str_eq(address, "MxiimznnxsqMfLKTQBL8Z2PoY9jKpjgkCu");
	ecdsa_get_address(pub_key,  48, address); ck_assert_str_eq(address, "LMNJqZbe89yrPbm7JVzrcXJf28hZ1rKPaH");

	memcpy(pub_key, fromhex("025b1654a0e78d28810094f6c5a96b8efb8a65668b578f170ac2b1f83bc63ba856"), 33);
	ecdsa_get_address(pub_key,   0, address); ck_assert_str_eq(address, "19Ywfm3witp6C1yBMy4NRYHY2347WCRBfQ");
	ecdsa_get_address(pub_key, 111, address); ck_assert_str_eq(address, "mp4txp8vXvFLy8So5Y2kFTVrt2epN6YzdP");
	ecdsa_get_address(pub_key,  52, address); ck_assert_str_eq(address, "N58JsQYveGueiZDgdnNwe4SSkGTAToutAY");
	ecdsa_get_address(pub_key,  48, address); ck_assert_str_eq(address, "LTmtvyMmoZ49SpfLY73fhZMJEFRPdyohKh");

	memcpy(pub_key, fromhex("03433f246a12e6486a51ff08802228c61cf895175a9b49ed4766ea9a9294a3c7fe"), 33);
	ecdsa_get_address(pub_key,   0, address); ck_assert_str_eq(address, "1FWE2bn3MWhc4QidcF6AvEWpK77sSi2cAP");
	ecdsa_get_address(pub_key, 111, address); ck_assert_str_eq(address, "mv2BKes2AY8rqXCFKp4Yk9j9B6iaMfWRLN");
	ecdsa_get_address(pub_key,  52, address); ck_assert_str_eq(address, "NB5bEFH2GtoAawy8t4Qk8kfj3LWvQs3MhB");
	ecdsa_get_address(pub_key,  48, address); ck_assert_str_eq(address, "LZjBHp5sSAwfKDQnnP5UCFaaXKV9YheGxQ");

	memcpy(pub_key, fromhex("03aeb03abeee0f0f8b4f7a5d65ce31f9570cef9f72c2dd8a19b4085a30ab033d48"), 33);
	ecdsa_get_address(pub_key,   0, address); ck_assert_str_eq(address, "1yrZb8dhdevoqpUEGi2tUccUEeiMKeLcs");
	ecdsa_get_address(pub_key, 111, address); ck_assert_str_eq(address, "mgVoreDcWf6BaxJ5wqgQiPpwLEFRLSr8U8");
	ecdsa_get_address(pub_key,  52, address); ck_assert_str_eq(address, "MwZDmEdcd1kVLP4yW62c6zmXCU3mNbveDo");
	ecdsa_get_address(pub_key,  48, address); ck_assert_str_eq(address, "LLCopoSTnHtz4eWdQQhLAVgNgT1zTi4QBK");

	memcpy(pub_key, fromhex("0496e8f2093f018aff6c2e2da5201ee528e2c8accbf9cac51563d33a7bb74a016054201c025e2a5d96b1629b95194e806c63eb96facaedc733b1a4b70ab3b33e3a"), 65);
	ecdsa_get_address(pub_key,   0, address); ck_assert_str_eq(address, "194SZbL75xCCGBbKtMsyWLE5r9s2V6mhVM");
	ecdsa_get_address(pub_key, 111, address); ck_assert_str_eq(address, "moaPreR5tydT3J4wbvrMLFSQi9TjPCiZc6");
	ecdsa_get_address(pub_key,  52, address); ck_assert_str_eq(address, "N4domEq61LHkniqqABCYirNzaPG5NRU8GH");
	ecdsa_get_address(pub_key,  48, address); ck_assert_str_eq(address, "LTHPpodwAcSFWzHV4VsGnMHr4NEJajMnKX");

	memcpy(pub_key, fromhex("0498010f8a687439ff497d3074beb4519754e72c4b6220fb669224749591dde416f3961f8ece18f8689bb32235e436874d2174048b86118a00afbd5a4f33a24f0f"), 65);
	ecdsa_get_address(pub_key,   0, address); ck_assert_str_eq(address, "1A2WfBD4BJFwYHFPc5KgktqtbdJLBuVKc4");
	ecdsa_get_address(pub_key, 111, address); ck_assert_str_eq(address, "mpYTxEJ2zKhCKPj1KeJ4ap4DTcu39T3uzD");
	ecdsa_get_address(pub_key,  52, address); ck_assert_str_eq(address, "N5bsrpi36gMW4pVtsteFyQzoKrhPE7nkxK");
	ecdsa_get_address(pub_key,  48, address); ck_assert_str_eq(address, "LUFTvPWtFxVzo5wYnDJz2uueoqfcMYiuxH");

	memcpy(pub_key, fromhex("04f80490839af36d13701ec3f9eebdac901b51c362119d74553a3c537faff31b17e2a59ebddbdac9e87b816307a7ed5b826b8f40b92719086238e1bebf19b77a4d"), 65);
	ecdsa_get_address(pub_key,   0, address); ck_assert_str_eq(address, "19J81hrPnQxg9UGx45ibTieCkb2ttm8CLL");
	ecdsa_get_address(pub_key, 111, address); ck_assert_str_eq(address, "mop5JkwNbSPvvakZmegyHdrXcadbjLazww");
	ecdsa_get_address(pub_key,  52, address); ck_assert_str_eq(address, "N4sVDMMNho4Eg1XTKu3AgEo7UpRwq3aNbn");
	ecdsa_get_address(pub_key,  48, address); ck_assert_str_eq(address, "LTX5GvADs5CjQGy7EDhtjjhxxoQB2Uhicd");
}
END_TEST

START_TEST(test_address_decode)
{
	int res;
	uint8_t decode[21];
	// byte      0 : address type
	// bytes  1-20 : pubkey hash 160
	res = ecdsa_address_decode("1JwSSubhmg6iPtRjtyqhUYYH7bZg3Lfy1T", decode);
	ck_assert_int_eq(res, 1);
	ck_assert_mem_eq(decode, fromhex("00c4c5d791fcb4654a1ef5e03fe0ad3d9c598f9827"), 21);

	res = ecdsa_address_decode("myTPjxggahXyAzuMcYp5JTkbybANyLsYBW", decode);
	ck_assert_int_eq(res, 1);
	ck_assert_mem_eq(decode, fromhex("6fc4c5d791fcb4654a1ef5e03fe0ad3d9c598f9827"), 21);

	res = ecdsa_address_decode("NEWoeZ6gh4CGvRgFAoAGh4hBqpxizGT6gZ", decode);
	ck_assert_int_eq(res, 1);
	ck_assert_mem_eq(decode, fromhex("34c4c5d791fcb4654a1ef5e03fe0ad3d9c598f9827"), 21);

	res = ecdsa_address_decode("LdAPi7uXrLLmeh7u57pzkZc3KovxEDYRJq", decode);
	ck_assert_int_eq(res, 1);
	ck_assert_mem_eq(decode, fromhex("30c4c5d791fcb4654a1ef5e03fe0ad3d9c598f9827"), 21);

	res = ecdsa_address_decode("1C7zdTfnkzmr13HfA2vNm5SJYRK6nEKyq8", decode);
	ck_assert_int_eq(res, 1);
	ck_assert_mem_eq(decode, fromhex("0079fbfc3f34e7745860d76137da68f362380c606c"), 21);

	res = ecdsa_address_decode("mrdwvWkma2D6n9mGsbtkazedQQuoksnqJV", decode);
	ck_assert_int_eq(res, 1);
	ck_assert_mem_eq(decode, fromhex("6f79fbfc3f34e7745860d76137da68f362380c606c"), 21);

	res = ecdsa_address_decode("N7hMq7AmgNsQXaYARrEwybbDGei9mcPNqr", decode);
	ck_assert_int_eq(res, 1);
	ck_assert_mem_eq(decode, fromhex("3479fbfc3f34e7745860d76137da68f362380c606c"), 21);

	res = ecdsa_address_decode("LWLwtfycqf1uFqypLAug36W4kdgNwrZdNs", decode);
	ck_assert_int_eq(res, 1);
	ck_assert_mem_eq(decode, fromhex("3079fbfc3f34e7745860d76137da68f362380c606c"), 21);

	// invalid char
	res = ecdsa_address_decode("1JwSSubhmg6i000jtyqhUYYH7bZg3Lfy1T", decode);
	ck_assert_int_eq(res, 0);

	// invalid address
	res = ecdsa_address_decode("1111Subhmg6iPtRjtyqhUYYH7bZg3Lfy1T", decode);
	ck_assert_int_eq(res, 0);
}
END_TEST

// define test suite and cases
Suite *test_suite(void)
{
	Suite *s = suite_create("trezor-crypto");
	TCase *tc;

	tc = tcase_create("bip32");
	tcase_add_test(tc, test_bip32_vector_1);
	tcase_add_test(tc, test_bip32_vector_2);
	suite_add_tcase(s, tc);

	tc = tcase_create("rfc6979");
	tcase_add_test(tc, test_rfc6979);
	suite_add_tcase(s, tc);

	tc = tcase_create("speed");
	tcase_add_test(tc, test_sign_speed);
	tcase_add_test(tc, test_verify_speed);
	suite_add_tcase(s, tc);

	tc = tcase_create("address");
	tcase_add_test(tc, test_address);
	suite_add_tcase(s, tc);

	tc = tcase_create("address_decode");
	tcase_add_test(tc, test_address_decode);
	suite_add_tcase(s, tc);

	tc = tcase_create("rijndael");
	tcase_add_test(tc, test_rijndael);
	suite_add_tcase(s, tc);

	tc = tcase_create("pbkdf2");
	tcase_add_test(tc, test_pbkdf2);
	suite_add_tcase(s, tc);

	tc = tcase_create("bip39");
	tcase_add_test(tc, test_mnemonic);
	suite_add_tcase(s, tc);

	return s;
}

// run suite
int main()
{
	int number_failed;
	Suite *s = test_suite();
	SRunner *sr = srunner_create(s);
	srunner_run_all(sr, CK_VERBOSE);
	number_failed = srunner_ntests_failed(sr);
	srunner_free(sr);
	return number_failed;
}
