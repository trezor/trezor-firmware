/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifdef SECURE_MODE
#if defined(VAULT_SEAL_HW)
#error "Select a record-sealing feature before enabling hardware records"
#endif

#include <trezor_bsp.h>

#include <sec/rng_strong.h>
#include <sec/secure_aes.h>
#include <sec/vault_kek.h>
#include <sys/systick.h>

#include "../../vault/inc/sec/vault_mode.h"
#include "../../vault/keywrap.h"

static bool vault_kek_block(bool encrypt, const uint8_t in[16],
                            uint8_t out[16]) {
  /* BHK is held in locked backup registers/SAES and never leaves them. */
  return (encrypt ? secure_aes_ecb_encrypt_hw(in, 16, out, SECURE_AES_KEY_BHK)
                  : secure_aes_ecb_decrypt_hw(in, 16, out,
                                              SECURE_AES_KEY_BHK)) == sectrue;
}

/* secret_bhk_load() fills the BHK registers with zeros when the secret area
 * cannot be read. Refuse to wrap under that key instead of failing open:
 * AES-256 of a zero block under the all-zero key is a fixed value. */
static bool vault_kek_present(void) {
  static const uint8_t zero_key_block[16] = {0xdc, 0x95, 0xc0, 0x78, 0xa2, 0x40,
                                             0x89, 0x89, 0xad, 0x48, 0xa2, 0x14,
                                             0x92, 0x84, 0x20, 0x87};
  static bool present = false;
  if (present) return true;
  uint8_t block[16] = {0};
  bool ok = vault_kek_block(true, block, block) &&
            memcmp(block, zero_key_block, sizeof(block)) != 0;
  memzero(block, sizeof(block));
  present = ok;
  return ok;
}

secbool vault_kek_wrap(bool encrypt, uint8_t value[40]) {
  bool ok = secure_aes_init() == sectrue && vault_kek_present() &&
            vault_keywrap(encrypt, value, vault_kek_block);
  /* Reset SAES data/key registers on both success and failure. Leave the
   * peripheral initialized for existing users of the secure_aes interface. */
  if (secure_aes_init() != sectrue) ok = false;
  if (!ok) memzero(value, 40);
  return ok ? sectrue : secfalse;
}

/* ------------------------------------------------------------------------- */
/* SAES record sealing */

#define SAES_TIMEOUT 100

/* Per-boot keys, wrapped under DHUK by SAES itself: one for vault records,
 * one for the storage key cache. Only the record key is reachable by smcall. */
typedef struct {
  uint32_t wrapped[8];
  bool ready;
} saes_key_t;
static saes_key_t storage_key;

/* HAL_CRYP_Init starts DHUK loading but does not wait for that load.
 * WrapKey/UnwrapKey enable SAES directly, so their callers must wait first. */
static bool saes_wait_key(CRYP_HandleTypeDef* h) {
  uint32_t deadline = ticks_timeout(SAES_TIMEOUT);
  for (;;) {
    uint32_t errors = SAES->ISR;
    if (errors & (AES_ISR_KEIF | AES_ISR_RNGEIF)) {
      h->ErrorCode |=
          (errors & AES_ISR_KEIF) ? HAL_CRYP_ERROR_KEY : HAL_CRYP_ERROR_RNG;
      return false;
    }
    uint32_t status = SAES->SR;
    if (!(status & AES_SR_BUSY) && (status & AES_SR_KEYVALID)) return true;
    if (ticks_expired(deadline)) {
      h->ErrorCode |= HAL_CRYP_ERROR_TIMEOUT;
      return false;
    }
  }
}

static bool saes_setup(CRYP_HandleTypeDef* h, uint32_t key_mode,
                       uint32_t key_select, uint32_t algorithm) {
  memset(h, 0, sizeof(*h));
  h->Instance = SAES;
  h->Init.DataType = CRYP_NO_SWAP;
  h->Init.KeySize = CRYP_KEYSIZE_256B;
  h->Init.KeySelect = key_select;
  h->Init.KeyMode = key_mode;
  h->Init.Algorithm = algorithm;
  h->Init.DataWidthUnit = CRYP_DATAWIDTHUNIT_BYTE;
  h->Init.HeaderWidthUnit = CRYP_HEADERWIDTHUNIT_BYTE;
  h->Init.KeyIVConfigSkip = CRYP_KEYIVCONFIG_ALWAYS;
  return HAL_CRYP_Init(h) == HAL_OK && saes_wait_key(h);
}

