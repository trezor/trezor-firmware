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
	aes_blk_len(BLKLEN, &ctx); \
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
	test_aes("mnemonic", 24, "000000000000000000000000000000000000000000000000", "7b8704678f263c316ddd1746d8377a4046a99dd9e5687d59");
	test_aes("mnemonic", 32, "0000000000000000000000000000000000000000000000000000000000000000", "7c0575db9badc9960441c6b8dcbd5ebdfec522ede5309904b7088d0e77c2bcef");

	test_aes("mnemonic", 16, "686f6a6461686f6a6461686f6a6461686f6a6461", "9c3bb85af2122cc2df449033338beb56");
	test_aes("mnemonic", 24, "686f6a6461686f6a6461686f6a6461686f6a6461686f6a64", "0d7009c589869eaa1d7398bffc7660cce32207a520d6cafe");
	test_aes("mnemonic", 32, "686f6a6461686f6a6461686f6a6461686f6a6461686f6a6461686f6a6461686f", "b1a4d05e3827611c5986ea4c207679a6934f20767434218029c4b3b7a53806a3");

	test_aes("mnemonic", 16, "ffffffffffffffffffffffffffffffff", "e720f4474b7dabe382eec0529e2b1128");
	test_aes("mnemonic", 24, "ffffffffffffffffffffffffffffffffffffffffffffffff", "14dfe4c7a93e14616dce6c793110baee0b8bb404f3bec6c5");
	test_aes("mnemonic", 32, "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", "ccf498fd9a57f872a4d274549fab474cbacdbd9d935ca31b06e3025526a704fb");
}
END_TEST

