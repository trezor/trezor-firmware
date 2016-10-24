#include <stdio.h>
#include <assert.h>
#include <time.h>
#include <string.h>
#include <stdint.h>
#include "curves.h"
#include "ecdsa.h"
#include "secp256k1.h"
#include "nist256p1.h"
#include "ed25519.h"
#include "curve25519.h"

static uint8_t msg[32];

void prepare_msg(void)
{
	for (size_t i = 0; i < sizeof(msg); i++) {
		msg[i] = i * 1103515245;
	}
}

void bench_secp256k1(void)
{
	uint8_t sig[64], pub[33], priv[32], pby;

	const ecdsa_curve *curve = &secp256k1;

	memcpy(priv, "\xc5\x5e\xce\x85\x8b\x0d\xdd\x52\x63\xf9\x68\x10\xfe\x14\x43\x7c\xd3\xb5\xe1\xfb\xd7\xc6\xa2\xec\x1e\x03\x1f\x05\xe8\x6d\x8b\xd5", 32);
	ecdsa_get_public_key33(curve, priv, pub);
	ecdsa_sign(curve, priv, msg, sizeof(msg), sig, &pby, NULL);

	clock_t t = clock();
	for (int i = 0 ; i < 500; i++) {
		int res = ecdsa_verify(curve, pub, sig, msg, sizeof(msg));
		assert(res == 0);
	}
	printf("SECP256k1 verifying speed: %0.2f sig/s\n", 500.0f / ((float)(clock() - t) / CLOCKS_PER_SEC));
}

void bench_nist256p1(void)
{
	uint8_t sig[64], pub[33], priv[32], pby;

	const ecdsa_curve *curve = &nist256p1;

	memcpy(priv, "\xc5\x5e\xce\x85\x8b\x0d\xdd\x52\x63\xf9\x68\x10\xfe\x14\x43\x7c\xd3\xb5\xe1\xfb\xd7\xc6\xa2\xec\x1e\x03\x1f\x05\xe8\x6d\x8b\xd5", 32);
	ecdsa_get_public_key33(curve, priv, pub);
	ecdsa_sign(curve, priv, msg, sizeof(msg), sig, &pby, NULL);

	clock_t t = clock();
	for (int i = 0 ; i < 500; i++) {
		int res = ecdsa_verify(curve, pub, sig, msg, sizeof(msg));
		assert(res == 0);
	}
	printf("NIST256p1 verifying speed: %0.2f sig/s\n", 500.0f / ((float)(clock() - t) / CLOCKS_PER_SEC));
}

void bench_ed25519(void)
{
	ed25519_public_key pk;
	ed25519_secret_key sk;
	ed25519_signature sig;

	memcpy(pk, "\xc5\x5e\xce\x85\x8b\x0d\xdd\x52\x63\xf9\x68\x10\xfe\x14\x43\x7c\xd3\xb5\xe1\xfb\xd7\xc6\xa2\xec\x1e\x03\x1f\x05\xe8\x6d\x8b\xd5", 32);
	ed25519_publickey(sk, pk);
	ed25519_sign(msg, sizeof(msg), sk, pk, sig);

	clock_t t = clock();
	for (int i = 0 ; i < 500; i++) {
		int res = ed25519_sign_open(msg, sizeof(msg), pk, sig);
		assert(res == 0);
	}
	printf("Ed25519 verifying speed: %0.2f sig/s\n", 500.0f / ((float)(clock() - t) / CLOCKS_PER_SEC));
}

void test_verify_speed(void)
{
	prepare_msg();
	bench_secp256k1();
	bench_nist256p1();
	bench_ed25519();
}

void bench_curve25519(void)
{
	uint8_t result[32];
	uint8_t secret[32];
	uint8_t basepoint[32];

	memcpy(secret, "\xc5\x5e\xce\x85\x8b\x0d\xdd\x52\x63\xf9\x68\x10\xfe\x14\x43\x7c\xd3\xb5\xe1\xfb\xd7\xc6\xa2\xec\x1e\x03\x1f\x05\xe8\x6d\x8b\xd5", 32);
	memcpy(basepoint, "\x96\x47\xda\xbe\x1e\xea\xaf\x25\x47\x1e\x68\x0b\x4d\x7c\x6f\xd1\x14\x38\x76\xbb\x77\x59\xd8\x3d\x0f\xf7\xa2\x49\x08\xfd\xda\xbc", 32);

	clock_t t = clock();
	for (int i = 0 ; i < 500; i++) {
		curve25519_donna(result, secret, basepoint);
	}
	printf("Curve25519 multiplying speed: %0.2f mul/s\n", 500.0f / ((float)(clock() - t) / CLOCKS_PER_SEC));
}

void test_multiply_speed(void)
{
	bench_curve25519();
}

static HDNode root;

void prepare_node(void)
{
	hdnode_from_seed((uint8_t *)"NothingToSeeHere", 16, SECP256K1_NAME, &root);
	hdnode_fill_public_key(&root);
}

void bench_ckd_normal(int iterations)
{
	char addr[MAX_ADDR_SIZE];
	HDNode node;
	clock_t t = clock();
	for (int i = 0; i < iterations; i++) {
		memcpy(&node, &root, sizeof(HDNode));
		hdnode_public_ckd(&node, i);
		hdnode_fill_public_key(&node);
		ecdsa_get_address(node.public_key, 0, addr, sizeof(addr));
		if (i == 0 || i == iterations - 1) {
			printf("address = %s\n", addr);
		}
	}
	printf("CKD normal speed: %0.2f iter/s\n", iterations / ((float)(clock() - t) / CLOCKS_PER_SEC));
}

void bench_ckd_optimized(int iterations)
{
	char addr[MAX_ADDR_SIZE];
	curve_point pub;
	ecdsa_read_pubkey(&secp256k1, root.public_key, &pub);
	clock_t t = clock();
	for (int i = 0; i < iterations; i++) {
		hdnode_public_ckd_address_optimized(&pub, root.public_key, root.chain_code, i, 0, addr, sizeof(addr));
		if (i == 0 || i == iterations -1) {
			printf("address = %s\n", addr);
		}
	}
	printf("CKD optim speed: %0.2f iter/s\n", iterations / ((float)(clock() - t) / CLOCKS_PER_SEC));
}

void test_ckd_speed(int iterations)
{
	prepare_node();
	bench_ckd_normal(iterations);
	bench_ckd_optimized(iterations);
}

int main(void) {
	test_verify_speed();
	test_multiply_speed();
	test_ckd_speed(1000);
	return 0;
}
