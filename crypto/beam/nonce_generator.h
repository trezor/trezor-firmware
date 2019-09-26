#ifndef _NONCE_GENERATOR_H_
#define _NONCE_GENERATOR_H_

#include "../hmac.h"
#include "definitions.h"
#include "internal.h"

typedef struct {
  HMAC_SHA256_CTX hash;
  uint8_t prk[32];
  uint8_t okm[32];
  uint8_t number;
} nonce_generator_t;

int is_scalar_valid(uint8_t *scalar);

void nonce_generator_init(nonce_generator_t *nonce, const uint8_t *salt,
                          uint8_t salt_size);

void nonce_generator_write(nonce_generator_t *nonce, const uint8_t *seed,
                           uint8_t seed_size);

void nonce_generator_get_first_output_key_material(nonce_generator_t *nonce,
                                                   const uint8_t *context,
                                                   size_t context_size);

void nonce_generator_get_rest_output_key_material(nonce_generator_t *nonce,
                                                  const uint8_t *context,
                                                  size_t context_size);

uint8_t nonce_generator_export_output_key(nonce_generator_t *nonce,
                                          const uint8_t *context,
                                          uint8_t context_size, uint8_t *okm32);

uint8_t nonce_generator_export_scalar(nonce_generator_t *nonce,
                                      const uint8_t *context,
                                      uint8_t context_size,
                                      secp256k1_scalar *out_scalar);

#endif  // _NONCE_GENERATOR_H_