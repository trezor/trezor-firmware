#include "nonce_generator.h"

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "beam/lib/secp256k1-zkp/src/field_impl.h"
#include "beam/lib/secp256k1-zkp/src/group_impl.h"
#include "beam/lib/secp256k1-zkp/src/scalar_impl.h"
#pragma GCC diagnostic pop

const uint8_t scalar_order[] =
    {  // fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141
        0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
        0xFF, 0xFF, 0xFF, 0xFF, 0xFE, 0xBA, 0xAE, 0xDC, 0xE6, 0xAF, 0x48,
        0xA0, 0x3B, 0xBF, 0xD2, 0x5E, 0x8C, 0xD0, 0x36, 0x41, 0x41};

inline int is_scalar_valid(uint8_t *scalar_bytes) {
  return memcmp(scalar_bytes, scalar_order, 32) < 0;
}

inline void nonce_generator_init(nonce_generator_t *nonce, const uint8_t *salt,
                                 uint8_t salt_size) {
  nonce->number = 1;
  memset(nonce->okm, 0, sizeof(nonce->okm));
  memset(nonce->prk, 0, sizeof(nonce->prk));
  hmac_sha256_Init(&nonce->hash, (uint8_t *)salt, salt_size);
}

inline void nonce_generator_write(nonce_generator_t *nonce, const uint8_t *seed,
                                  uint8_t seed_size) {
  hmac_sha256_Update(&nonce->hash, seed, seed_size);
}

inline void nonce_generator_get_first_output_key_material(
    nonce_generator_t *nonce, const uint8_t *context, size_t context_size) {
  hmac_sha256_Final(&nonce->hash, nonce->prk);
  hmac_sha256_Init(&nonce->hash, nonce->prk, 32);

  hmac_sha256_Update(&nonce->hash, context, context_size);
  hmac_sha256_Update(&nonce->hash, &nonce->number, 1);
  hmac_sha256_Final(&nonce->hash, nonce->okm);
}

inline void nonce_generator_get_rest_output_key_material(
    nonce_generator_t *nonce, const uint8_t *context, size_t context_size) {
  hmac_sha256_Init(&nonce->hash, nonce->prk, 32);

  hmac_sha256_Update(&nonce->hash, nonce->okm, 32);
  hmac_sha256_Update(&nonce->hash, context, context_size);
  hmac_sha256_Update(&nonce->hash, &nonce->number, 1);
  hmac_sha256_Final(&nonce->hash, nonce->okm);
}

inline uint8_t nonce_generator_export_output_key(nonce_generator_t *nonce,
                                                 const uint8_t *context,
                                                 uint8_t context_size,
                                                 uint8_t *okm32) {
  if (1 == nonce->number) {
    nonce_generator_get_first_output_key_material(nonce, context, context_size);
  } else {
    nonce_generator_get_rest_output_key_material(nonce, context, context_size);
  }

  if (NULL != okm32) memcpy(okm32, nonce->okm, 32);
  return ++nonce->number;
}

inline uint8_t nonce_generator_export_scalar(nonce_generator_t *nonce,
                                             const uint8_t *context,
                                             uint8_t context_size,
                                             secp256k1_scalar *out_scalar) {
  secp256k1_scalar_clear(out_scalar);
  do {
    nonce_generator_export_output_key(nonce, context, context_size, NULL);
  } while (!scalar_import_nnz(out_scalar, nonce->okm));

  return nonce->number;
}
