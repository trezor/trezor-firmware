/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <sec/vault_cipher.h>
#include <string.h>
#include "consteq.h"
#include "memzero.h"

static inline void vault_gcm_put_be32(uint8_t *p, uint32_t value) {
  for (size_t i = 0; i < 4; i++) p[i] = value >> (24 - 8 * i);
}

static inline uint32_t vault_gcm_get_be32(const uint8_t *p) {
  return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 |
         p[3];
}

/* Fixed-work GHASH multiplication in GF(2^128) (SP 800-38D, Algorithm 1) on
 * big-endian 32-bit words, with no secret-indexed tables or branches. Both the
 * subkey and intermediate products are erased. */
static void vault_gcm_hash_multiply(uint8_t value[16], const uint8_t h[16]) {
  uint32_t x[4], z[4] = {0}, v[4];
  for (size_t i = 0; i < 4; i++) {
    x[i] = vault_gcm_get_be32(value + 4 * i);
    v[i] = vault_gcm_get_be32(h + 4 * i);
  }
  for (size_t bit = 0; bit < 128; bit++) {
    uint32_t mask = 0U - ((x[bit / 32] >> (31 - bit % 32)) & 1U);
    for (size_t i = 0; i < 4; i++) z[i] ^= v[i] & mask;
    uint32_t reduce = 0U - (v[3] & 1U);
    v[3] = (v[3] >> 1) | (v[2] << 31);
    v[2] = (v[2] >> 1) | (v[1] << 31);
    v[1] = (v[1] >> 1) | (v[0] << 31);
    v[0] = (v[0] >> 1) ^ (0xe1000000U & reduce);
  }
  for (size_t i = 0; i < 4; i++) vault_gcm_put_be32(value + 4 * i, z[i]);
  memzero(x, sizeof(x));
  memzero(z, sizeof(z));
  memzero(v, sizeof(v));
}
static void vault_gcm_hash(uint8_t value[16], const uint8_t h[16],
                           const uint8_t *data, size_t length) {
  for (size_t offset = 0; offset < length; offset += 16) {
    size_t n = length - offset;
    if (n > 16) n = 16;
    for (size_t i = 0; i < n; i++) value[i] ^= data[offset + i];
    vault_gcm_hash_multiply(value, h);
  }
}

static inline uint32_t vault_gcm_ecb_record(
    const vault_cipher_provider_t *cipher, vault_cipher_request_t *r) {
  uint8_t output[VAULT_CIPHER_RECORD_SIZE] = {0};
  uint8_t h[16] = {0}, hash[16] = {0}, counter[16] = {0};
  uint8_t mask[16] = {0}, tag[16] = {0};
  uint32_t result = VAULT_CIPHER_FAILED;
  bool encrypt = r->op == VAULT_CIPHER_SEAL;
  if (!cipher->block || !cipher->block(cipher->context, true, counter, h))
    goto cleanup;

  memcpy(counter, r->iv, sizeof(r->iv));
  vault_gcm_put_be32(counter + 12, 1);
  if (!cipher->block(cipher->context, true, counter, mask)) goto cleanup;

  /* Authenticate ciphertext before producing any plaintext on OPEN. */
  if (encrypt) {
    for (size_t offset = 0; offset < r->length; offset += 16) {
      vault_gcm_put_be32(counter + 12, 2 + offset / 16);
      if (!cipher->block(cipher->context, true, counter, tag)) goto cleanup;
      size_t n = r->length - offset;
      if (n > 16) n = 16;
      for (size_t i = 0; i < n; i++)
        output[offset + i] = r->data[offset + i] ^ tag[i];
    }
  }
  vault_gcm_hash(hash, h, r->aad, sizeof(r->aad));
  vault_gcm_hash(hash, h, encrypt ? output : r->data, r->length);
  memset(counter, 0, sizeof(counter));
  vault_gcm_put_be32(counter + 4, sizeof(r->aad) * 8);
  vault_gcm_put_be32(counter + 12, r->length * 8);
  vault_gcm_hash(hash, h, counter, sizeof(counter));
  for (size_t i = 0; i < 16; i++) tag[i] = hash[i] ^ mask[i];
  if (encrypt) {
    memcpy(r->tag, tag, sizeof(tag));
  } else {
    volatile uint8_t diff = 0;
    for (size_t i = 0; i < sizeof(tag); i++) diff |= r->tag[i] ^ tag[i];
    if (diff) {
      result = VAULT_CIPHER_AUTH_FAILED;
      goto cleanup;
    }
    memcpy(counter, r->iv, sizeof(r->iv));
    for (size_t offset = 0; offset < r->length; offset += 16) {
      vault_gcm_put_be32(counter + 12, 2 + offset / 16);
      if (!cipher->block(cipher->context, true, counter, tag)) goto cleanup;
      size_t n = r->length - offset;
      if (n > 16) n = 16;
      for (size_t i = 0; i < n; i++)
        output[offset + i] = r->data[offset + i] ^ tag[i];
    }
    if (diff) { /* an independently skipped branch must not release plaintext */
      result = VAULT_CIPHER_AUTH_FAILED;
      goto cleanup;
    }
  }
  memcpy(r->data, output, r->length);
  result = VAULT_CIPHER_OK;
cleanup:
  memzero(output, sizeof(output));
  memzero(h, sizeof(h));
  memzero(hash, sizeof(hash));
  memzero(counter, sizeof(counter));
  memzero(mask, sizeof(mask));
  memzero(tag, sizeof(tag));
  if (result != VAULT_CIPHER_OK) memzero(r->data, sizeof(r->data));
  return result;
}

