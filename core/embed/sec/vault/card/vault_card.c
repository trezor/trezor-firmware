/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <string.h>

#include <sec/vault.h>
#include "bip32.h"
#include "curves.h"
#include "memzero.h"

#include <sec/vault_card.h>
#include "card_proto.h"
#include "card_transport.h"

#ifndef VAULT_TEST
#include <sec/storage.h>
#endif

/* Emulator vault whose seed lives on a card. Seed-derived records are card
 * handles: the derivation path plus a passphrase slot, never key material.
 * Every other request goes to the local vault unchanged, and a card handle
 * reaching the local vault fails there, because its kind is unknown. */

/* Card handle layout. It fits the 171-byte node blob coreapp keeps. */
#define CARD_KIND 0xCA
#define CARD_OFF_OWNER 0
#define CARD_OFF_KIND 4
#define CARD_OFF_TYPE 5 /* VAULT_KEY_SEED or VAULT_KEY_NODE */
#define CARD_OFF_SLOT 6
#define CARD_OFF_CURVE 7
#define CARD_OFF_GENERATION 8
#define CARD_OFF_DEPTH 12
#define CARD_OFF_FLAGS 13
#define CARD_OFF_PATH 16
#define CARD_OFF_CHAIN (CARD_OFF_PATH + 4 * CARD_MAX_DEPTH)
#define CARD_OFF_PUBLIC (CARD_OFF_CHAIN + 32)
#define CARD_HANDLE_SIZE (CARD_OFF_PUBLIC + 33)
_Static_assert(CARD_HANDLE_SIZE <= VAULT_NODE_BLOB_SIZE, "card handle size");

#define CARD_FLAG_CACHED 1      /* chain code and public key are valid */
#define CARD_FLAG_PUBLIC_ONLY 2 /* made by public derivation: cannot sign */

/* The passphrase is entered on the phone and sent to the card on each tap,
 * since BIP-39 seed derivation runs on the card. */
#define CARD_SEED_SLOTS 4
typedef struct {
  uint32_t generation;
  uint8_t tag[CARD_TAG_SIZE];
  bool tagged;
  size_t length;
  char passphrase[CARD_PASSPHRASE_MAX];
} card_seed_t;
static card_seed_t card_seeds[CARD_SEED_SLOTS];
static uint32_t card_generation;
static uint8_t card_next_slot;

/* A tap may take this long. The prompt waits a moment first, so that it does
 * not flash for a card that is already on the phone. */
#ifndef CARD_WAIT_MS
#define CARD_WAIT_MS 30000
#endif
#define CARD_PROMPT_MS 300
static vault_card_ui_t card_ui;
/* State of the current vault operation, reported when it ends. */
static bool card_prompted;
static vault_card_state_t card_outcome;

static const char *const card_curves[CARD_CURVE_COUNT] = {
    SECP256K1_NAME, NIST256P1_NAME, ED25519_NAME};

static uint32_t card_get32(const uint8_t *p) {
  uint32_t value;
  memcpy(&value, p, 4);
  return value;
}
static void card_put32(uint8_t *p, uint32_t value) { memcpy(p, &value, 4); }

static bool card_is_handle(const vault_blob_t *blob) {
  return blob->bytes[CARD_OFF_KIND] == CARD_KIND;
}

void vault_card_wipe(void) {
  memzero(card_seeds, sizeof(card_seeds));
  card_disconnect();
}

void vault_card_set_ui(vault_card_ui_t ui) { card_ui = ui; }

bool card_waiting(uint32_t waited_ms) {
  if (waited_ms >= CARD_WAIT_MS) {
    card_outcome = VAULT_CARD_TIMEOUT;
    return false;
  }
  if (waited_ms < CARD_PROMPT_MS || !card_ui) return true;
  card_prompted = true;
  if (card_ui(VAULT_CARD_WAITING, CARD_WAIT_MS - waited_ms)) {
    card_outcome = VAULT_CARD_CANCELLED;
    return false;
  }
  return true;
}

