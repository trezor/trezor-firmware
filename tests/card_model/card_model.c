/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <string.h>

#include "bip32.h"
#include "bip39.h"
#include "curves.h"
#include "ecdsa.h"
#include "memzero.h"
#include "secp256k1.h"

#include "card_model.h"
#include "card_proto.h"

/* VAULT_CANONICAL_* from sec/vault.h; the card does not include vault code. */
#define CANONICAL_NONE 0
#define CANONICAL_ETHEREUM 1
#define CANONICAL_EOS 2

/* NVM */
static char card_mnemonic[256];
/* RAM, lost on every reset */
static uint8_t card_seed[64];
static uint8_t card_tag[CARD_TAG_SIZE];
static int card_selected;

static const char *const card_curves[CARD_CURVE_COUNT] = {
    SECP256K1_NAME, NIST256P1_NAME, ED25519_NAME};

int card_model_init(const char *mnemonic) {
  card_model_reset();
  if (strlen(mnemonic) >= sizeof(card_mnemonic) || !mnemonic_check(mnemonic))
    return 0;
  strcpy(card_mnemonic, mnemonic);
  return 1;
}

void card_model_reset(void) {
  memzero(card_seed, sizeof(card_seed));
  memzero(card_tag, sizeof(card_tag));
  card_selected = 0;
}

static size_t card_sw(uint8_t *response, size_t length, uint16_t sw) {
  response[length] = sw >> 8;
  response[length + 1] = sw;
  return length + 2;
}

/* TODO: verify the access code (retry counter, wipe after N) before this. */
static uint16_t card_select(const uint8_t *data, size_t length,
                            uint8_t *response, size_t *out) {
  char passphrase[CARD_PASSPHRASE_MAX + 1] = {0};
  if (length > CARD_PASSPHRASE_MAX || memchr(data, 0, length))
    return CARD_SW_WRONG_DATA;
  if (!card_mnemonic[0]) return CARD_SW_NO_SEED;
  memcpy(passphrase, data, length);
  mnemonic_to_seed(card_mnemonic, passphrase, card_seed, NULL);
  memzero(passphrase, sizeof(passphrase));
  HDNode root = {0};
  if (!hdnode_from_seed(card_seed, sizeof(card_seed), SECP256K1_NAME, &root))
    return CARD_SW_FAILED;
  uint32_t fingerprint = hdnode_fingerprint(&root);
  memzero(&root, sizeof(root));
  for (int i = 0; i < CARD_TAG_SIZE; i++)
    card_tag[i] = fingerprint >> (24 - 8 * i);
  card_selected = 1;
  memcpy(response, card_tag, CARD_TAG_SIZE);
  *out = CARD_TAG_SIZE;
  return CARD_SW_OK;
}

/* Parse the node prefix of a command and derive it from the selected seed.
 * *used is set to the number of bytes the node took. */
static uint16_t card_derive(const uint8_t *data, size_t length, HDNode *node,
                            size_t *used) {
  if (length < CARD_TAG_SIZE + 2) return CARD_SW_WRONG_LENGTH;
  if (!card_selected || memcmp(data, card_tag, CARD_TAG_SIZE))
    return CARD_SW_NO_SEED;
  uint8_t curve = data[CARD_TAG_SIZE], depth = data[CARD_TAG_SIZE + 1];
  if (curve >= CARD_CURVE_COUNT || depth > CARD_MAX_DEPTH)
    return CARD_SW_WRONG_DATA;
  *used = CARD_TAG_SIZE + 2 + 4 * depth;
  if (length < *used) return CARD_SW_WRONG_LENGTH;
  if (!hdnode_from_seed(card_seed, sizeof(card_seed), card_curves[curve], node))
    return CARD_SW_FAILED;
  const uint8_t *p = data + CARD_TAG_SIZE + 2;
  for (uint8_t i = 0; i < depth; i++, p += 4) {
    uint32_t index = (uint32_t)p[0] << 24 | p[1] << 16 | p[2] << 8 | p[3];
    if (!hdnode_private_ckd(node, index)) return CARD_SW_FAILED;
  }
  return hdnode_fill_public_key(node) ? CARD_SW_FAILED : CARD_SW_OK;
}