START_TEST(test_mnemonic)
{
	static const char *vectors[] = {
		"00000000000000000000000000000000",
		"abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about",
		"6ca6a10baeaeff4b9b2e0dbc9f880dd8428c61168caa8cdf57234e87b7ace148ee4531ef37d518439c42392ee3878f74efec1d677b0327bca7378bfd009722a1",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"legal winner thank year wave sausage worth useful legal winner thank yellow",
		"f0eee1f28591edfad85f47ccd64f1ba18c9b3d31d5c28bf05f296f323ffd22c94edfdbe9494a094d96e8099adb80cdcc4e6b564e04ee38515d35b3d6fb9b91be",
		"80808080808080808080808080808080",
		"letter advice cage absurd amount doctor acoustic avoid letter advice cage above",
		"14949034b83876cc10b4624c2f7489499c68df72aeea503195ef2cb1686c1767fe41b854fbb0ac2596e4ba8235c27395297039578d5e7b4921e5bf7eafe28a27",
		"ffffffffffffffffffffffffffffffff",
		"zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo wrong",
		"d430f6f2fd8573c2aac937cb5eb88486cce4fd06a4c632bc58b8b24f60697e2a158e3e51290360175b38c71ca90971cbcfa26049c1cb14f3d44e031d8d18e634",
		"000000000000000000000000000000000000000000000000",
		"abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon agent",
		"6836b4fb07e82f99f157d5abec7a6bc3fae25e6aaed44b547b6e64d9bfae955cde245db6b06decb2429b5c5f849563108d7f799734b6cfb86f797c1c74d20cca",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"legal winner thank year wave sausage worth useful legal winner thank year wave sausage worth useful legal will",
		"6b5d7995263e58421531e0c9c4084c0d5738bc2eef5306cc267e496f263256aa93f0adb51ab92b26bfaf00d448e896f8564fca91e66b7cfb2ac2c7cb1e59cb0f",
		"808080808080808080808080808080808080808080808080",
		"letter advice cage absurd amount doctor acoustic avoid letter advice cage absurd amount doctor acoustic avoid letter always",
		"f3e672575342c0c0544593f76706214ab6e78098e9632b979807b1d3e0632fee8661146f740289036a831311b4e28c11601d29aec0e52ca4ee19476a0e03231e",
		"ffffffffffffffffffffffffffffffffffffffffffffffff",
		"zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo when",
		"1a4e1e5532e8d34da0c4e225745840af7f80b6e22adf9443b424965deeab3e287a45f4ccfbc6b0a4ae9945bfd0eccef65ddb05115ff6829f051cb58e2ce02227",
		"0000000000000000000000000000000000000000000000000000000000000000",
		"abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon art",
		"aae9cdd3667c7ab3169bc755c868f65980ae5cc02ab57fcea08e43b3d1652c4da748dfcaacc707f146e785e0c75fdd2935c99db986703a24ffc5961158f67c23",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"legal winner thank year wave sausage worth useful legal winner thank year wave sausage worth useful legal winner thank year wave sausage worth title",
		"217b6d8b54552deb05701e1f7478431f528e82e590bf68cd8c6236fb9c2fa16bbb9d759fa68cb8e3f17a0525596de2c645aee8a2b0b071d78411d2147fdef443",
		"8080808080808080808080808080808080808080808080808080808080808080",
		"letter advice cage absurd amount doctor acoustic avoid letter advice cage absurd amount doctor acoustic avoid letter advice cage absurd amount doctor acoustic bless",
		"d5432ff9f0a0dc85373635a658056b04b8ad96069c79c953151de03496c81f772301acbd1b4bc87f0ef07fdcf070ea7384c1c86ec324fab11ac8851d7bc7122f",
		"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
		"zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo zoo vote",
		"faed83f0823ee9958d35e9514b497729776f675ce5ce7a14d1ab47efc70d71bc7bad208c3df16ab0cce19ec2ad115fe78c93d4245028f82215c0d278616c07e7",
		"b4950b98f22cdff09bd809960771012b",
		"region portion tower tone social weapon hunt abuse noodle describe doctor fit",
		"8917cbe312d2122616df35a4f92cc81c67063200acd2ac530502e28d01e9247b6e6c87495ead957733001096b6679ff9a63f762f07a07f9834cac326f7249926",
		"e4dcab3716ef913118a8d51675c7ce8b460b5d33587c4bad",
		"tooth torch soccer column weekend obtain glance boy biology purchase victory bird gaze purse sniff auto entry hundred",
		"dc645f9c8d11ee5b372993b710540c59bdc4693b253dd207998811df4fbcbce711247361582a9042482a445a2123be514a2602913b5984336271879d1c36bc55",
		"7874365a015417bf86b2e6e68c4fb332afcaf344ac1c5b514869bdc4503f07f5",
		"journey payment notable actor door thank bracket fresh track give under grab witness keen bargain logic forget medal bounce knee eagle buzz cabin salute",
		"fe49079843bb0461496faeafd6c6e18e058c6b54403d085616863bca32a8a3ec59bca20c4f68e5f300098faf7cf592e52493ee358add5161befeef601a0984b9",
		"dd36b9581bef791e27dea2349d99f111",
		"tag remind figure daughter wasp monitor panda stairs cruel under labor carry",
		"db8870c20d22f8fd43baf8675a30567745b908c56404b65da6b940b89dee1623a207385073da5931e202006971eb0460f0c86da7be233917fde24137a5d0b4c7",
		"f268b3d9a0504f7a93602f58aca5e3b296a386d1b867a271",
		"venue easily wait doll agent run eternal album flavor gown jump gown health sell eight artefact pen melody",
		"f4afc4679667969b2a051e530c10bda028fc66fecdf6db416f6e5b834bfd26314591f3303a6f0a607fbeb0b7072a42fde064d76d362c796284107656981ad1d2",
		"575fab7f9a24cb9edd664541d491349ba1ee64ca3982ffaf0d951ffb3c03b104",
		"firm wool that crowd erosion sorry intact silly dove pig essay dance bus crash cigar core zero journey grab divide record achieve series outdoor",
		"000607026976a77b840eb314461bb8799ece12ce4844c452c39b6d94aa8c9f8f55f668786099add17a32e63338576316c93161e350ec9726d2384aa2d5ea884e",
		"7499a884c8dc8d854996a42046764af7",
		"innocent snap cancel museum silver section chaos stand cake crisp naive until",
		"0a256d3cd41423b084717335a43b58ff522a41f254448304e6b80f572b09e5709dfd88ba190c43aef3b4366016212e67d85e7f48d91c2b37306ba6792f779652",
		"4b87f573b3710d6551115c148698974849caeaef46baf41a",
		"entire distance friend group awkward razor dust clog behind crumble chair mountain original install rug struggle village spice",
		"cbe978501edc014868011032069d730947a1a37f305ad401847796c157f9039d322a0b8ba5c4e34b6ea6ea90b408249e960df501685ae720ed1d78dc8495b682",
		"1eb272608649d7ca5118174f6c71bb5a9684af1dd9159a9707803c5df8c6a229",
		"burger near oblige arrive output topple dutch actual exhaust glory human release hair fiscal jazz cargo once return theme judge test globe master clerk",
		"7dcdf57089ca467e023bcb6d97872317b9c3b120b6363d7986a95d42555e1036f914f4f19c2f381e346d24cfa5204f8cbe6b96146f39012b0740ce5ae21e625b",
		"b45c6ab5b78e98d0ec2b8cb77cf2eecb",
		"reform today pulp humor trumpet half radar immense resist travel roof nurse",
		"5118a62d70721d83e5525e7fdef5f049843900a60bc6bdc408feb0104f9fd5237000f166b811de432c27011a739578d8f9266d2882b290345ee04dae908d77d4",
		"3b80180f9abebbbf9a45c5620dc711426c1a3b0ede191608",
		"describe absorb advance cube two thank harbor reward ginger hotel session luggage script budget derive segment bid early",
		"80c58137ee8a3f0fae6d4bc2ea366f95929efe2fba063a676ea7559a383c38d1cdd5a04dd09bc29c21bf7334b3f492d6b7ce0f3ba5e78ef06337f2056aacc11b",
		"1fdc34f4457c1adddb0ff2de01b92817f4ffe7c82bef6719e4742a54d0463efc",
		"cabin ticket dial memory script humble history wrestle task assist energy copper exit view camera law grow song brown feed escape cart winner maple",
		"eae75edd758d1b65e317d15682ce76d6625251ab618dbbce179caa3aaf29e4f88e0ab97cd070c80b480bad3d50cfc458005a06949ab31d8702f95f6863eae176",
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
		mnemonic_to_seed(m, "", seed);
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
