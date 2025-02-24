#include "mlkem.h"

#include "rand.h"

void randombytes(uint8_t *out, size_t outlen) { random_buffer(out, outlen); }

int mlkem_generate_keypair(
    uint8_t encapsulation_key[MLKEM_ENCAPSULATION_KEY_SIZE],
    uint8_t decapsulation_key[MLKEM_DECAPSULATION_KEY_SIZE]) {
  return crypto_kem_keypair(encapsulation_key, decapsulation_key);
}

int mlkem_encapsulate(
    uint8_t ciphertext[MLKEM_CIPHERTEXT_SIZE],
    uint8_t shared_secret[MLKEM_SHARED_SECRET_SIZE],
    const uint8_t encapsulation_key[MLKEM_ENCAPSULATION_KEY_SIZE]) {
  return crypto_kem_enc(ciphertext, shared_secret, encapsulation_key);
}

int mlkem_decapsulate(
    uint8_t shared_secret[MLKEM_SHARED_SECRET_SIZE],
    const uint8_t ciphertext[MLKEM_CIPHERTEXT_SIZE],
    const uint8_t decapsulation_key[MLKEM_DECAPSULATION_KEY_SIZE]) {
  return crypto_kem_dec(shared_secret, ciphertext, decapsulation_key);
}
