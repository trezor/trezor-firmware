/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "seal.h"
#include "aes/aes.h"
#if VAULT_SEAL_MODE == VAULT_SEAL_AES_GCM
#include "aes/aesgcm.h"
#elif VAULT_SEAL_MODE == VAULT_SEAL_AES_SIV
#include "siv.h"
#endif
#include "memzero.h"
#include "timing.h"
#ifdef VAULT_TIMING
vault_timing_t vault_timing;
#endif
#if defined(VAULT_TEST)
#include "keywrap.h"
/* Tests inject AES and entropy, never the production binary. */
extern bool vault_wrap_block(bool encrypt, const uint8_t in[16],
                             uint8_t out[16]);
extern void vault_random(void *dest, size_t len);
#elif !defined(USE_VAULT_KEK)
#include <sec/rng_strong.h>
#include "keywrap.h"
/* Emulator and F4 (no SAES): the wrapping key lives in ordinary RAM. On F4
 * that is MPU-protected kernel RAM; in the emulator it is process RAM. */
static uint8_t soft_kek[32];
static bool soft_kek_ready;
static bool vault_wrap_block(bool encrypt, const uint8_t in[16],
                             uint8_t out[16]) {
  if (!soft_kek_ready) {
    rng_fill_buffer_strong(soft_kek, sizeof(soft_kek));
    soft_kek_ready = true;
  }
  bool ok;
  if (encrypt) {
    aes_encrypt_ctx ctx = {0};
    ok = aes_encrypt_key256(soft_kek, &ctx) == 0 &&
         aes_encrypt(in, out, &ctx) == 0;
    memzero(&ctx, sizeof(ctx));
  } else {
    aes_decrypt_ctx ctx = {0};
    ok = aes_decrypt_key256(soft_kek, &ctx) == 0 &&
         aes_decrypt(in, out, &ctx) == 0;
    memzero(&ctx, sizeof(ctx));
  }
  return ok;
}
#define vault_random rng_fill_buffer_strong
#else
#include <sec/rng_strong.h>
#include <sec/vault_kek.h>
#define vault_random rng_fill_buffer_strong
#endif

static bool vault_kek(bool encrypt, uint8_t value[40]) {
#if defined(VAULT_TEST) || !defined(USE_VAULT_KEK)
  return vault_keywrap(encrypt, value, vault_wrap_block);
#else
  /* The BHK never leaves SAES. The whole key wrap runs in the secure world,
   * via an smcall when secmon owns SAES, with no per-block AES oracle. */
  return vault_kek_wrap(encrypt, value) == sectrue;
#endif
}

static uint8_t wrapped_dek[40 * VAULT_KEY_COUNT];
static bool key_ready, key_active;
#if VAULT_SEAL_MODE == VAULT_SEAL_AES_GCM
static gcm_ctx record_ctx;
#elif VAULT_SEAL_MODE == VAULT_SEAL_AES_SIV
static vault_siv_ctx record_ctx;
#else
/* ECB operations need only one direction at a time. Re-unwrap on a direction
 * change rather than retaining both expanded schedules in kernel RAM. */
static union {
  aes_encrypt_ctx encrypt;
  aes_decrypt_ctx decrypt;
} record_ctx;
static bool key_encrypt_active;
#endif

