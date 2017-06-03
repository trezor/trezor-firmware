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

#include <openssl/ecdsa.h>
#include <openssl/obj_mac.h>
#include <openssl/sha.h>
#include <stdio.h>
#include <stdint.h>

#include "ecdsa.h"
#include "rand.h"
#include "secp256k1.h"

int main(int argc, char *argv[])
{
	uint8_t sig[64], pub_key33[33], pub_key65[65], priv_key[32], msg[256], buffer[1000], hash[32], *p;
	uint32_t i, j, msg_len;
	SHA256_CTX sha256;
	EC_GROUP *ecgroup;
	int cnt = 0;

	ecgroup = EC_GROUP_new_by_curve_name(NID_secp256k1);

	unsigned long max_iterations = -1;
	if (argc == 2) {
		sscanf(argv[1], "%lu", &max_iterations);
	} else if (argc > 2) {
		puts("Zero or one command-line arguments only, exiting....");
	}
	unsigned long iterations = 0;
	while (argc == 1 || iterations < max_iterations) {
		// random message len between 1 and 256
		msg_len = (random32() & 0xFF) + 1;
		// create random message
		for (i = 0; i < msg_len; i++) {
			msg[i] = random32() & 0xFF;
		}
		// new ECDSA key
		EC_KEY *eckey = EC_KEY_new();
		EC_KEY_set_group(eckey, ecgroup);

		// generate the key
		EC_KEY_generate_key(eckey);
		// copy key to buffer
		p = buffer;
		i2d_ECPrivateKey(eckey, &p);

		// size of the key is in buffer[8] and the key begins right after that
		i = buffer[8];
		// extract key data
		if (i > 32) {
			for (j = 0; j < 32; j++) {
				priv_key[j] = buffer[j + i - 23];
			}
		} else {
			for (j = 0; j < 32 - i; j++) {
				priv_key[j] = 0;
			}
			for (j = 0; j < i; j++) {
				priv_key[j + 32 - i] = buffer[j + 9];
			}
		}

		// use our ECDSA signer to sign the message with the key
		if (ecdsa_sign(&secp256k1, priv_key, msg, msg_len, sig, NULL, NULL) != 0) {
			printf("trezor-crypto signing failed\n");
			break;
		}

		// generate public key from private key
		ecdsa_get_public_key33(&secp256k1, priv_key, pub_key33);
		ecdsa_get_public_key65(&secp256k1, priv_key, pub_key65);

		// use our ECDSA verifier to verify the message signature
		if (ecdsa_verify(&secp256k1, pub_key65, sig, msg, msg_len) != 0) {
			printf("trezor-crypto verification failed (pub_key_len = 65)\n");
			break;
		}
		if (ecdsa_verify(&secp256k1, pub_key33, sig, msg, msg_len) != 0) {
			printf("trezor-crypto verification failed (pub_key_len = 33)\n");
			break;
		}

		// copy signature to the OpenSSL struct
		ECDSA_SIG *signature = ECDSA_SIG_new();
		BN_bin2bn(sig, 32, signature->r);
		BN_bin2bn(sig + 32, 32, signature->s);

		// compute the digest of the message
		SHA256_Init(&sha256);
		SHA256_Update(&sha256, msg, msg_len);
		SHA256_Final(hash, &sha256);

		// verify all went well, i.e. we can decrypt our signature with OpenSSL
		if (ECDSA_do_verify(hash, 32, signature, eckey) != 1) {
			printf("OpenSSL verification failed\n");
			break;
		}
		ECDSA_SIG_free(signature);
		EC_KEY_free(eckey);
		cnt++;
		if ((cnt % 100) == 0) printf("Passed ... %d\n", cnt);
            ++iterations;
	}
	EC_GROUP_free(ecgroup);
	return 0;
}
