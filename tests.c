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
#include <time.h>

#include "blowfish.h"
#include "bignum.h"
#include "bip32.h"
#include "ecdsa.h"
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

char *tohex(const uint8_t *bin, size_t l)
{
	static char buf[257], digits[] = "0123456789abcdef";
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
    "Assertion '"#X#OP#Y"' failed: "#X"==\"%s\"", tohex(_ck_x, _ck_l)); \
} while (0)
#define ck_assert_mem_eq(X, Y, L) _ck_assert_mem(X, Y, L, ==)
#define ck_assert_mem_ne(X, Y, L) _ck_assert_mem(X, Y, L, !=)

// test vector 1 from https://en.bitcoin.it/wiki/BIP_0032_TestVectors
START_TEST(test_bip32_vector_1)
{
	xprv node;

	// init m
	xprv_from_seed(fromhex("000102030405060708090a0b0c0d0e0f"), 16, &node);

	// [Chain m]
	ck_assert_mem_eq(node.chain_code,  fromhex("873dff81c02f525623fd1fe5167eac3a55a049de3d314bb42ee227ffed37d508"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("e8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2"), 33);
	ck_assert_str_eq(node.address,     "15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma");

	// [Chain m/0']
	xprv_descent_prime(&node, 0);
	ck_assert_mem_eq(node.chain_code,  fromhex("47fdacbd0f1097043b78c63c20c34ef4ed9a111d980047ad16282c7ae6236141"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("edb2e14f9ee77d26dd93b4ecede8d16ed408ce149b6cd80b0715a2d911a0afea"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("035a784662a4a20a65bf6aab9ae98a6c068a81c52e4b032c0fb5400c706cfccc56"), 33);
	ck_assert_str_eq(node.address,     "19Q2WoS5hSS6T8GjhK8KZLMgmWaq4neXrh");

	// [Chain m/0'/1]
	xprv_descent(&node, 1);
	ck_assert_mem_eq(node.chain_code,  fromhex("2a7857631386ba23dacac34180dd1983734e444fdbf774041578e9b6adb37c19"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("3c6cb8d0f6a264c91ea8b5030fadaa8e538b020f0a387421a12de9319dc93368"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("03501e454bf00751f24b1b489aa925215d66af2234e3891c3b21a52bedb3cd711c"), 33);
	ck_assert_str_eq(node.address,     "1JQheacLPdM5ySCkrZkV66G2ApAXe1mqLj");

	// [Chain m/0'/1/2']
	xprv_descent_prime(&node, 2);
	ck_assert_mem_eq(node.chain_code,  fromhex("04466b9cc8e161e966409ca52986c584f07e9dc81f735db683c3ff6ec7b1503f"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("cbce0d719ecf7431d88e6a89fa1483e02e35092af60c042b1df2ff59fa424dca"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("0357bfe1e341d01c69fe5654309956cbea516822fba8a601743a012a7896ee8dc2"), 33);
	ck_assert_str_eq(node.address,     "1NjxqbA9aZWnh17q1UW3rB4EPu79wDXj7x");

	// [Chain m/0'/1/2'/2]
	xprv_descent(&node, 2);
	ck_assert_mem_eq(node.chain_code,  fromhex("cfb71883f01676f587d023cc53a35bc7f88f724b1f8c2892ac1275ac822a3edd"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("0f479245fb19a38a1954c5c7c0ebab2f9bdfd96a17563ef28a6a4b1a2a764ef4"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("02e8445082a72f29b75ca48748a914df60622a609cacfce8ed0e35804560741d29"), 33);
	ck_assert_str_eq(node.address,     "1LjmJcdPnDHhNTUgrWyhLGnRDKxQjoxAgt");


	// [Chain m/0'/1/2'/2/1000000000]
	xprv_descent(&node, 1000000000);
	ck_assert_mem_eq(node.chain_code,  fromhex("c783e67b921d2beb8f6b389cc646d7263b4145701dadd2161548a8b078e65e9e"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("471b76e389e528d6de6d816857e012c5455051cad6660850e58372a6c3e6e7c8"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("022a471424da5e657499d1ff51cb43c47481a03b1e77f951fe64cec9f5a48f7011"), 33);
	ck_assert_str_eq(node.address,     "1LZiqrop2HGR4qrH1ULZPyBpU6AUP49Uam");
}
END_TEST

// test vector 2 from https://en.bitcoin.it/wiki/BIP_0032_TestVectors
START_TEST(test_bip32_vector_2)
{
	xprv node;

	// init m
	xprv_from_seed(fromhex("fffcf9f6f3f0edeae7e4e1dedbd8d5d2cfccc9c6c3c0bdbab7b4b1aeaba8a5a29f9c999693908d8a8784817e7b7875726f6c696663605d5a5754514e4b484542"), 64, &node);

	// [Chain m]
	ck_assert_mem_eq(node.chain_code,  fromhex("60499f801b896d83179a4374aeb7822aaeaceaa0db1f85ee3e904c4defbd9689"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("4b03d6fc340455b363f51020ad3ecca4f0850280cf436c70c727923f6db46c3e"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("03cbcaa9c98c877a26977d00825c956a238e8dddfbd322cce4f74b0b5bd6ace4a7"), 33);
	ck_assert_str_eq(node.address,     "1JEoxevbLLG8cVqeoGKQiAwoWbNYSUyYjg");

	// [Chain m/0]
	xprv_descent(&node, 0);
	ck_assert_mem_eq(node.chain_code,  fromhex("f0909affaa7ee7abe5dd4e100598d4dc53cd709d5a5c2cac40e7412f232f7c9c"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("abe74a98f6c7eabee0428f53798f0ab8aa1bd37873999041703c742f15ac7e1e"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("02fc9e5af0ac8d9b3cecfe2a888e2117ba3d089d8585886c9c826b6b22a98d12ea"), 33);
	ck_assert_str_eq(node.address,     "19EuDJdgfRkwCmRzbzVBHZWQG9QNWhftbZ");

	// [Chain m/0/2147483647']
	xprv_descent_prime(&node, 2147483647);
	ck_assert_mem_eq(node.chain_code,  fromhex("be17a268474a6bb9c61e1d720cf6215e2a88c5406c4aee7b38547f585c9a37d9"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("877c779ad9687164e9c2f4f0f4ff0340814392330693ce95a58fe18fd52e6e93"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("03c01e7425647bdefa82b12d9bad5e3e6865bee0502694b94ca58b666abc0a5c3b"), 33);
	ck_assert_str_eq(node.address,     "1Lke9bXGhn5VPrBuXgN12uGUphrttUErmk");

	// [Chain m/0/2147483647'/1]
	xprv_descent(&node, 1);
	ck_assert_mem_eq(node.chain_code,  fromhex("f366f48f1ea9f2d1d3fe958c95ca84ea18e4c4ddb9366c336c927eb246fb38cb"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("704addf544a06e5ee4bea37098463c23613da32020d604506da8c0518e1da4b7"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("03a7d1d856deb74c508e05031f9895dab54626251b3806e16b4bd12e781a7df5b9"), 33);
	ck_assert_str_eq(node.address,     "1BxrAr2pHpeBheusmd6fHDP2tSLAUa3qsW");

	// [Chain m/0/2147483647'/1/2147483646']
	xprv_descent_prime(&node, 2147483646);
	ck_assert_mem_eq(node.chain_code,  fromhex("637807030d55d01f9a0cb3a7839515d796bd07706386a6eddf06cc29a65a0e29"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("f1c7c871a54a804afe328b4c83a1c33b8e5ff48f5087273f04efa83b247d6a2d"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("02d2b36900396c9282fa14628566582f206a5dd0bcc8d5e892611806cafb0301f0"), 33);
	ck_assert_str_eq(node.address,     "15XVotxCAV7sRx1PSCkQNsGw3W9jT9A94R");

	// [Chain m/0/2147483647'/1/2147483646'/2]
	xprv_descent(&node, 2);
	ck_assert_mem_eq(node.chain_code,  fromhex("9452b549be8cea3ecb7a84bec10dcfd94afe4d129ebfd3b3cb58eedf394ed271"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("bb7d39bdb83ecf58f2fd82b6d918341cbef428661ef01ab97c28a4842125ac23"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("024d902e1a2fc7a8755ab5b694c575fce742c48d9ff192e63df5193e4c7afe1f9c"), 33);
	ck_assert_str_eq(node.address,     "14UKfRV9ZPUp6ZC9PLhqbRtxdihW9em3xt");
}
END_TEST

START_TEST(test_rfc6979)
{
	int res;
	bignum256 k;
	uint8_t buf[32];

	SHA256_Raw((uint8_t *)"sample", 6, buf);
	res = generate_k_rfc6979(&k, fromhex("cca9fbcc1b41e5a95d369eaa6ddcff73b61a4efaa279cfc6567e8daa39cbaf50"), buf);
	ck_assert_int_eq(res, 0);
	bn_write_be(&k, buf);
	ck_assert_mem_eq(buf, fromhex("2df40ca70e639d89528a6b670d9d48d9165fdc0febc0974056bdce192b8e16a3"), 32);

	SHA256_Raw((uint8_t *)"Satoshi Nakamoto", 16, buf);
	res = generate_k_rfc6979(&k, fromhex("0000000000000000000000000000000000000000000000000000000000000001"), buf);
	ck_assert_int_eq(res, 0);
	bn_write_be(&k, buf);
	ck_assert_mem_eq(buf, fromhex("8f8a276c19f4149656b280621e358cce24f5f52542772691ee69063b74f15d15"), 32);

	SHA256_Raw((uint8_t *)"Satoshi Nakamoto", 16, buf);
	res = generate_k_rfc6979(&k, fromhex("fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364140"), buf);
	ck_assert_int_eq(res, 0);
	bn_write_be(&k, buf);
	ck_assert_mem_eq(buf, fromhex("33a19b60e25fb6f4435af53a3d42d493644827367e6453928554f43e49aa6f90"), 32);

	SHA256_Raw((uint8_t *)"Alan Turing", 11, buf);
	res = generate_k_rfc6979(&k, fromhex("f8b8af8ce3c7cca5e300d33939540c10d45ce001b8f252bfbc57ba0342904181"), buf);
	ck_assert_int_eq(res, 0);
	bn_write_be(&k, buf);
	ck_assert_mem_eq(buf, fromhex("525a82b70e67874398067543fd84c83d30c175fdc45fdeee082fe13b1d7cfdf1"), 32);

	SHA256_Raw((uint8_t *)"All those moments will be lost in time, like tears in rain. Time to die...", 74, buf);
	res = generate_k_rfc6979(&k, fromhex("0000000000000000000000000000000000000000000000000000000000000001"), buf);
	ck_assert_int_eq(res, 0);
	bn_write_be(&k, buf);
	ck_assert_mem_eq(buf, fromhex("38aa22d72376b4dbc472e06c3ba403ee0a394da63fc58d88686c611aba98d6b3"), 32);

	SHA256_Raw((uint8_t *)"There is a computer disease that anybody who works with computers knows about. It's a very serious disease and it interferes completely with the work. The trouble with computers is that you 'play' with them!", 207, buf);
	res = generate_k_rfc6979(&k, fromhex("e91671c46231f833a6406ccbea0e3e392c76c167bac1cb013f6f1013980455c2"), buf);
	ck_assert_int_eq(res, 0);
	bn_write_be(&k, buf);
	ck_assert_mem_eq(buf, fromhex("1f4b84c23a86a221d233f2521be018d9318639d5b8bbd6374a8a59232d16ad3d"), 32);
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

#define test_bfsh(KEY, CLEAR, CIPHER) do { \
	memcpy(key, fromhex(KEY), strlen(KEY)/2); \
	memcpy(data, fromhex(CLEAR), strlen(CLEAR)/2); \
	blowfish_setkey(key, strlen(KEY)/2); \
	blowfish_encrypt(data, strlen(CLEAR)/2); \
	ck_assert_mem_eq(data, fromhex(CIPHER), strlen(CIPHER)/2); \
} while (0)

// test vectors from https://www.schneier.com/code/vectors.txt
START_TEST(test_blowfish_1)
{
	uint8_t key[8];
	uint8_t data[8];
	test_bfsh("0000000000000000", "0000000000000000", "4ef997456198dd78");
	test_bfsh("ffffffffffffffff", "ffffffffffffffff", "51866fd5b85ecb8a");
	test_bfsh("3000000000000000", "1000000000000001", "7d856f9a613063f2");
	test_bfsh("1111111111111111", "1111111111111111", "2466dd878b963c9d");
	test_bfsh("0123456789abcdef", "1111111111111111", "61f9c3802281b096");
	test_bfsh("1111111111111111", "0123456789abcdef", "7d0cc630afda1ec7");
	test_bfsh("0000000000000000", "0000000000000000", "4ef997456198dd78");
	test_bfsh("fedcba9876543210", "0123456789abcdef", "0aceab0fc6a0a28d");
	test_bfsh("7ca110454a1a6e57", "01a1d6d039776742", "59c68245eb05282b");
	test_bfsh("0131d9619dc1376e", "5cd54ca83def57da", "b1b8cc0b250f09a0");
	test_bfsh("07a1133e4a0b2686", "0248d43806f67172", "1730e5778bea1da4");
	test_bfsh("3849674c2602319e", "51454b582ddf440a", "a25e7856cf2651eb");
	test_bfsh("04b915ba43feb5b6", "42fd443059577fa2", "353882b109ce8f1a");
	test_bfsh("0113b970fd34f2ce", "059b5e0851cf143a", "48f4d0884c379918");
	test_bfsh("0170f175468fb5e6", "0756d8e0774761d2", "432193b78951fc98");
	test_bfsh("43297fad38e373fe", "762514b829bf486a", "13f04154d69d1ae5");
	test_bfsh("07a7137045da2a16", "3bdd119049372802", "2eedda93ffd39c79");
	test_bfsh("04689104c2fd3b2f", "26955f6835af609a", "d887e0393c2da6e3");
	test_bfsh("37d06bb516cb7546", "164d5e404f275232", "5f99d04f5b163969");
	test_bfsh("1f08260d1ac2465e", "6b056e18759f5cca", "4a057a3b24d3977b");
	test_bfsh("584023641aba6176", "004bd6ef09176062", "452031c1e4fada8e");
	test_bfsh("025816164629b007", "480d39006ee762f2", "7555ae39f59b87bd");
	test_bfsh("49793ebc79b3258f", "437540c8698f3cfa", "53c55f9cb49fc019");
	test_bfsh("4fb05e1515ab73a7", "072d43a077075292", "7a8e7bfa937e89a3");
	test_bfsh("49e95d6d4ca229bf", "02fe55778117f12a", "cf9c5d7a4986adb5");
	test_bfsh("018310dc409b26d6", "1d9d5c5018f728c2", "d1abb290658bc778");
	test_bfsh("1c587f1c13924fef", "305532286d6f295a", "55cb3774d13ef201");
	test_bfsh("0101010101010101", "0123456789abcdef", "fa34ec4847b268b2");
	test_bfsh("1f1f1f1f0e0e0e0e", "0123456789abcdef", "a790795108ea3cae");
	test_bfsh("e0fee0fef1fef1fe", "0123456789abcdef", "c39e072d9fac631d");
	test_bfsh("0000000000000000", "ffffffffffffffff", "014933e0cdaff6e4");
	test_bfsh("ffffffffffffffff", "0000000000000000", "f21e9a77b71c49bc");
	test_bfsh("0123456789abcdef", "0000000000000000", "245946885754369a");
	test_bfsh("fedcba9876543210", "ffffffffffffffff", "6b5c5a9c5d9e0a5a");
}
END_TEST

// mnemonic test vectors
START_TEST(test_blowfish_2)
{
	uint8_t key[24];
	uint8_t data[24];
	// 6d6e656d6f6e6963 = "mnemonic"
	test_bfsh("6d6e656d6f6e6963", "0000000000000000", "e6b5de53efaec3a5");
	test_bfsh("6d6e656d6f6e6963", "00000000000000000000000000000000", "e6b5de53efaec3a5e6b5de53efaec3a5");
	test_bfsh("6d6e656d6f6e6963", "000000000000000000000000000000000000000000000000", "e6b5de53efaec3a5e6b5de53efaec3a5e6b5de53efaec3a5");
	test_bfsh("6d6e656d6f6e6963", "7f7f7f7f7f7f7f7f", "cb21e7cd6313594b");
	test_bfsh("6d6e656d6f6e6963", "7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f", "cb21e7cd6313594bcb21e7cd6313594b");
	test_bfsh("6d6e656d6f6e6963", "7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f", "cb21e7cd6313594bcb21e7cd6313594bcb21e7cd6313594b");
	test_bfsh("6d6e656d6f6e6963", "8080808080808080", "8800e1df66298ae6");
	test_bfsh("6d6e656d6f6e6963", "80808080808080808080808080808080", "8800e1df66298ae68800e1df66298ae6");
	test_bfsh("6d6e656d6f6e6963", "808080808080808080808080808080808080808080808080", "8800e1df66298ae68800e1df66298ae68800e1df66298ae6");
	test_bfsh("6d6e656d6f6e6963", "ffffffffffffffff", "4c8be56fcf3de4cf");
	test_bfsh("6d6e656d6f6e6963", "ffffffffffffffffffffffffffffffff", "4c8be56fcf3de4cf4c8be56fcf3de4cf");
	test_bfsh("6d6e656d6f6e6963", "ffffffffffffffffffffffffffffffffffffffffffffffff", "4c8be56fcf3de4cf4c8be56fcf3de4cf4c8be56fcf3de4cf");
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

	tc = tcase_create("blowfish");
	tcase_add_test(tc, test_blowfish_1);
	tcase_add_test(tc, test_blowfish_2);
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