static uint16_t card_get_public(const uint8_t *data, size_t length,
                                uint8_t *response, size_t *out) {
  HDNode node = {0};
  size_t used = 0;
  uint16_t sw = card_derive(data, length, &node, &used);
  if (sw == CARD_SW_OK && used != length) sw = CARD_SW_WRONG_LENGTH;
  if (sw == CARD_SW_OK) {
    response[0] = node.depth;
    for (int i = 0; i < 4; i++)
      response[1 + i] = node.child_num >> (24 - 8 * i);
    memcpy(response + 5, node.chain_code, 32);
    memcpy(response + 37, node.public_key, 33);
    *out = CARD_PUBLIC_SIZE;
  }
  memzero(&node, sizeof(node));
  return sw;
}

static int card_ethereum_canonical(uint8_t v, uint8_t signature[64]) {
  (void)signature;
  return (v & 2) == 0;
}
static int card_eos_canonical(uint8_t v, uint8_t signature[64]) {
  (void)v;
  return !(signature[0] & 0x80) &&
         !(signature[0] == 0 && !(signature[1] & 0x80)) &&
         !(signature[32] & 0x80) &&
         !(signature[32] == 0 && !(signature[33] & 0x80));
}

/* TODO: a batch form, so one tap signs every input of a transaction. */
static uint16_t card_sign(uint8_t canonical, const uint8_t *data, size_t length,
                          uint8_t *response, size_t *out) {
  HDNode node = {0};
  size_t used = 0;
  if (canonical > CANONICAL_EOS) return CARD_SW_WRONG_DATA;
  uint16_t sw = card_derive(data, length, &node, &used);
  if (sw == CARD_SW_OK && used + 32 != length) sw = CARD_SW_WRONG_LENGTH;
  if (sw == CARD_SW_OK && data[CARD_TAG_SIZE] != CARD_CURVE_SECP256K1)
    sw = CARD_SW_WRONG_DATA;
  if (sw == CARD_SW_OK) {
    int (*is_canonical)(uint8_t, uint8_t[64]) =
        canonical == CANONICAL_ETHEREUM ? card_ethereum_canonical
        : canonical == CANONICAL_EOS    ? card_eos_canonical
                                        : NULL;
    uint8_t recovery = 0;
    if (ecdsa_sign_digest(&secp256k1, node.private_key, data + used,
                          response + 1, &recovery, is_canonical) == 0) {
      response[0] = recovery;
      *out = CARD_SIGN_SIZE;
    } else {
      sw = CARD_SW_FAILED;
    }
  }
  memzero(&node, sizeof(node));
  return sw;
}

size_t card_model_process(const uint8_t *command, size_t length,
                          uint8_t *response) {
  size_t out = 0;
  if (length < 5 || length != 5u + command[4])
    return card_sw(response, 0, CARD_SW_WRONG_LENGTH);
  if (command[0] != CARD_CLA) return card_sw(response, 0, CARD_SW_CLA);
  const uint8_t *data = command + 5;
  size_t data_length = command[4];
  uint16_t sw = CARD_SW_INS;
  switch (command[1]) {
    case CARD_INS_SELECT_SEED:
      sw = card_select(data, data_length, response, &out);
      break;
    case CARD_INS_GET_PUBLIC:
      sw = card_get_public(data, data_length, response, &out);
      break;
    case CARD_INS_SIGN:
      sw = card_sign(command[2], data, data_length, response, &out);
      break;
  }
  if (sw != CARD_SW_OK) {
    memzero(response, out);
    out = 0;
  }
  return card_sw(response, out, sw);
}
