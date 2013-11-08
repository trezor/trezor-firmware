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
#define ck_assert_mem_eq(X, Y, L) _ck_assert_mem(X, Y, L, ==)
#define ck_assert_mem_ne(X, Y, L) _ck_assert_mem(X, Y, L, !=)

// test vector 1 from https://en.bitcoin.it/wiki/BIP_0032_TestVectors
START_TEST(test_bip32_vector_1)
{
	XprvNode node;

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
	XprvNode node;

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
		"risk tiger venture dinner age assume float denial penalty hello game wing",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"truth chase learn pretty right casual acoustic frozen betray main slogan method",
		"80808080808080808080808080808080",
		"olive garment twenty drill people finish hat own usual level milk usage",
		"ffffffffffffffffffffffffffffffff",
		"laundry faint system client frog vanish plug shell slot cable large embrace",
		"000000000000000000000000000000000000000000000000",
		"giant twelve seat embark ostrich jazz leader lunch budget hover much weapon vendor build truth garden year list",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"awful faint gun mean fuel side slogan marine glad donkey velvet oyster movie real type digital dress federal",
		"808080808080808080808080808080808080808080808080",
		"bless carpet daughter animal hospital pave faculty escape fortune song sign twin unknown bread mobile normal agent use",
		"ffffffffffffffffffffffffffffffffffffffffffffffff",
		"saddle curve flight drama client resemble venture arch will ordinary enrich clutch razor shallow trophy tumble dice outer",
		"0000000000000000000000000000000000000000000000000000000000000000",
		"supreme army trim onion neglect coach squirrel spider device glass cabbage giant web digital floor able social magnet only fork fuel embrace salt fence",
		"7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f",
		"cloth video uncle switch year captain artist country adjust edit inherit ocean tennis soda baby express hospital forest panel actual profit boy spice elite",
		"8080808080808080808080808080808080808080808080808080808080808080",
		"fence twin prize extra choose mask twist deny cereal quarter can power term ostrich leg staff nature nut swift sausage amateur aim script wisdom",
		"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
		"moon fiscal evidence exile rifle series neglect giant exclude banana glance frown kangaroo globe turtle hat fitness casual sudden select idle arctic best unlock",
		"449ea2d7249c6e0d8d295424fb8894cf",
		"choice barrel artefact cram increase sell veteran matrix mirror hollow walk pave",
		"75fc3f44a7ff8e2b8af05aa18bded3827a3796df406763dd",
		"crack outside teach chat praise client manual scorpion predict chalk decrease casino lunch garbage enable ball when bamboo",
		"1cce2f8c2c6a7f2d8473ebf1c32ce13b36737835d7a8768f44dcf96d64782c0e",
		"muffin evoke all fiber night guard black quote neck expire dial tenant leisure have dragon neck notable peace captain insane nice uphold shine angry",
		"3daa82dd08bd144ec9fb9f77c6ece3d2",
		"foil dawn net enroll turtle bird vault trumpet service fun immune unveil",
		"9720239c0039f8446d44334daec325f3c24b3a490315d6d9",
		"damp all desert dash insane pear debate easily soup enough goddess make friend plug violin pact wealth insect",
		"fe58c6644bc3fad95832d4400cea0cce208c8b19bb4734a26995440b7fae7600",
		"wet sniff asthma once gap enrich pumpkin define trust rude gesture keen grass fine emerge census immense smooth ritual spirit rescue problem beef choice",
		"99fe82c94edadffe75e1cc64cbd7ada7",
		"thing real emerge verify domain cloud lens teach travel radio effort glad",
		"4fd6e8d06d55b4700130f8f462f7f9bfc6188da83e3faadb",
		"diary opinion lobster code orange odor insane permit spirit evolve upset final antique grant friend dutch say enroll",
		"7a547fb59606e89ba88188013712946f6cb31c3e0ca606a7ee1ff23f57272c63",
		"layer owner legal stadium glance oyster element spell episode eager wagon stand pride old defense black print junior fade easy topic ready galaxy debris",
		"e5fc62d20e0e5d9b2756e8d4d91cbb80",
		"flat make unit discover rifle armed unit acquire group panel nerve want",
		"d29be791a9e4b6a48ff79003dbf31d6afabdc4290a273765",
		"absurd valve party disorder basket injury make blanket vintage ancient please random theory cart retire odor borrow belt",
		"c87c135433c16f1ecbf9919dc53dd9f30f85824dc7264d4e1bd644826c902be2",
		"upper will wisdom term once bean blur inquiry used bamboo frequent hamster amazing cake attack any author mimic leopard day token joy install company",
		0,
		0,
	};

	const char **d, **s, *m;

	// check encode
	d = vectors;
	s = vectors + 1;
	while (*d && *s) {
		m = mnemonic_encode(fromhex(*d), strlen(*d) / 2, 0);
		ck_assert_ptr_ne(m, 0);
		ck_assert_str_eq(m, *s);
		d += 2; s += 2;
	}

	// check decode
	d = vectors;
	s = vectors + 1;
	uint8_t data[32];
	int len;
	while (*d && *s) {
		len = mnemonic_decode(*s, data, 0);
		ck_assert_int_eq(len, strlen(*d) / 2);
		ck_assert_mem_eq(fromhex(*d), data, len);
		d += 2; s += 2;
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
