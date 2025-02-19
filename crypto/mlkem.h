#ifndef __MLKEM_H__
#define __MLKEM_H__

#include "vendor/mlkem-native/mlkem/kem.h"

#define MLKEM_ENCAPSULATION_KEY_SIZE MLKEM_INDCCA_PUBLICKEYBYTES
#define MLKEM_DECAPSULATION_KEY_SIZE MLKEM_INDCCA_SECRETKEYBYTES
#define MLKEM_CIPHERTEXT_SIZE MLKEM_INDCCA_CIPHERTEXTBYTES
#define MLKEM_SHARED_SECRET_SIZE MLKEM_SSBYTES

int mlkem_generate_keypair(
    uint8_t encapsulation_key[MLKEM_ENCAPSULATION_KEY_SIZE],
    uint8_t decapsulation_key[MLKEM_DECAPSULATION_KEY_SIZE]);

int mlkem_encapsulate(
    uint8_t ciphertext[MLKEM_CIPHERTEXT_SIZE],
    uint8_t shared_secret[MLKEM_SHARED_SECRET_SIZE],
    const uint8_t encapsulation_key[MLKEM_ENCAPSULATION_KEY_SIZE]);

int mlkem_decapsulate(
    uint8_t shared_secret[MLKEM_SHARED_SECRET_SIZE],
    const uint8_t ciphertext[MLKEM_CIPHERTEXT_SIZE],
    const uint8_t decapsulation_key[MLKEM_DECAPSULATION_KEY_SIZE]);
#endif