void vault_seal_end(void) {
  memzero(&record_ctx, sizeof(record_ctx));
  key_active = false;
}
void vault_seal_wipe(void) {
  vault_seal_end();
  memzero(wrapped_dek, sizeof(wrapped_dek));
  key_ready = false;
#if !defined(USE_VAULT_KEK) && !defined(VAULT_TEST)
  memzero(soft_kek, sizeof(soft_kek));
  soft_kek_ready = false;
#endif
}
bool vault_seal_ready(void) { return key_ready; }
bool vault_seal_idle(void) {
  volatile uint8_t residue = key_active;
  for (size_t i = 0; i < sizeof(record_ctx); i++)
    residue |= ((const uint8_t *)&record_ctx)[i];
  return !residue;
}
static bool vault_seal_begin(bool encrypt) {
#if VAULT_SEAL_MODE == VAULT_SEAL_AES_ECB
  if (key_active && key_encrypt_active == encrypt) return true;
  vault_seal_end();
#else
  (void)encrypt;
  if (key_active) return true;
#endif
  uint8_t key[40 * VAULT_KEY_COUNT] = {0};
  bool ok = false;
  uint32_t start = 0;
  if (!key_ready) {
    for (size_t i = 0; i < VAULT_KEY_COUNT; i++) {
      vault_random(key + 40 * i + 8, 32);
      if (!vault_kek(true, key + 40 * i)) goto cleanup;
    }
    memcpy(wrapped_dek, key, sizeof(key));
    key_ready = true;
  }
  memcpy(key, wrapped_dek, sizeof(key));
  start = vault_cycles();
  for (size_t i = 0; i < VAULT_KEY_COUNT; i++)
    if (!vault_kek(false, key + 40 * i)) goto cleanup;
  VAULT_TIMING_ADD(unwrap, start);
  start = vault_cycles();
#if VAULT_SEAL_MODE == VAULT_SEAL_AES_GCM
  if (gcm_init_and_key(key + 8, 32, &record_ctx) != RETURN_GOOD) goto cleanup;
#elif VAULT_SEAL_MODE == VAULT_SEAL_AES_SIV
  if (aes_encrypt_key256(key + 8, &record_ctx.mac) != 0 ||
      aes_encrypt_key256(key + 48, &record_ctx.ctr) != 0)
    goto cleanup;
#else
  if ((encrypt ? aes_encrypt_key256(key + 8, &record_ctx.encrypt)
               : aes_decrypt_key256(key + 8, &record_ctx.decrypt)) != 0)
    goto cleanup;
  key_encrypt_active = encrypt;
#endif
  VAULT_TIMING_ADD(expand, start);
  key_active = true;
  ok = true;
cleanup:
  memzero(key, sizeof(key));
  if (!ok) vault_seal_wipe();
  return ok;
}
bool vault_seal_record(bool encrypt, uint64_t nonce,
                       const uint8_t aad[VAULT_AAD_SIZE],
                       uint8_t data[VAULT_RECORD_SIZE], size_t length,
                       uint8_t tag[16]) {
  if (!length || length > VAULT_RECORD_SIZE || !vault_seal_begin(encrypt))
    return false;
  uint32_t start = vault_cycles();
#if VAULT_SEAL_MODE == VAULT_SEAL_AES_GCM
  uint8_t iv[12] = {'S', 'V', '0', '1'};
  for (size_t i = 0; i < 8; i++) iv[4 + i] = nonce >> (56 - 8 * i);
  int ret = encrypt ? gcm_encrypt_message(iv, sizeof(iv), aad, VAULT_AAD_SIZE,
                                          data, length, tag, 16, &record_ctx)
                    : gcm_decrypt_message(iv, sizeof(iv), aad, VAULT_AAD_SIZE,
                                          data, length, tag, 16, &record_ctx);
  bool ok = ret == RETURN_GOOD;
#elif VAULT_SEAL_MODE == VAULT_SEAL_AES_SIV
  (void)nonce;
  bool ok = vault_siv_record(&record_ctx, encrypt, aad, VAULT_AAD_SIZE, data,
                             length, tag);
#else
  (void)nonce;
  (void)aad;
  (void)tag;
  bool ok = length % 16 == 0;
  for (size_t offset = 0; ok && offset < length; offset += 16) {
    ok = (encrypt
              ? aes_encrypt(data + offset, data + offset, &record_ctx.encrypt)
              : aes_decrypt(data + offset, data + offset,
                            &record_ctx.decrypt)) == 0;
  }
#endif
  VAULT_TIMING_ADD(record, start);
#ifdef VAULT_TIMING
  vault_timing.records++;
#endif
  if (!ok) {
    memzero(data, VAULT_RECORD_SIZE);
    return false;
  }
  return true;
}
