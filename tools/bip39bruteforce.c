#include <stdio.h>
#include <time.h>
#include <string.h>
#include <bip39.h>
#include <bip32.h>
#include <ecdsa.h>

char passphrase[256];
uint8_t seed[512 / 8];
uint8_t addr[21], pubkeyhash[20];
int count = 0, found = 0;
HDNode node;
clock_t start;

// around 120 tries per second

// testing data:
//
// mnemonic:   "all all all all all all all all all all all all"
// address:    "1N3uJ5AU3FTYQ1ZQgTMtYmgSvMBmQiGVBS"
// passphrase: "testing"

int main(int argc, char **argv)
{
	if (argc != 3) {
		fprintf(stderr, "Usage: bip39bruteforce mnemonic address\n");
		return 1;
	}
	const char *mnemonic = argv[1];
	const char *address = argv[2];
	if (!mnemonic_check(mnemonic)) {
		fprintf(stderr, "\"%s\" is not a valid mnemonic\n", mnemonic);
		return 2;
	}
	if (!ecdsa_address_decode(address, addr)) {
		fprintf(stderr, "\"%s\" is not a valid address\n", address);
		return 3;
	}
	printf("Reading passphrases from stdin ...\n");
	start = clock();
	for (;;) {
		if (fgets(passphrase, 256, stdin) == NULL) break;
		int len = strlen(passphrase);
		if (len <= 0) {
			continue;
		}
		count++;
		passphrase[len - 1] = 0;
		mnemonic_to_seed(mnemonic, passphrase, seed, NULL);
		hdnode_from_seed(seed, 512 / 8, &node);
		hdnode_private_ckd_prime(&node, 44);
		hdnode_private_ckd_prime(&node, 0);
		hdnode_private_ckd_prime(&node, 0);
		hdnode_private_ckd(&node, 0);
		hdnode_private_ckd(&node, 0);
		ecdsa_get_pubkeyhash(node.public_key, pubkeyhash);
		if (memcmp(addr + 1, pubkeyhash, 20) == 0) {
			found = 1;
			break;
		}
	}
	float dur = (float)(clock() - start) / CLOCKS_PER_SEC;
	printf("Tried %d passphrases in %f seconds = %f tries/second\n", count, dur, (float)count/dur);
	if (found) {
		printf("Correct passphrase found! :-)\n\"%s\"\n", passphrase);
		return 0;
	}
	printf("Correct passphrase not found. :-(\n");
	return 4;
}
