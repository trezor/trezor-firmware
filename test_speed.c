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

uint8_t msg[32];

void prepare_msg(void)
{
	for (size_t i = 0; i < sizeof(msg); i++) {
		msg[i] = i * 1103515245;
	}
}

void bench_secp256k1(void) {
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

void bench_nist256p1(void) {
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

void bench_ed25519(void) {
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

void test_verify_speed(void) {
	prepare_msg();
	bench_secp256k1();
	bench_nist256p1();
	bench_ed25519();
}

HDNode root;

void prepare_node(void)
{
	hdnode_from_seed((uint8_t *)"NothingToSeeHere", 16, SECP256K1_NAME, &root);
}

void bench_ckd_normal(void) {
	char addr[40];
	clock_t t = clock();
	for (int i = 0; i < 1000; i++) {
		HDNode node = root;
		hdnode_public_ckd(&node, i);
		ecdsa_get_address(node.public_key, 0, addr, 40);
		if (i == 0) {
			printf("address = %s\n", addr);
		}
	}
	printf("CKD normal speed: %0.2f iter/s\n", 1000.0f / ((float)(clock() - t) / CLOCKS_PER_SEC));
}

void bench_ckd_optimized(void) {
	char addr[40];
	curve_point pub;
	ecdsa_read_pubkey(0, root.public_key, &pub);
	clock_t t = clock();
	for (int i = 0; i < 1000; i++) {
		hdnode_public_ckd_address_optimized(&pub, root.public_key, root.chain_code, i, 0, addr, 40);
		if (i == 0) {
			printf("address = %s\n", addr);
		}
	}
	printf("CKD optim speed: %0.2f iter/s\n", 1000.0f / ((float)(clock() - t) / CLOCKS_PER_SEC));
}

void test_ckd_speed(void) {
	prepare_node();
	bench_ckd_normal();
	bench_ckd_optimized();
}

int main(void) {
	test_verify_speed();
	test_ckd_speed();
	return 0;
}
