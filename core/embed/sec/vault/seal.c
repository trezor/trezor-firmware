/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "seal.h"
#include "aes/aes.h"
#include "memzero.h"
#include "timing.h"
#ifdef VAULT_TIMING
vault_timing_t vault_timing;
#endif

/* SAES records use the selected cipher; saes-gcm is the U5 default.
 * Software sealing below is only for builds that do not select SAES. Native
 * tests substitute vault_saes_record(). */
#if defined(VAULT_SEAL_HW) && !defined(USE_VAULT_KEK) && !defined(VAULT_TEST)
/* Never fall back to a RAM-held key when hardware sealing was selected. */
#error "VAULT_SEAL_HW requires USE_VAULT_KEK"
#endif
#if defined(VAULT_SEAL_HW) && (defined(USE_VAULT_KEK) || defined(VAULT_TEST))
#include <sec/vault_kek.h>

_Static_assert(VAULT_SAES_RECORD_SIZE == VAULT_RECORD_SIZE, "record size");
_Static_assert(VAULT_SAES_AAD_SIZE == VAULT_AAD_SIZE, "AAD size");

/* False after a hardware or key failure; the next wipe makes a new key. */
static bool saes_ready = true;
/* The record key may live in secmon, which can outlive this kernel; the
 * nonce counter lives here. Replace the key before the first record of every
 * kernel run, so a restarted counter never meets an old key. */
static bool saes_fresh;

void vault_seal_end(void) {}
void vault_seal_wipe(void) {
  vault_saes_request_t r = {.abi = VAULT_CIPHER_REQUEST_ABI,
                            .op = VAULT_SAES_RESET};
  saes_ready = vault_saes_record(&r) == VAULT_SAES_OK;
  saes_fresh = saes_ready;
}
bool vault_seal_ready(void) { return saes_ready; }
/* No record key or expanded schedule ever exists in kernel RAM. */
bool vault_seal_idle(void) { return true; }

bool vault_seal_record(bool encrypt, uint64_t nonce,
                       const uint8_t aad[VAULT_AAD_SIZE],
                       uint8_t data[VAULT_RECORD_SIZE], size_t length,
                       uint8_t tag[VAULT_TAG_BUFFER_SIZE]) {
  if (!length || length > VAULT_RECORD_SIZE || !saes_ready) return false;
  if (!saes_fresh) {
    vault_seal_wipe();
    if (!saes_ready) return false;
  }
  vault_saes_request_t r = {
      .abi = VAULT_CIPHER_REQUEST_ABI,
      .op = encrypt ? VAULT_SAES_SEAL : VAULT_SAES_OPEN,
      .length = length,
      .iv = {'S', 'V', '0', '1'},
  };
  for (size_t i = 0; i < 8; i++) r.iv[4 + i] = nonce >> (56 - 8 * i);
  memcpy(r.aad, aad, VAULT_AAD_SIZE);
  memcpy(r.data, data, length);
  if (!encrypt) memcpy(r.tag, tag, sizeof(r.tag));
  uint32_t start = vault_cycles();
  uint32_t result = vault_saes_record(&r);
  VAULT_TIMING_ADD(record, start);
#ifdef VAULT_TIMING
  vault_timing.records++;
#endif
  bool ok = result == VAULT_SAES_OK;
  /* A tag mismatch is the caller's data; anything else is the key's. */
  if (!ok && result != VAULT_SAES_AUTH_FAILED) saes_ready = false;
  if (ok) {
    memcpy(data, r.data, length);
    if (encrypt) memcpy(tag, r.tag, sizeof(r.tag));
  } else {
    memzero(data, VAULT_RECORD_SIZE);
  }
  memzero(&r, sizeof(r));
  return ok;
}

#else  // software sealing
#include "siv.h"
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
static vault_siv_ctx record_ctx;

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
  (void)encrypt;
  if (key_active) return true;
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
  if (aes_encrypt_key256(key + 8, &record_ctx.mac) != 0 ||
      aes_encrypt_key256(key + 48, &record_ctx.ctr) != 0)
    goto cleanup;
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
                       uint8_t tag[VAULT_TAG_BUFFER_SIZE]) {
  if (!length || length > VAULT_RECORD_SIZE || !vault_seal_begin(encrypt))
    return false;
  uint32_t start = vault_cycles();
  (void)nonce;
  bool ok = vault_siv_record(&record_ctx, encrypt, aad, VAULT_AAD_SIZE, data,
                             length, tag);
  VAULT_TIMING_ADD(record, start);
#ifdef VAULT_TIMING
  vault_timing.records++;
#endif
#if !VAULT_CACHE_RECORD_CONTEXT
  vault_seal_end();
#endif
  if (!ok) {
    memzero(data, VAULT_RECORD_SIZE);
    return false;
  }
  return true;
}

#endif  // software sealing