static void card_fail(void) {
  if (card_outcome == VAULT_CARD_WAITING) card_outcome = VAULT_CARD_FAILED;
}

/* End of a vault operation on the card: show its outcome when the user was
 * asked for the card, or when the card failed. A card already held while
 * coreapp derives quietly shows nothing. */
static void card_report(bool ok) {
  vault_card_state_t state = card_outcome;
  if (state == VAULT_CARD_WAITING && card_prompted)
    state = ok ? VAULT_CARD_DONE : VAULT_CARD_FAILED;
  if (state != VAULT_CARD_WAITING && card_ui) card_ui(state, 0);
  card_prompted = false;
  card_outcome = VAULT_CARD_WAITING;
}

/* --- Owners: the local vault keeps them; card handles follow its rules. --- */

static bool card_owner_info(uint32_t owner, vault_lifecycle_response_t *info) {
  vault_lifecycle_request_t request = {VAULT_ABI, VAULT_OWNER_INFO, owner};
  return vault_lifecycle_dispatch(1, &request, info);
}

/* A request may use its own handles and those of its session. Crypto ops may
 * run while locked only under a CoinJoin authorization, as in the vault. */
static bool card_access(const vault_request_t *r, bool unlocked,
                        vault_lifecycle_response_t *info) {
  if (r->abi != VAULT_ABI || !card_owner_info(r->owner, info)) return false;
  if (!unlocked && !info->value) return false;
  uint32_t holder = card_get32(r->blob.bytes + CARD_OFF_OWNER);
  return holder == r->owner || (info->parent && holder == info->parent);
}

static card_seed_t *card_seed(const vault_blob_t *blob) {
  uint8_t slot = blob->bytes[CARD_OFF_SLOT];
  if (slot >= CARD_SEED_SLOTS) return NULL;
  card_seed_t *seed = &card_seeds[slot];
  uint32_t generation = card_get32(blob->bytes + CARD_OFF_GENERATION);
  return seed->generation && seed->generation == generation ? seed : NULL;
}

/* --- APDU exchange --- */

static uint16_t card_apdu(uint8_t ins, uint8_t p1, const uint8_t *data,
                          size_t length, uint8_t *out, size_t out_size,
                          size_t *out_length) {
  uint8_t command[CARD_COMMAND_MAX] = {CARD_CLA, ins, p1, 0, (uint8_t)length};
  uint8_t response[CARD_RESPONSE_MAX] = {0};
  size_t response_length = sizeof(response);
  uint16_t sw = CARD_SW_FAILED;
  if (length > 255) return sw;
  memcpy(command + 5, data, length);
  if (card_transceive(command, 5 + length, response, &response_length) &&
      response_length >= 2 && response_length - 2 <= out_size) {
    sw = response[response_length - 2] << 8 | response[response_length - 1];
    *out_length = response_length - 2;
    memcpy(out, response, *out_length);
  }
  /* No seed is the card's normal state at the start of a tap. */
  if (sw != CARD_SW_OK && sw != CARD_SW_NO_SEED) card_fail();
  memzero(command, sizeof(command));
  memzero(response, sizeof(response));
  return sw;
}

/* Select the seed for this tap. A tag that changed means another card or a
 * changed mnemonic: refuse rather than sign with a different wallet. */
static bool card_select(card_seed_t *seed) {
  uint8_t tag[CARD_TAG_SIZE] = {0};
  size_t length = 0;
  if (card_apdu(CARD_INS_SELECT_SEED, 0, (const uint8_t *)seed->passphrase,
                seed->length, tag, sizeof(tag), &length) != CARD_SW_OK ||
      length != CARD_TAG_SIZE)
    return false;
  if (seed->tagged) {
    if (memcmp(tag, seed->tag, CARD_TAG_SIZE) == 0) return true;
    card_fail();
    return false;
  }
  memcpy(seed->tag, tag, CARD_TAG_SIZE);
  seed->tagged = true;
  return true;
}