static bool saes_key_valid(void) {
  return (SAES->SR & AES_SR_KEYVALID) == AES_SR_KEYVALID;
}

/* Load a key into the SAES key registers without exposing it. */
static bool saes_load_key(CRYP_HandleTypeDef* h, saes_key_t* key) {
  return saes_setup(h, CRYP_KEYMODE_WRAPPED, CRYP_KEYSEL_HW, CRYP_AES_ECB) &&
         HAL_CRYPEx_UnwrapKey(h, key->wrapped, SAES_TIMEOUT) == HAL_OK &&
         saes_key_valid();
}

/* Keep the unwrapped key in SAES while selecting the ordinary ECB cipher. */
static bool saes_cipher_key(CRYP_HandleTypeDef* handle, saes_key_t* key) {
  CRYP_ConfigTypeDef conf = {0};
  if (!saes_load_key(handle, key) ||
      HAL_CRYP_GetConfig(handle, &conf) != HAL_OK)
    return false;
  conf.Algorithm = CRYP_AES_ECB;
  conf.KeyMode = CRYP_KEYMODE_NORMAL;
  conf.KeySelect = CRYP_KEYSEL_NORMAL;
  conf.pKey = NULL;
  conf.KeyIVConfigSkip = CRYP_KEYNOCONFIG;
  return HAL_CRYP_SetConfig(handle, &conf) == HAL_OK && saes_key_valid();
}

