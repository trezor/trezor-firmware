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

#include "aes.h"
#include "bignum.h"
#include "bip32.h"
#include "bip39.h"
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
#define ck_assert_mem_eq(X, Y, L) _ck_assert_mem((X), (Y), (L), ==)
#define ck_assert_mem_ne(X, Y, L) _ck_assert_mem((X), (Y), (L), !=)

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

START_TEST(test_mnemonic)
{
	static const char *vectors[] = {
		"00000000000000000000000000000000",
		"abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
		"cb5e7230ce8229de990674f6aa4288325fd4d8181f761734bd8b5cc944fedc2a4300e64422864b565352de7ffbc5ad0fafdf5344489f3a83e4a4bb5271cafaae",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"legal winner thank year wave sausage worth useful legal winner thank yellow",
		"de1277934939d6969519f44b7b3757a905d7f635be41e1e88022c346bc52ad26c0a3e9578e73e9b89066873266f285a5891d27d28cb27fccfe26d92bbd7ee364",
		"80808080808080808080808080808080",
		"letter advice cage absurd amount doctor acoustic avoid letter advice cage above",
		"8863bccef9cfffeacef1e4c6fc97bba8227ab0fc7e8e162be7467282689a13521ea364d7c4bc8cd241b59f53c5147a89c18a47248a96592ab9a2c1f1870b026c",
		"ffffffffffffffffffffffffffffffff",
		"zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong",
		"7a29e57c7a1532af1bddb7e02b892cfccc6a57b74fe9784324ea89fab8a66dc64fde79c31166b159685116f4e93c1795496f20ffdc2d3a69d3439931dabde86e",
		"000000000000000000000000000000000000000000000000",
		"abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon agent",
		"c3e382025b6a22a901505cf393faea450eb6c4a5f2a8c8f0596285b2bd84688877a6cc7231420e2bbdd2428e62ed549a78fa215b3adafd8dea075dabfc704d5e",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"legal winner thank year wave sausage worth useful legal winner thank year wave sausage worth useful legal will",
		"c82666e40eb097bf6eb05fecd7dc2ddfb6bbdc6071900f4b3fd3c3e635db69aa2094f1f450c98e8dc6103aa72df635abdfcc3b6d6ec5261a9208a07a35a3f1c8",
		"808080808080808080808080808080808080808080808080",
		"letter advice cage absurd amount doctor acoustic avoid letter advice cage absurd amount doctor acoustic avoid letter always",
		"e90681c67c55504afadca009ce4042819341fa0e90300b6d32b4f2e8e8a6678ff7e7fc1da663ae194dc7a2ef7ec7b50112d1a5efce47bfd00c66eec82f2265b5",
		"ffffffffffffffffffffffffffffffffffffffffffffffff",
		"zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo when",
		"2a372547df962742942674170a7cef495ea0b97f4864de16d0f3ee82eb577ca1eca345e601cc2df7c626c5bc51c52c28a3b4294224b685c958c7450bee6769e6",
		"0000000000000000000000000000000000000000000000000000000000000000",
		"abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art",
		"58cb9c5555d67ecc7b32305a78d1a2fcf0c9b22f1af761cfafc65eb1d3909f63ee2cab84996a7478cfd3e864cda5efb0caf580d56cf49739c6b3638d94e758c1",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"legal winner thank year wave sausage worth useful legal winner thank year wave sausage worth useful legal winner thank year wave sausage worth title",
		"0093cb3ed6d1302d3cf498017f8cb1c7dc2fdbd62ec57fc49e4b2a4dd47a23e44e0b309517d5a3e7b0f4f0ef0ed132818cf120a098a92e572ad086f1a90ccb7f",
		"8080808080808080808080808080808080808080808080808080808080808080",
		"letter advice cage absurd amount doctor acoustic avoid letter advice cage absurd amount doctor acoustic avoid letter advice cage absurd amount doctor acoustic bless",
		"8a21e46b9d264328c63e707e3d38ed4eb21508deda309fa2ef57cc8eca8b351ca3018758844ba9fb5851bab15d026a61cabace53a9a39bc91dc2c51407542cf5",
		"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
		"zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo vote",
		"5c8a1a284ab2844daf02cab322df3996574c9d53cbd36159c493441990f0d2a6bc9bc1502e3a067943d8ec67324663cbfb9667b57fed220e3f28335e26a90f93",
		"1083fa24dbb0afa4e7b327d23f666567",
		"awesome cabin matrix resist april sponsor paddle gossip split will off soon",
		"467406b36a0176e40e013393e5ecef1f5b4019980b502eda9db1db06f7786e088b206f045f2bfcf93bd3b17a598335b078fcc5890115857ff741bd154b54f049",
		"d8cbcd1ac2153ecd74048480c2732f637d642b21f0dd40df",
		"sugar fury effort loud fault grit source mountain liar bean slim shoulder stone better march brick dolphin zero",
		"f60180ea5047659cbb17ed6ef79c974de86c0170c7a1962b205329eb8fe9dcdd148615d35c515c4ec8da25f4cf54d5b7cd8cd5bf8dc4059df3a7900ca25f8306",
		"2952f95cefe041616f6f379ab649cf8b702ecf8e4acceaebdda4cc50e2bf1d7b",
		"citizen oak fire thank advice radar sad tragic one rather initial black actual guitar decrease flower turtle galaxy hard obvious athlete garbage invest have",
		"eff4b6a15bb55fcf4bbfa2b3b9e24e7dc4bed8319ef7703f1786d472c73666922925778eaa5a06f8a26d2c7e7240be746fd69edfaf197e0dae12d7e0b550cfc8",
		"f5e82717078a6ddc538a03e825f91bed",
		"vote donkey shift audit plug until evolve document trial cool eight swarm",
		"83dad22293225780a914083fc1a69bfe1d910f5b5962b0364820132a42ae1bd567a1fb4d5a19ad3d64539e38a7ee3d6429fac2b74e72b020913131c5eadb7db4",
		"16b59b6a426f2f302f73049a32ab8572394278982212357a",
		"birth proud surround luggage very object saddle gauge olive next throw tongue neither detail gauge drastic cube strategy",
		"38ceb07e0dad221f612631843be6ae44a650aaf789c8ebea9313e07498d7864385227d25c7a8268a5b850367eef31639632e9218acadead20980b864b1cd477e",
		"95b6cb48c7bc9c2a54496ae3eea790824b57e52b9637058f084555bc1b809b2f",
		"noble rent split month six benefit eye coil token inside tomorrow afraid rely verb purity shoulder airport joke bacon problem script scare hole trumpet",
		"e33e3d32e467877596a18ac60050488a0ec1557fda6bf95bad3d33d964c5e99dcd97d378403cc2723ed1c85c12b42bc59f15458d970d7a9d015f556109c146b0",
		"7f93397f750f70a26513de2732ed95ee",
		"legend oil garlic tube warfare eye nephew knock cheese number grace tackle",
		"7f92ad63e4cdf4f15c23740556ad81e7f8cbd67cc672c93894c9c0d4fb171539eed5ab29f366570ed9940b816f45a539c3816f7ac19511794b752c5c1ec0e732",
		"14c29fe840dd1c9f05d392ba13e4e1466b32ed0726a15f89",
		"below belt wheel like spike exhibit blanket inch ring palace debate mimic rebel isolate broken stage garbage enhance",
		"7bae6e54f8bad645f18f574b310bd3e6fde126dabcaf63a889940380e4798810e48c8151fc56bb2389c07498deacef025f03cbf8fc57ea3ec68f6421b0fcb649",
		"cb30610d175ffeab8357d5190d31923997752a7f9815087bfcad5eb0b43f6468",
		"sleep loan drive concert zoo fiction ask wide boil hat goose industry jar news wrist actor anchor that clip runway area cabbage museum abuse",
		"b922030609e7626696b9cf5ca4c06cd99290be30b1052770f6a60c5f26532d178f287a4285d7a2add2845dc89a816b26fdba1c830067d130740f64c0ab5cfbe1",
		"a30b50a5439dcd1774f412ea5ec33403",
		"perfect fold citizen mango system merry stable liquid tumble voyage snack alter",
		"aae175f26848370c4d5d3d0640597e2bf1b28e95908dd877259b3eac5d71ffe3140739a3ed80180f88159571df84441985620e6b2fb0696e5cba1aa7b8d10b98",
		"70044da2175ad681d0ebbf2da83cf407eb9c8fd91fc0a8c9",
		"hybrid carbon hammer concert pulp domain dry jewel color draft dial average right elevator good way potato energy",
		"a3dffe3a31a2e949d1b04af7495a5b59db17e41d93b985feeaaae89260a9c86c6dcdf7cb32eaba61c2f4f0340f0f17d1ebb67af11657286b2ffd66ec4e05a8b7",
		"0e0bab4df9669b97ba3f75a50b2e92423bbe6e91a1b01dbbf3ba200a917c9106",
		"asthma front square version have slim trophy upgrade pink floor pig love room dance educate current buffalo test update divorce poverty salad dune scheme",
		"2eb4d85fbd8deaf9b06bf9cdb3e5f36e8da040d110312075eb32e776fc8e505b94be3e63c1525ad41f5e5968a263853001dc7c40ea3af8e8b0cfb7effd5f408c",
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
