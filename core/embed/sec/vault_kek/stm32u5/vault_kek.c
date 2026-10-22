/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifdef SECURE_MODE

#include <trezor_bsp.h>

#include <sec/rng_strong.h>
#include <sec/secure_aes.h>
#include <sec/vault_kek.h>

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
/* SAES record sealing (C3) */

#define SAES_TIMEOUT 100

/* Per-boot keys, wrapped under DHUK by SAES itself: one for vault records,
 * one for the storage key cache. Only the record key is reachable by smcall. */
typedef struct {
  uint32_t wrapped[8];
  bool ready;
} saes_key_t;
static saes_key_t record_key, storage_key;

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
  return HAL_CRYP_Init(h) == HAL_OK;
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

/* One GCM pass with the key already in the key registers. */
static uint32_t saes_gcm(saes_key_t* key, vault_saes_request_t* r) {
  uint32_t data[VAULT_SAES_RECORD_SIZE / 4] = {0};
  uint32_t out[VAULT_SAES_RECORD_SIZE / 4] = {0};
  uint32_t aad[VAULT_SAES_AAD_SIZE / 4] = {0};
  uint32_t tag[4] = {0};
  uint32_t iv[4] = {0};
  memcpy(iv, r->iv, sizeof(r->iv));
  iv[3] = 2; /* J0 counter for a 96-bit IV, as SAES expects */
  memcpy(aad, r->aad, sizeof(aad));
  memcpy(data, r->data, r->length);

  uint32_t result = VAULT_SAES_FAILED;
  CRYP_HandleTypeDef h;
  CRYP_ConfigTypeDef conf = {0};
  bool encrypt = r->op == VAULT_SAES_SEAL;
  if (!saes_load_key(&h, key) || HAL_CRYP_GetConfig(&h, &conf) != HAL_OK)
    goto cleanup;
  conf.Algorithm = CRYP_AES_GCM_GMAC;
  conf.KeyMode = CRYP_KEYMODE_NORMAL;
  conf.KeySelect = CRYP_KEYSEL_NORMAL;
  conf.pKey = NULL; /* keep the unwrapped key in the key registers */
  conf.KeyIVConfigSkip = CRYP_KEYNOCONFIG;
  conf.pInitVect = iv;
  conf.Header = aad;
  conf.HeaderSize = VAULT_SAES_AAD_SIZE;
  if (HAL_CRYP_SetConfig(&h, &conf) != HAL_OK || !saes_key_valid())
    goto cleanup;
  if ((encrypt ? HAL_CRYP_Encrypt(&h, data, r->length, out, SAES_TIMEOUT)
               : HAL_CRYP_Decrypt(&h, data, r->length, out, SAES_TIMEOUT)) !=
          HAL_OK ||
      HAL_CRYPEx_AESGCM_GenerateAuthTAG(&h, tag, SAES_TIMEOUT) != HAL_OK)
    goto cleanup;

  if (encrypt) {
    memcpy(r->tag, tag, sizeof(r->tag));
    memcpy(r->data, out, r->length);
    result = VAULT_SAES_OK;
  } else {
    /* Compared twice: one skipped branch must not release altered data. */
    volatile uint8_t diff = 0;
    for (size_t i = 0; i < sizeof(r->tag); i++)
      diff |= r->tag[i] ^ ((const uint8_t*)tag)[i];
    if (diff) {
      result = VAULT_SAES_AUTH_FAILED;
    } else {
      memcpy(r->data, out, r->length);
      result = diff ? VAULT_SAES_AUTH_FAILED : VAULT_SAES_OK;
    }
  }

cleanup:
  if (result != VAULT_SAES_OK) memzero(r->data, sizeof(r->data));
  memzero(data, sizeof(data));
  memzero(out, sizeof(out));
  memzero(tag, sizeof(tag));
  /* Clear the key and data registers, as vault_kek_wrap() does. */
  if (secure_aes_init() != sectrue) result = VAULT_SAES_FAILED;
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
  if (secure_aes_init() != sectrue || (!key->ready && !saes_key_create(key))) {
    memzero(r->data, sizeof(r->data));
    return VAULT_SAES_FAILED;
  }
  return saes_gcm(key, r);
}

uint32_t vault_saes_record(vault_saes_request_t* r) {
  return saes_request(&record_key, r);
}

uint32_t vault_saes_storage(vault_saes_request_t* r) {
  return saes_request(&storage_key, r);
}

#endif  // SECURE_MODE
