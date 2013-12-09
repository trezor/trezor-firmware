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
	hdnode_from_seed(fromhex("000102030405060708090a0b0c0d0e0f"), 16, &node);

	// [Chain m]
	ck_assert_mem_eq(node.chain_code,  fromhex("873dff81c02f525623fd1fe5167eac3a55a049de3d314bb42ee227ffed37d508"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("e8f32e723decf4051aefac8e2c93c9c5b214313817cdb01a1494b917c8436b35"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("0339a36013301597daef41fbe593a02cc513d0b55527ec2df1050e2e8ff49c85c2"), 33);
	ck_assert_str_eq(node.address,     "15mKKb2eos1hWa6tisdPwwDC1a5J1y9nma");

	// [Chain m/0']
	hdnode_descent_prime(&node, 0);
	ck_assert_mem_eq(node.chain_code,  fromhex("47fdacbd0f1097043b78c63c20c34ef4ed9a111d980047ad16282c7ae6236141"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("edb2e14f9ee77d26dd93b4ecede8d16ed408ce149b6cd80b0715a2d911a0afea"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("035a784662a4a20a65bf6aab9ae98a6c068a81c52e4b032c0fb5400c706cfccc56"), 33);
	ck_assert_str_eq(node.address,     "19Q2WoS5hSS6T8GjhK8KZLMgmWaq4neXrh");

	// [Chain m/0'/1]
	hdnode_descent(&node, 1);
	ck_assert_mem_eq(node.chain_code,  fromhex("2a7857631386ba23dacac34180dd1983734e444fdbf774041578e9b6adb37c19"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("3c6cb8d0f6a264c91ea8b5030fadaa8e538b020f0a387421a12de9319dc93368"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("03501e454bf00751f24b1b489aa925215d66af2234e3891c3b21a52bedb3cd711c"), 33);
	ck_assert_str_eq(node.address,     "1JQheacLPdM5ySCkrZkV66G2ApAXe1mqLj");

	// [Chain m/0'/1/2']
	hdnode_descent_prime(&node, 2);
	ck_assert_mem_eq(node.chain_code,  fromhex("04466b9cc8e161e966409ca52986c584f07e9dc81f735db683c3ff6ec7b1503f"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("cbce0d719ecf7431d88e6a89fa1483e02e35092af60c042b1df2ff59fa424dca"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("0357bfe1e341d01c69fe5654309956cbea516822fba8a601743a012a7896ee8dc2"), 33);
	ck_assert_str_eq(node.address,     "1NjxqbA9aZWnh17q1UW3rB4EPu79wDXj7x");

	// [Chain m/0'/1/2'/2]
	hdnode_descent(&node, 2);
	ck_assert_mem_eq(node.chain_code,  fromhex("cfb71883f01676f587d023cc53a35bc7f88f724b1f8c2892ac1275ac822a3edd"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("0f479245fb19a38a1954c5c7c0ebab2f9bdfd96a17563ef28a6a4b1a2a764ef4"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("02e8445082a72f29b75ca48748a914df60622a609cacfce8ed0e35804560741d29"), 33);
	ck_assert_str_eq(node.address,     "1LjmJcdPnDHhNTUgrWyhLGnRDKxQjoxAgt");

	// [Chain m/0'/1/2'/2/1000000000]
	hdnode_descent(&node, 1000000000);
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

	// init m
	hdnode_from_seed(fromhex("fffcf9f6f3f0edeae7e4e1dedbd8d5d2cfccc9c6c3c0bdbab7b4b1aeaba8a5a29f9c999693908d8a8784817e7b7875726f6c696663605d5a5754514e4b484542"), 64, &node);

	// [Chain m]
	ck_assert_mem_eq(node.chain_code,  fromhex("60499f801b896d83179a4374aeb7822aaeaceaa0db1f85ee3e904c4defbd9689"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("4b03d6fc340455b363f51020ad3ecca4f0850280cf436c70c727923f6db46c3e"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("03cbcaa9c98c877a26977d00825c956a238e8dddfbd322cce4f74b0b5bd6ace4a7"), 33);
	ck_assert_str_eq(node.address,     "1JEoxevbLLG8cVqeoGKQiAwoWbNYSUyYjg");

	// [Chain m/0]
	hdnode_descent(&node, 0);
	ck_assert_mem_eq(node.chain_code,  fromhex("f0909affaa7ee7abe5dd4e100598d4dc53cd709d5a5c2cac40e7412f232f7c9c"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("abe74a98f6c7eabee0428f53798f0ab8aa1bd37873999041703c742f15ac7e1e"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("02fc9e5af0ac8d9b3cecfe2a888e2117ba3d089d8585886c9c826b6b22a98d12ea"), 33);
	ck_assert_str_eq(node.address,     "19EuDJdgfRkwCmRzbzVBHZWQG9QNWhftbZ");

	// [Chain m/0/2147483647']
	hdnode_descent_prime(&node, 2147483647);
	ck_assert_mem_eq(node.chain_code,  fromhex("be17a268474a6bb9c61e1d720cf6215e2a88c5406c4aee7b38547f585c9a37d9"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("877c779ad9687164e9c2f4f0f4ff0340814392330693ce95a58fe18fd52e6e93"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("03c01e7425647bdefa82b12d9bad5e3e6865bee0502694b94ca58b666abc0a5c3b"), 33);
	ck_assert_str_eq(node.address,     "1Lke9bXGhn5VPrBuXgN12uGUphrttUErmk");

	// [Chain m/0/2147483647'/1]
	hdnode_descent(&node, 1);
	ck_assert_mem_eq(node.chain_code,  fromhex("f366f48f1ea9f2d1d3fe958c95ca84ea18e4c4ddb9366c336c927eb246fb38cb"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("704addf544a06e5ee4bea37098463c23613da32020d604506da8c0518e1da4b7"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("03a7d1d856deb74c508e05031f9895dab54626251b3806e16b4bd12e781a7df5b9"), 33);
	ck_assert_str_eq(node.address,     "1BxrAr2pHpeBheusmd6fHDP2tSLAUa3qsW");

	// [Chain m/0/2147483647'/1/2147483646']
	hdnode_descent_prime(&node, 2147483646);
	ck_assert_mem_eq(node.chain_code,  fromhex("637807030d55d01f9a0cb3a7839515d796bd07706386a6eddf06cc29a65a0e29"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("f1c7c871a54a804afe328b4c83a1c33b8e5ff48f5087273f04efa83b247d6a2d"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("02d2b36900396c9282fa14628566582f206a5dd0bcc8d5e892611806cafb0301f0"), 33);
	ck_assert_str_eq(node.address,     "15XVotxCAV7sRx1PSCkQNsGw3W9jT9A94R");

	// [Chain m/0/2147483647'/1/2147483646'/2]
	hdnode_descent(&node, 2);
	ck_assert_mem_eq(node.chain_code,  fromhex("9452b549be8cea3ecb7a84bec10dcfd94afe4d129ebfd3b3cb58eedf394ed271"), 32);
	ck_assert_mem_eq(node.private_key, fromhex("bb7d39bdb83ecf58f2fd82b6d918341cbef428661ef01ab97c28a4842125ac23"), 32);
	ck_assert_mem_eq(node.public_key,  fromhex("024d902e1a2fc7a8755ab5b694c575fce742c48d9ff192e63df5193e4c7afe1f9c"), 33);
	ck_assert_str_eq(node.address,     "14UKfRV9ZPUp6ZC9PLhqbRtxdihW9em3xt");
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
		"a3c9324fab99733ef7b5f9313e49cd45a134ee77da9aa176a84458d4b73e46f00a59361709d71d6b68338c957366937942b8f2ce2bd306b4ab0ae63c6b4ff7f5",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"legal winner thank year wave sausage worth useful legal winner thank yellow",
		"f48f158e9689580f91ae0c813f4353ba2f90cd242e811ec27b2d79f97eb21fcfaf54a0b546c27c3b0a60285df2b064b3eef84fa7269d93ab013af10a20adc758",
		"80808080808080808080808080808080",
		"letter advice cage absurd amount doctor acoustic avoid letter advice cage above",
		"7804de4eb059484ebd7c384e3bd99654763ff1f736abf4e8a5053b12594ea7389beefd967031f03416fa03994cf6be7d3f2fbe37709a27cd091f9e3d310f16d0",
		"ffffffffffffffffffffffffffffffff",
		"zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong",
		"ce2467164ca78cbce7c368bf35a390474d0e3af6afc4cc47214d215dcfc52ee567fd9921e66c32fc34e8f37abc468e7ba6cc744a96e815c95c583ad849d1c372",
		"000000000000000000000000000000000000000000000000",
		"abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon agent",
		"e6fa0d745f5b841a4c90f1487dea80d5e5cc64c46c7aebe115b10ac333066f37b6d34ae514b8a1acb21b38c3836c248aec81c10874c2323bee98e70443cb2e2c",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"legal winner thank year wave sausage worth useful legal winner thank year wave sausage worth useful legal will",
		"b829d8809875e7cae49114971e6ab87f13bd133c8d676972fb7a7ce8a9604b57759137091f21018ecd757906331c7e5466c8d9bc31b705e96e959beba111acc5",
		"808080808080808080808080808080808080808080808080",
		"letter advice cage absurd amount doctor acoustic avoid letter advice cage absurd amount doctor acoustic avoid letter always",
		"e8716279b6e74e876477061b83c4b29eeab288ea85ea196d95281dc0504c3edb1c70c86042e66f56ad27fb93d24c0a64294eac9668f0bba6d13a13882de542dd",
		"ffffffffffffffffffffffffffffffffffffffffffffffff",
		"zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo when",
		"417b80e3489de48dc644d9bf8e32ed907f918efdaf78541c219e6e1b6e7e17ed38448e7d2ef311ad4446f8be779507d288285eb5eff32ce723d4b3692a26d6a4",
		"0000000000000000000000000000000000000000000000000000000000000000",
		"abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art",
		"c716b0c6e051b60f819ba04bc5c402ac15e3aa4071c99735dfecce05d41b550155ae3511789a0ccf2cb245050f53e48292e8d88864e7c46eaa2fe626373e6fc8",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"legal winner thank year wave sausage worth useful legal winner thank year wave sausage worth useful legal winner thank year wave sausage worth title",
		"8d80646b3677f02a56efc2977dc5972dadddd96dc34309119fbd44f5f939344df0e6c0aa924fabfe858c123283f904e1fcb24a5e20b70d69ec82a40e3e010c12",
		"8080808080808080808080808080808080808080808080808080808080808080",
		"letter advice cage absurd amount doctor acoustic avoid letter advice cage absurd amount doctor acoustic avoid letter advice cage absurd amount doctor acoustic bless",
		"fd544f531a25958d2980925b10e7146290dd8615fd9241a66b0681cf3afb44e607a279cc88fa4afe65779b07b3ba441dcfb13be42266642c474fb4787683556c",
		"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
		"zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo vote",
		"024a5866efbd866885915e8eb2fc743af294c1b69285d2d62efff4228d6b3eb53bfc2ecd97048fc9691b200ee4f11af4e51fab23aa0ac674dd187235b4e3283f",
		"7dce4ed2284c9134d026608ab684c05c",
		"lava include region explain simple omit dog slot melt reflect copy reward",
		"bf010975d766bec901a632c0eadc9461de1ff89c20e37e49a67ae03730681a08122004304ed92bff0592db5271254967de4bc7f3a20de9b3becc5ab951c28d7c",
		"0ce452419635c1a5faf44d60f2029f73fdc43419b4de1f03",
		"artefact card motor cluster foster spray type meadow genius mosquito pond tree sword borrow grocery orange business burger",
		"fd81692c4b0341a73bdb479ad5f572444658c68e11e693c06cafbda8d27f31eed03f32fa6e02744fcf902b8383253c64f98ffd659ba12fcb7dff47991d811fb0",
		"00ac97c48106f0aeb8ba061e0250a559b3251dc35854e694780ba51d53a50120",
		"absent gorilla van acoustic humor firm title dolphin bulk barely citizen recall crane moment aspect appear track phrase actual enforce steel spoon afraid benefit",
		"97a796e70d1ba31176e0ace6feffa6bdcda6233648deb83b7a92e0dd01ad133d0b545a4d1283e5d5bef984b6b055fe9ebb99f4063607a7f17cdcee20a5fde35f",
		"5baf069620eff15c71dd97c9a6ee328f",
		"forum join pitch dove yellow purchase shuffle real situate danger million bunker",
		"8e6416b101bc429d59becfdeef9b4ca40b4dd938efca1d3dabb54dfcbd48a78a65a2a28fdf4732f94806f2e8aa2e40fadff71fa7060883ce50eea7a90fbe4bd3",
		"977f8287f9ed670b8489838ab0476a63b65d4df12f406e68",
		"number winter peanut video stool magic banana corn melt lion surround shuffle grape plunge seven trend hover dwarf",
		"bb63f0b3e0f9a1ed6afa0a694e6e3673f669ec8ac16b36bb6c3d273db387357b83e0c09e05c9dfc58b09a226a84e93a6bba558050b7b73c3a9b8f1bd8f3b7c33",
		"3edc83b60740d77af3afa2fcb82c2f1bc541ee4e2518ddef4996d32453f54a3c",
		"disagree tomato unique attend aspect runway solid violin witness scrap armed daring favorite warm decade perfect target kid grant play early wide cigar night",
		"fdd3a53afaaf299cb3c5c1f9a2bb69627a03da65106deca4301859cda102d34eece0ad49558f145fb8986cf39b4ce88aad96c21ae9be2894da97a6379659ad25",
		"63deb1e7f0c3de56f4ab43c9d2ae6c86",
		"glow void ketchup thunder digital clock sport half six nice open artefact",
		"68ce9777c0adc97c85ff636fd0c677b00c5f1dab44c4090a5f60c516ccb50a8b8a3f59afeaf85a935d986ad37dcea8e921e9ecde3bb6649c4cbc843b19e2b8a5",
		"e77c6500b49072aefdf0a8aa787cf557d1920e94103e0597",
		"trash tobacco dizzy hard already first water bench price sentence diary quick bomb also expect amazing airport royal",
		"4c9e646357ea442fb2734018662e7473b5870ef7dc9f5048f9460ec22f08aeea561def3664e8f8a96759eaf1aeedb2b113fb820b96e8dc5853fd7de6293568de",
		"89bb4bc5555992cdaf3444c5e7ca5a6e9f27efab894f1990bae41be8b2a26ea4",
		"meadow surge vanish primary odor grocery rubber mass shine dinner notable tag venue water purchase clarify book magic ribbon daughter menu eye ritual orchard",
		"71ce132d69f9bd4ebd7a3f8b4c45d057341670f9093fb22ce4855ee1672119d6a430f203ebcde5767e53f7c3ff64a5ad29ccd41f31d5d4f9db59e21f65b02cd0",
		"00641669f095b433a304ed0f953f28eb",
		"about camera omit thrive forget border metal oval auto prepare sketch stomach",
		"016837c6355b0e8998a2fe8e10294a8b5dc0d9bc87e545e38f1ae77b4ade3247998a101ac1146f52414c9c8e0442f610fd7f0af25b60823fd044dc6902c865c8",
		"b8b0ff94389d3ec591c7d2fb72d8d3666e4e52b8cdf5471d",
		"reward margin topic illness stadium glare either where window nothing crumble smoke top citizen tobacco salt either truth",
		"366e1ba1ab99d840505b94a20d9c63f1e17ec330ff77a7e2db399b57be5d34971ca33d7dea361f5bc9f3e6c939f0624f7231d62f53b9963d9632c8926a031abe",
		"911fec0fbd88029f6fa99164896c18d898c9232af18bdcca3e42d53b86493104",
		"much youth advance kitchen lens exile salt cram goose enter alert raise milk muscle profit cousin system faint mouse price reveal cause series long",
		"ed60c0f8ee61d91be8c96dbe8fd999c21d77c162e682fff73e904bf138d6f4b48e69becf69d4c72fd0e630179238acc9dd037eaec55eca077e0ad379249dc456",
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