/* Encode the node of a handle, optionally extended by one index. Returns the
 * encoded length, or 0. The tag is filled in by card_run. */
static size_t card_node(const vault_blob_t *blob, const uint32_t *extra,
                        uint8_t node[CARD_NODE_MAX]) {
  uint8_t depth = blob->bytes[CARD_OFF_DEPTH];
  if (depth > CARD_MAX_DEPTH || (extra && depth == CARD_MAX_DEPTH)) return 0;
  node[CARD_TAG_SIZE] = blob->bytes[CARD_OFF_CURVE];
  node[CARD_TAG_SIZE + 1] = depth + (extra != NULL);
  uint8_t *p = node + CARD_TAG_SIZE + 2;
  for (uint8_t i = 0; i <= depth; i++) {
    if (i == depth && !extra) break;
    uint32_t index =
        i < depth ? card_get32(blob->bytes + CARD_OFF_PATH + 4 * i) : *extra;
    *p++ = index >> 24;
    *p++ = index >> 16;
    *p++ = index >> 8;
    *p++ = index;
  }
  return p - node;
}

/* Run a node command, selecting the seed when the card has none: the first
 * command of every tap, or after the card was removed and tapped again. */
static uint16_t card_run(card_seed_t *seed, uint8_t ins, uint8_t p1,
                         uint8_t *data, size_t length, uint8_t *out,
                         size_t out_size, size_t *out_length) {
  uint16_t sw = CARD_SW_NO_SEED;
  for (int attempt = 0; attempt < 2 && sw == CARD_SW_NO_SEED; attempt++) {
    if ((!seed->tagged || attempt) && !card_select(seed)) {
      card_disconnect();
      return CARD_SW_FAILED;
    }
    memcpy(data, seed->tag, CARD_TAG_SIZE);
    sw = card_apdu(ins, p1, data, length, out, out_size, out_length);
  }
  return sw;
}

/* Fill the public cache of a node handle from the card. */
static bool card_fetch_public(card_seed_t *seed, vault_blob_t *blob) {
  if (blob->bytes[CARD_OFF_FLAGS] & CARD_FLAG_CACHED) return true;
  uint8_t node[CARD_NODE_MAX] = {0};
  uint8_t out[CARD_PUBLIC_SIZE] = {0};
  size_t length = card_node(blob, NULL, node), out_length = 0;
  if (!length ||
      card_run(seed, CARD_INS_GET_PUBLIC, 0, node, length, out, sizeof(out),
               &out_length) != CARD_SW_OK ||
      out_length != CARD_PUBLIC_SIZE || out[0] != blob->bytes[CARD_OFF_DEPTH])
    return false;
  memcpy(blob->bytes + CARD_OFF_CHAIN, out + 5, 32);
  memcpy(blob->bytes + CARD_OFF_PUBLIC, out + 37, 33);
  blob->bytes[CARD_OFF_FLAGS] |= CARD_FLAG_CACHED;
  return true;
}

/* Public view of a cached handle, for fingerprints and public derivation. */
static bool card_public_node(const vault_blob_t *blob, HDNode *node) {
  memzero(node, sizeof(*node));
  node->curve = get_curve_by_name(card_curves[blob->bytes[CARD_OFF_CURVE]]);
  node->depth = blob->bytes[CARD_OFF_DEPTH];
  if (node->depth)
    node->child_num =
        card_get32(blob->bytes + CARD_OFF_PATH + 4 * (node->depth - 1));
  memcpy(node->chain_code, blob->bytes + CARD_OFF_CHAIN, 32);
  memcpy(node->public_key, blob->bytes + CARD_OFF_PUBLIC, 33);
  node->is_public_key_set = true;
  return node->curve != NULL;
}

/* --- Operations --- */