/* Native engines (e.g. H5F4 SAES) provide computed authentication tags.
 * Never let a backend expose unauthenticated plaintext in caller memory. */
static inline uint32_t vault_gcm_native_record(
    const vault_cipher_provider_t *cipher, vault_cipher_request_t *r) {
  uint8_t output[VAULT_CIPHER_RECORD_SIZE] = {0};
  uint8_t tag[VAULT_GCM_TAG_SIZE] = {0};
  bool encrypt = r->op == VAULT_CIPHER_SEAL;
  uint32_t result = VAULT_CIPHER_FAILED;
  volatile uint8_t diff = 0;
  if (!cipher->native_gcm(cipher->context, encrypt, r->iv, r->aad, r->data,
                          r->length, output, tag))
    goto cleanup;
  if (!encrypt) {
    for (size_t i = 0; i < sizeof(tag); i++) diff |= r->tag[i] ^ tag[i];
    if (!consteq(r->tag, tag, sizeof(tag)) || diff) {
      result = VAULT_CIPHER_AUTH_FAILED;
      goto cleanup;
    }
  }
  if (diff) {
    result = VAULT_CIPHER_AUTH_FAILED;
    goto cleanup;
  }
  memcpy(r->data, output, r->length);
  if (encrypt) memcpy(r->tag, tag, sizeof(tag));
  result = VAULT_CIPHER_OK;
cleanup:
  memzero(output, sizeof(output));
  memzero(tag, sizeof(tag));
  return result;
}

static inline uint32_t vault_gcm_cipher_record(
    const vault_cipher_provider_t *cipher, vault_cipher_request_t *r) {
  uint32_t result = VAULT_CIPHER_FAILED;
  if ((r->op == VAULT_CIPHER_SEAL || r->op == VAULT_CIPHER_OPEN) && r->length &&
      r->length <= VAULT_CIPHER_RECORD_SIZE) {
#ifdef VAULT_NATIVE_GCM
    /* A platform advertising native GCM must supply its adapter. */
    if (!cipher->native_gcm) {
      memzero(r->data, sizeof(r->data));
      return VAULT_CIPHER_FAILED;
    }
#endif
    result = cipher->native_gcm ? vault_gcm_native_record(cipher, r)
                                : vault_gcm_ecb_record(cipher, r);
  }
  if (result != VAULT_CIPHER_OK) memzero(r->data, sizeof(r->data));
  return result;
}
