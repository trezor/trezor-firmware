#include <stdio.h>
#include <assert.h>
#include <time.h>
#include <string.h>
#include <stdint.h>
#include "curves.h"
#include "ecdsa.h"
#include "secp256k1.h"
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
	ecdsa_sign(curve, priv, msg, sizeof(msg), sig, &pby);

	clock_t t = clock();
	for (int i = 0 ; i < 500; i++) {
		int res = ecdsa_verify(curve, pub, sig, msg, sizeof(msg));
		assert(res == 0);
	}
	printf("SECP256k1 verifying speed: %0.2f sig/s\n", 500.0f / ((float)(clock() - t) / CLOCKS_PER_SEC));
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

int main(void) {
	prepare_msg();
	bench_secp256k1();
	bench_ed25519();
	return 0;
}