static bool card_seed_storage(const vault_request_t *r, bool unlocked,
                              vault_response_t *out) {
  vault_lifecycle_response_t info = {0};
  /* Opening a seed needs a real unlock, never a CoinJoin authorization. */
  if (r->abi != VAULT_ABI || !unlocked || !card_owner_info(r->owner, &info) ||
      r->length > CARD_PASSPHRASE_MAX || memchr(r->data, 0, r->length))
    return false;
  uint8_t slot = card_next_slot;
  card_next_slot = (card_next_slot + 1) % CARD_SEED_SLOTS;
  card_seed_t *seed = &card_seeds[slot];
  memzero(seed, sizeof(*seed));
  seed->generation = ++card_generation;
  seed->length = r->length;
  memcpy(seed->passphrase, r->data, r->length);
  card_put32(out->blob.bytes + CARD_OFF_OWNER, r->owner);
  out->blob.bytes[CARD_OFF_KIND] = CARD_KIND;
  out->blob.bytes[CARD_OFF_TYPE] = VAULT_KEY_SEED;
  out->blob.bytes[CARD_OFF_SLOT] = slot;
  card_put32(out->blob.bytes + CARD_OFF_GENERATION, seed->generation);
  /* The card is contacted on first use, not here. */
  return true;
}

static bool card_execute(const vault_request_t *r, bool unlocked,
                         vault_response_t *out) {
  vault_lifecycle_response_t info = {0};
  if (!card_access(r, unlocked, &info)) return false;
  card_seed_t *seed = card_seed(&r->blob);
  if (!seed) return false;
  uint8_t type = r->blob.bytes[CARD_OFF_TYPE];
  vault_blob_t blob = r->blob;
  bool ok = false;

  switch (r->op) {
    case VAULT_FROM_SEED: {
      if (type != VAULT_KEY_SEED || !r->arg) break;
      for (uint8_t curve = 0; curve < CARD_CURVE_COUNT; curve++) {
        if (strncmp(r->curve, card_curves[curve], VAULT_CURVE_SIZE)) continue;
        blob.bytes[CARD_OFF_TYPE] = VAULT_KEY_NODE;
        blob.bytes[CARD_OFF_CURVE] = curve;
        card_put32(blob.bytes + CARD_OFF_OWNER, r->owner);
        out->blob = blob;
        ok = true;
      }
      break;
    }
    case VAULT_RETAIN: {
      uint32_t kind = type == VAULT_KEY_NODE ? SECRET_NODE : SECRET_BYTES;
      if (r->arg != kind || !info.parent ||
          card_get32(blob.bytes + CARD_OFF_OWNER) != r->owner)
        break;
      card_put32(blob.bytes + CARD_OFF_OWNER, info.parent);
      out->blob = blob;
      ok = true;
      break;
    }
    case VAULT_PUBLIC: {
      if (type != VAULT_KEY_NODE) break;
      bool cached = blob.bytes[CARD_OFF_FLAGS] & CARD_FLAG_CACHED;
      HDNode node;
      if (!card_fetch_public(seed, &blob) || !card_public_node(&blob, &node))
        break;
      out->depth = node.depth;
      out->child_num = node.child_num;
      out->value = blob.bytes[CARD_OFF_CURVE];
      memcpy(out->chain_code, node.chain_code, 32);
      memcpy(out->public_key, node.public_key, 33);
      /* As the vault does: hand back the computed key, for own handles. */
      if (!cached && card_get32(blob.bytes + CARD_OFF_OWNER) == r->owner)
        out->blob = blob;
      memzero(&node, sizeof(node));
      ok = true;
      break;
    }
    case VAULT_DERIVE: {
      uint8_t depth = blob.bytes[CARD_OFF_DEPTH];
      uint32_t index = card_get32(r->data);
      bool public_only = blob.bytes[CARD_OFF_FLAGS] & CARD_FLAG_PUBLIC_ONLY;
      HDNode node;
      if (type != VAULT_KEY_NODE || r->length != 4 || r->arg > 1 ||
          depth >= CARD_MAX_DEPTH || (!r->arg && public_only) ||
          !card_fetch_public(seed, &blob) || !card_public_node(&blob, &node))
        break;
      out->value = hdnode_fingerprint(&node);
      blob.bytes[CARD_OFF_FLAGS] &= ~CARD_FLAG_CACHED;
      if (r->arg) {
        /* Public derivation runs on the phone: no tap for addresses. */
        if (!hdnode_public_ckd(&node, index) || hdnode_fill_public_key(&node))
          break;
        memcpy(blob.bytes + CARD_OFF_CHAIN, node.chain_code, 32);
        memcpy(blob.bytes + CARD_OFF_PUBLIC, node.public_key, 33);
        blob.bytes[CARD_OFF_FLAGS] |= CARD_FLAG_CACHED | CARD_FLAG_PUBLIC_ONLY;
      }
      memzero(&node, sizeof(node));
      card_put32(blob.bytes + CARD_OFF_PATH + 4 * depth, index);
      blob.bytes[CARD_OFF_DEPTH] = depth + 1;
      card_put32(blob.bytes + CARD_OFF_OWNER, r->owner);
      out->blob = blob;
      ok = true;
      break;
    }
    case VAULT_SIGN: {
      /* arg: bit 0 compressed, bits 1-2 VAULT_CANONICAL_*. */
      uint32_t compressed = r->arg & 1, canonical = r->arg >> 1;
      uint8_t data[CARD_NODE_MAX + 32] = {0};
      uint8_t signature[CARD_SIGN_SIZE] = {0};
      size_t length = card_node(&blob, NULL, data), out_length = 0;
      if (type != VAULT_KEY_NODE ||
          blob.bytes[CARD_OFF_CURVE] != CARD_CURVE_SECP256K1 ||
          (blob.bytes[CARD_OFF_FLAGS] & CARD_FLAG_PUBLIC_ONLY) ||
          r->length != 32 || canonical > VAULT_CANONICAL_EOS || !length)
        break;
      /* TODO: queue the signs of one transaction into a single tap. */
      memcpy(data + length, r->data, 32);
      ok = card_run(seed, CARD_INS_SIGN, canonical, data, length + 32,
                    signature, sizeof(signature), &out_length) == CARD_SW_OK &&
           out_length == CARD_SIGN_SIZE && signature[0] < 4;
      if (ok) {
        out->signature[0] = 27 + signature[0] + 4 * compressed;
        memcpy(out->signature + 1, signature + 1, 64);
      }
      memzero(signature, sizeof(signature));
      break;
    }
    /* SNAPSHOT and every other op would need the key itself: never. */
    default:
      break;
  }
  memzero(&blob, sizeof(blob));
  return ok;
}