static uint32_t saes_be32(const uint8_t* p) {
  return (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 |
         p[3];
}
static void saes_put_be32(uint8_t* p, uint32_t value) {
  for (size_t i = 0; i < 4; i++) p[i] = value >> (24 - 8 * i);
}

/* U5 SAES supports ECB/CBC, not GCM. Use its ECB encryption primitive for
 * GCM's counter blocks and hash subkey; the AES key never leaves SAES. */
static bool saes_block(CRYP_HandleTypeDef* h, const uint8_t in[16],
                       uint8_t out[16]) {
  uint32_t input[4], output[4] = {0};
  for (size_t i = 0; i < 4; i++) input[i] = saes_be32(in + 4 * i);
  bool ok = HAL_CRYP_Encrypt(h, input, 16, output, SAES_TIMEOUT) == HAL_OK;
  if (ok)
    for (size_t i = 0; i < 4; i++) saes_put_be32(out + 4 * i, output[i]);
  memzero(input, sizeof(input));
  memzero(output, sizeof(output));
  return ok;
}

/* U5 has ECB/CBC only. A future native-GCM MCU supplies the same provider
 * contract from its own driver, without changing record layout or key owners.
 */
#ifdef VAULT_NATIVE_GCM
#error "The STM32U5 SAES backend does not implement native GCM"
#endif
#include "../../vault/gcm.h"
#include "../../vault/record_backend.h"
static bool saes_gcm_block(const void* context, bool encrypt,
                           const uint8_t in[16], uint8_t out[16]) {
  return encrypt && saes_block((CRYP_HandleTypeDef*)context, in, out);
}
static uint32_t saes_gcm(saes_key_t* key, vault_saes_request_t* r) {
  CRYP_HandleTypeDef handle;
  const vault_cipher_provider_t cipher = {
      .context = &handle,
      .block = saes_gcm_block,
  };
  uint32_t result = VAULT_SAES_FAILED;
  if (saes_cipher_key(&handle, key))
    result = vault_gcm_cipher_record(&cipher, r);
  memzero(&handle, sizeof(handle));
  if (secure_aes_init() != sectrue) result = VAULT_SAES_FAILED;
  if (result != VAULT_SAES_OK) memzero(r->data, sizeof(r->data));
  return result;
}

static void saes_key_drop(saes_key_t* key) {
  memzero(key->wrapped, sizeof(key->wrapped));
  key->ready = false;
}

/* Generate and wrap a new key, then check it with a round trip. */
static bool saes_key_create(saes_key_t* key) {
  uint32_t plain[8] = {0};
  CRYP_HandleTypeDef h;
  rng_fill_buffer_strong(plain, sizeof(plain));
  bool ok =
      saes_setup(&h, CRYP_KEYMODE_WRAPPED, CRYP_KEYSEL_HW, CRYP_AES_ECB) &&
      HAL_CRYPEx_WrapKey(&h, plain, key->wrapped, SAES_TIMEOUT) == HAL_OK;
  memzero(plain, sizeof(plain));
  if (secure_aes_init() != sectrue) ok = false;
  if (!ok) {
    saes_key_drop(key);
    return false;
  }
  key->ready = true;

  /* A key that did not reach the key registers fails here, not later. */
  vault_saes_request_t probe = {.op = VAULT_SAES_SEAL, .length = 16};
  memset(probe.data, 0x5c, 16);
  ok = saes_gcm(key, &probe) == VAULT_SAES_OK;
  bool changed = false;
  for (size_t i = 0; i < 16; i++) changed |= probe.data[i] != 0x5c;
  probe.op = VAULT_SAES_OPEN;
  ok = ok && changed && saes_gcm(key, &probe) == VAULT_SAES_OK;
  for (size_t i = 0; ok && i < 16; i++) ok = probe.data[i] == 0x5c;
  memzero(&probe, sizeof(probe));
  if (!ok) saes_key_drop(key);
  return ok;
}

#if !PRODUCTION

/* Independent AES-256-GCM vectors: zero key, IV 00..0b, AAD 01..20,
 * plaintext byte i = 3 + 17*i. Exercise full and partial blocks on hardware. */
static bool saes_known_answer(void) {
  static bool passed;
  if (passed) return true;
  static const uint16_t lengths[] = {1, 15, 16, 17, 139, 160};
  static const uint8_t ciphertext[160] = {
      0x8b, 0xdf, 0x16, 0x64, 0x47, 0xa5, 0xe6, 0x83, 0x49, 0xe4, 0xff, 0x5b,
      0x32, 0xe3, 0x2f, 0x0e, 0x47, 0x48, 0x9d, 0xdc, 0xe8, 0xf5, 0xf6, 0x7c,
      0x54, 0x67, 0x59, 0xc5, 0x52, 0xc5, 0x0e, 0x7d, 0xcf, 0xc3, 0xf9, 0xf3,
      0x2b, 0x1f, 0xb8, 0x66, 0x93, 0x6c, 0x00, 0x54, 0x41, 0xbd, 0x5f, 0x20,
      0x07, 0xb0, 0xc2, 0x9c, 0x90, 0x05, 0x14, 0x74, 0x17, 0x35, 0x80, 0xad,
      0xed, 0x9a, 0x92, 0x94, 0xc3, 0x60, 0x8f, 0xa5, 0x14, 0xd8, 0xb3, 0x16,
      0x8d, 0x07, 0x44, 0x6b, 0xfe, 0x78, 0x8d, 0x75, 0x2c, 0x91, 0x92, 0x86,
      0x39, 0xad, 0x6d, 0x8a, 0xec, 0x3e, 0x52, 0x63, 0x33, 0xee, 0xc0, 0x44,
      0xc2, 0x74, 0x3e, 0xb7, 0x73, 0x0b, 0xd7, 0x0b, 0xf4, 0x58, 0x12, 0x29,
      0xca, 0x74, 0x27, 0x58, 0x0d, 0xda, 0x17, 0xaf, 0x64, 0xe3, 0x49, 0x6d,
      0x9a, 0xfa, 0x7a, 0x65, 0x9d, 0xf1, 0x5f, 0x94, 0xf3, 0x06, 0xc0, 0x85,
      0x9f, 0xf8, 0x0e, 0x95, 0x98, 0x78, 0x57, 0x89, 0xac, 0x41, 0xd5, 0xf7,
      0x6b, 0xc3, 0x4d, 0x94, 0xac, 0x50, 0xba, 0x8e, 0x09, 0xb9, 0xb8, 0x27,
      0xaf, 0x8b, 0x97, 0xff};
  static const uint8_t tags[6][16] = {
      {0x2f, 0xac, 0xe1, 0x61, 0x10, 0x60, 0xa5, 0x21, 0x3e, 0x9c, 0xef, 0x49,
       0xa6, 0x40, 0xdf, 0x2f},
      {0xbd, 0x08, 0xef, 0xc9, 0x19, 0x26, 0xe2, 0x16, 0x9e, 0x28, 0x54, 0x6b,
       0xfd, 0x6e, 0x2e, 0xe4},
      {0xee, 0x0e, 0xff, 0xed, 0x62, 0x40, 0xf0, 0x27, 0xbd, 0x90, 0x42, 0x4e,
       0xec, 0x1d, 0xea, 0xf2},
      {0x88, 0xe2, 0xf3, 0x8c, 0xa2, 0x43, 0x47, 0xda, 0xdc, 0xf3, 0x04, 0xd3,
       0xdf, 0x4a, 0xdb, 0xdf},
      {0x19, 0x1b, 0xf2, 0x1a, 0x2a, 0x92, 0x26, 0x55, 0x8f, 0xc6, 0x61, 0xa5,
       0xcd, 0x08, 0x61, 0x20},
      {0xb7, 0x39, 0x8f, 0x48, 0x8b, 0x97, 0x43, 0xdb, 0x02, 0xbd, 0xa8, 0x0c,
       0x7d, 0xa8, 0x83, 0x46}};
  saes_key_t key = {0};
  uint32_t plain[8] = {0};
  CRYP_HandleTypeDef handle;
  bool ok =
      saes_setup(&handle, CRYP_KEYMODE_WRAPPED, CRYP_KEYSEL_HW, CRYP_AES_ECB) &&
      HAL_CRYPEx_WrapKey(&handle, plain, key.wrapped, SAES_TIMEOUT) == HAL_OK;
  memzero(plain, sizeof(plain));
  if (secure_aes_init() != sectrue) ok = false;
  ensure_true(ok, "SAES self-test: key wrap");
  for (size_t test = 0; test < sizeof(lengths) / sizeof(lengths[0]); test++) {
    vault_saes_request_t probe = {.op = VAULT_SAES_SEAL,
                                  .length = lengths[test]};
    for (size_t i = 0; i < sizeof(probe.iv); i++) probe.iv[i] = i;
    for (size_t i = 0; i < sizeof(probe.aad); i++) probe.aad[i] = i + 1;
    for (size_t i = 0; i < probe.length; i++) probe.data[i] = 3 + 17 * i;
    ok = saes_gcm(&key, &probe) == VAULT_SAES_OK;
    ensure_true(ok, "SAES self-test: GCM seal");
    ok = memcmp(probe.data, ciphertext, probe.length) == 0 &&
         memcmp(probe.tag, tags[test], sizeof(tags[test])) == 0;
    ensure_true(ok, "SAES self-test: known answer");
    probe.op = VAULT_SAES_OPEN;
    probe.data[probe.length - 1] ^= 1;
    ok = saes_gcm(&key, &probe) == VAULT_SAES_AUTH_FAILED &&
         memcmp(probe.data, (uint8_t[VAULT_SAES_RECORD_SIZE]){0},
                sizeof(probe.data)) == 0;
    ensure_true(ok, "SAES self-test: bad ciphertext");
    memcpy(probe.data, ciphertext, probe.length);
    ok = saes_gcm(&key, &probe) == VAULT_SAES_OK;
    for (size_t i = 0; ok && i < probe.length; i++)
      ok = probe.data[i] == (uint8_t)(3 + 17 * i);
    ensure_true(ok, "SAES self-test: GCM open");
    memcpy(probe.data, ciphertext, probe.length);
    probe.tag[0] ^= 1;
    ok = saes_gcm(&key, &probe) == VAULT_SAES_AUTH_FAILED &&
         memcmp(probe.data, (uint8_t[VAULT_SAES_RECORD_SIZE]){0},
                sizeof(probe.data)) == 0;
    ensure_true(ok, "SAES self-test: bad tag");
    memzero(&probe, sizeof(probe));
  }
  saes_key_drop(&key);
  passed = ok;
  return ok;
}
#endif

static uint32_t saes_request(saes_key_t* key, vault_saes_request_t* r) {
  if (r->op == VAULT_SAES_RESET) {
    saes_key_drop(key);
    return VAULT_SAES_OK;
  }
  if ((r->op != VAULT_SAES_SEAL && r->op != VAULT_SAES_OPEN) || !r->length ||
      r->length > VAULT_SAES_RECORD_SIZE) {
    memzero(r->data, sizeof(r->data));
    return VAULT_SAES_FAILED;
  }
  if (secure_aes_init() != sectrue
#if !PRODUCTION
      || !saes_known_answer()
#endif
      || (!key->ready && !saes_key_create(key))) {
    memzero(r->data, sizeof(r->data));
    return VAULT_SAES_FAILED;
  }
  return saes_gcm(key, r);
}

uint32_t vault_saes_record(vault_saes_request_t* r) {
  memzero(r->data, sizeof(r->data));
  return VAULT_SAES_FAILED;
}

uint32_t vault_saes_storage(vault_saes_request_t* r) {
  return saes_request(&storage_key, r);
}

#endif  // SECURE_MODE