static bool card_dispatch(const vault_request_t *r, vault_response_t *out,
                          bool unlocked) {
  memzero(out, sizeof(*out));
  bool ok = false;
  if (r->op == VAULT_SEED_STORAGE)
    ok = card_seed_storage(r, unlocked, out);
  else if (card_is_handle(&r->blob)) {
    ok = card_execute(r, unlocked, out);
    card_report(ok);
  } else
    return vault_dispatch(1, r, out, unlocked);
  if (!ok) memzero(out, sizeof(*out));
  return ok;
}

#ifndef VAULT_TEST
static bool card_unlocked(void) { return storage_is_unlocked() == sectrue; }
#else
bool vault_card_test_unlocked = true;
static bool card_unlocked(void) { return vault_card_test_unlocked; }
#endif

bool vault_call(const vault_request_t *request, vault_response_t *response) {
  vault_request_t copy = *request;
  bool ok = card_dispatch(&copy, response, card_unlocked());
  memzero(&copy, sizeof(copy));
  return ok;
}

bool vault_call_message(const vault_message_request_t *request,
                        const uint8_t *message, size_t length,
                        vault_response_t *response) {
  /* Ed25519 and key-value messages are not on the card yet. */
  if (card_is_handle(&request->blob) || card_is_handle(&request->extension)) {
    memzero(response, sizeof(*response));
    return false;
  }
  return vault_message_snapshot(1, request, message, length, response,
                                card_unlocked());
}
