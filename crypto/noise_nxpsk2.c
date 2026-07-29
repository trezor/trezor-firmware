/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <string.h>

#include "aes/aesgcm.h"
#include "ed25519-donna/ed25519.h"
#include "hmac.h"
#include "memzero.h"
#include "noise_nxpsk2.h"
#include "rand.h"
#include "sha2.h"

#define NONCE_LIMIT 0xFFFFFFFFFFFFFFFFULL
#define NONCE_ARRAY_SIZE_BYTES 12
#define NOISE_TAG_SIZE_BYTES 16

/**
 * @brief translate nonce into 12 byte big-endian array with
 * 4 zero byte padding.
 *
 * @param nonce
 * @param output byte array
 */
static void nonce_to_bytes(uint64_t nonce,
                           uint8_t (*arr)[NONCE_ARRAY_SIZE_BYTES]) {
  (*arr)[0] = 0x0;
  (*arr)[1] = 0x0;
  (*arr)[2] = 0x0;
  (*arr)[3] = 0x0;

  for (size_t i = 4; i < NONCE_ARRAY_SIZE_BYTES; i++) {
    (*arr)[i] = (nonce >> (56 - (i - 4) * 8)) & 0xFF;
  }
}

static void ss_init(noise_nxpsk2_symmetric_state_t *ss,
                    const uint8_t *protocol_name, size_t protocol_name_len) {
  if (protocol_name_len <= NOISE_NXPSK2_HASHLEN) {
    memcpy(ss->handshake_hash, protocol_name, protocol_name_len);
    memset(ss->handshake_hash + protocol_name_len, 0,
           NOISE_NXPSK2_HASHLEN - protocol_name_len);
  } else {
    sha256_Raw(protocol_name, protocol_name_len, ss->handshake_hash);
  }

  memcpy(ss->chaining_key, ss->handshake_hash, NOISE_NXPSK2_HASHLEN);
  ss->cipher_state.has_key = false;
  ss->cipher_state.nonce = 0;
}

static void ss_mix_hash(noise_nxpsk2_symmetric_state_t *ss, const uint8_t *data,
                        size_t len) {
  SHA256_CTX context = {0};
  sha256_Init(&context);
  sha256_Update(&context, ss->handshake_hash, NOISE_NXPSK2_HASHLEN);
  sha256_Update(&context, data, len);
  sha256_Final(&context, ss->handshake_hash);
  memzero(&context, sizeof(context));
}

static void hkdf3(const uint8_t *chaining_key, size_t chaining_key_len,
                  const uint8_t *key, size_t key_len,
                  uint8_t (*output1)[NOISE_NXPSK2_HASHLEN],
                  uint8_t (*output2)[NOISE_NXPSK2_HASHLEN],
                  uint8_t (*output3)[NOISE_NXPSK2_HASHLEN]) {
  uint8_t temp_key[NOISE_NXPSK2_HASHLEN] = {0};
  hmac_sha256(chaining_key, chaining_key_len, key, key_len, temp_key);

  uint8_t buf[NOISE_NXPSK2_HASHLEN + 1] = {0};
  buf[0] = 0x1;
  hmac_sha256(temp_key, NOISE_NXPSK2_HASHLEN, buf, 1, *output1);

  memcpy(buf, *output1, NOISE_NXPSK2_HASHLEN);
  buf[NOISE_NXPSK2_HASHLEN] = 0x2;

  hmac_sha256(temp_key, NOISE_NXPSK2_HASHLEN, buf, NOISE_NXPSK2_HASHLEN + 1,
              *output2);

  memcpy(buf, *output2, NOISE_NXPSK2_HASHLEN);
  buf[NOISE_NXPSK2_HASHLEN] = 0x3;

  hmac_sha256(temp_key, NOISE_NXPSK2_HASHLEN, buf, NOISE_NXPSK2_HASHLEN + 1,
              *output3);

  memzero(temp_key, sizeof(temp_key));  // Clear buffes from stack
  memzero(buf, sizeof(buf));
}

static void hkdf2(const uint8_t *chaining_key, size_t chaining_key_len,
                  const uint8_t *key, size_t key_len,
                  uint8_t (*output1)[NOISE_NXPSK2_HASHLEN],
                  uint8_t (*output2)[NOISE_NXPSK2_HASHLEN]) {
  uint8_t temp_key[NOISE_NXPSK2_HASHLEN] = {0};
  hmac_sha256(chaining_key, chaining_key_len, key, key_len, temp_key);

  uint8_t buf[NOISE_NXPSK2_HASHLEN + 1] = {0};
  buf[0] = 0x1;
  hmac_sha256(temp_key, NOISE_NXPSK2_HASHLEN, buf, 1, *output1);

  memcpy(buf, *output1, NOISE_NXPSK2_HASHLEN);
  buf[NOISE_NXPSK2_HASHLEN] = 0x2;

  hmac_sha256(temp_key, NOISE_NXPSK2_HASHLEN, buf, NOISE_NXPSK2_HASHLEN + 1,
              *output2);

  memzero(temp_key, sizeof(temp_key));  // Clear buffers from stack
  memzero(buf, sizeof(buf));
}

static void dh(const uint8_t (*private_key)[NOISE_NXPSK2_DHLEN],
               const uint8_t (*public_key)[NOISE_NXPSK2_DHLEN],
               uint8_t (*output)[NOISE_NXPSK2_DHLEN]) {
  curve25519_scalarmult(*output, *private_key, *public_key);
}

static void ss_mix_key(
    noise_nxpsk2_symmetric_state_t *ss,
    const uint8_t (*input_key_material)[NOISE_NXPSK2_DHLEN]) {
  // Mix key
  hkdf2(ss->chaining_key, NOISE_NXPSK2_HASHLEN, *input_key_material,
        NOISE_NXPSK2_DHLEN,
        &ss->chaining_key,     // <- Output 1
        &ss->cipher_state.key  // <- Output 2
  );
  ss->cipher_state.has_key = true;
  ss->cipher_state.nonce = 0;
}

static void ss_mix_key_and_hash(noise_nxpsk2_symmetric_state_t *ss,
                                const uint8_t (*key)[NOISE_NXPSK2_HASHLEN]) {
  uint8_t temp_h[NOISE_NXPSK2_HASHLEN] = {0};

  hkdf3(ss->chaining_key, NOISE_NXPSK2_HASHLEN, (uint8_t *)key,
        NOISE_NXPSK2_HASHLEN, &ss->chaining_key, &temp_h,
        &ss->cipher_state.key);

  ss->cipher_state.has_key = true;
  ss->cipher_state.nonce = 0;
  ss_mix_hash(ss, temp_h, NOISE_NXPSK2_HASHLEN);
  memzero(temp_h, sizeof(temp_h));  // Remove temp keys from stack
}

static void ss_ts_split(noise_nxpsk2_symmetric_state_t *ss,
                        noise_nxpsk2_transport_state_t *ts, bool initiator) {
  if (initiator) {
    hkdf2(ss->chaining_key, NOISE_NXPSK2_HASHLEN, NULL, 0,
          &ts->send_cipher_state.key, &ts->receive_cipher_state.key);
  } else {
    hkdf2(ss->chaining_key, NOISE_NXPSK2_HASHLEN, NULL, 0,
          &ts->receive_cipher_state.key, &ts->send_cipher_state.key);
  }

  ts->send_cipher_state.has_key = true;
  ts->send_cipher_state.nonce = 0;
  ts->receive_cipher_state.has_key = true;
  ts->receive_cipher_state.nonce = 0;
  memcpy(ts->handshake_hash, ss->handshake_hash, NOISE_NXPSK2_HASHLEN);
}

/**
 * @brief generate new curve25519 keypair
 *
 * @param private_key output buffer for generated private key
 * @param public_key output buffer for derived public key
 */
static void generate_keypair(uint8_t (*private_key)[NOISE_NXPSK2_DHLEN],
                             uint8_t (*public_key)[NOISE_NXPSK2_DHLEN]) {
  random_buffer(*private_key, NOISE_NXPSK2_DHLEN);
  (*private_key)[0] &= 248;
  (*private_key)[31] &= 127;
  (*private_key)[31] |= 64;
  curve25519_scalarmult_basepoint(*public_key, *private_key);
}

/**
 * @brief encrypt with associated data
 *
 * @param cs cipher state containing the key and nonce for encryption
 * @param ad pointer to the associated data
 * @param ad_len length of the associated data
 * @param plaintext pointer to the plaintext input of size defined by
 * `plaintext_len`
 * @param plaintext_len size of the plaintext
 * @param ciphertext pointer to the ciphertext output of size defined
 * by `plaintext_len + NOISE_TAG_SIZE_BYTES`
 * @return bool;
 */
static bool encrypt_with_ad(noise_nxpsk2_cipher_state_t *cs, const uint8_t *ad,
                            size_t ad_len, const uint8_t *plaintext,
                            size_t plaintext_len, uint8_t *ciphertext) {
  if (!cs->has_key || cs->nonce >= NONCE_LIMIT) {
    return false;
  } else {
    // Encrypt with AEAD
    gcm_ctx ctx = {0};
    if (gcm_init_and_key(cs->key, NOISE_NXPSK2_HASHLEN, &ctx) != RETURN_GOOD) {
      memzero(&ctx, sizeof(ctx));
      return false;
    }

    uint8_t nonce_bytes[NONCE_ARRAY_SIZE_BYTES] = {0};
    nonce_to_bytes(cs->nonce, &nonce_bytes);

    if (ciphertext != NULL && plaintext != NULL) {  // to suppress asan warning
      memcpy(ciphertext, plaintext, plaintext_len);
    }

    if (gcm_encrypt_message(nonce_bytes, NONCE_ARRAY_SIZE_BYTES, ad, ad_len,
                            ciphertext, plaintext_len,
                            ciphertext + plaintext_len, NOISE_TAG_SIZE_BYTES,
                            &ctx) != RETURN_GOOD) {
      memzero(&ctx, sizeof(ctx));
      memzero(ciphertext, plaintext_len + NOISE_TAG_SIZE_BYTES);
      memzero(nonce_bytes, sizeof(nonce_bytes));
      return false;
    }

    memzero(&ctx, sizeof(ctx));
    memzero(nonce_bytes, sizeof(nonce_bytes));
    cs->nonce++;
  }

  return true;
}

/**
 * @brief decrypt with associated data
 *
 * @param cs cipher state containing the key and nonce for decryption
 * @param ad pointer to the associated data
 * @param ad_len length of the associated data
 * @param ciphertext pointer to the ciphertext input of size defined
 * by `ciphertext_len`
 * @param ciphertext_len size of the ciphertext
 * @param plaintext pointer to the plaintext output of size defined
 * by `ciphertext_len - NOISE_TAG_SIZE_BYTES`
 * @return bool;
 */
static bool decrypt_with_ad(noise_nxpsk2_cipher_state_t *cs, const uint8_t *ad,
                            size_t ad_len, const uint8_t *ciphertext,
                            size_t ciphertext_len, uint8_t *plaintext) {
  if (!cs->has_key || cs->nonce >= NONCE_LIMIT) {
    return false;

  } else {
    if (ciphertext_len < NOISE_TAG_SIZE_BYTES) {
      // encrypted message is too short to contain the auth. tag
      return false;
    }

    // Decrypt with AEAD
    gcm_ctx ctx = {0};
    if (gcm_init_and_key(cs->key, NOISE_NXPSK2_HASHLEN, &ctx) != RETURN_GOOD) {
      memzero(&ctx, sizeof(ctx));
      return false;
    }

    uint8_t nonce_bytes[NONCE_ARRAY_SIZE_BYTES] = {0};
    nonce_to_bytes(cs->nonce, &nonce_bytes);

    // decrypted message is shorter by auth. tag
    size_t plaintext_len = ciphertext_len - NOISE_TAG_SIZE_BYTES;

    if (plaintext != NULL && ciphertext != NULL) {  // to suppress asan warning
      memcpy(plaintext, ciphertext, plaintext_len);
    }

    if (gcm_decrypt_message(nonce_bytes, NONCE_ARRAY_SIZE_BYTES, ad, ad_len,
                            plaintext, plaintext_len,
                            ciphertext + plaintext_len, NOISE_TAG_SIZE_BYTES,
                            &ctx) != RETURN_GOOD) {
      memzero(&ctx, sizeof(ctx));
      if (plaintext != NULL) {
        memzero(plaintext, plaintext_len);
      }
      memzero(nonce_bytes, sizeof(nonce_bytes));
      return false;
    }

    memzero(&ctx, sizeof(ctx));
    memzero(nonce_bytes, sizeof(nonce_bytes));
    cs->nonce++;
  }

  return true;
}

/**
 * @brief encrypt and hash
 *
 * @param ss pointer to symmetric state structure,
 * @param plaintext pointer to the plaintext input of size defined by
 * `plaintext_len`
 * @param plaintext_len size of the plaintext
 * @param ciphertext pointer to the ciphertext output of size defined by
 * `plaintext_len + NOISE_TAG_SIZE_BYTES`
 * @return bool;
 */
static bool ss_encrypt_and_hash(noise_nxpsk2_symmetric_state_t *ss,
                                const uint8_t *plaintext, size_t plaintext_len,
                                uint8_t *ciphertext) {
  if (!encrypt_with_ad(&ss->cipher_state, ss->handshake_hash,
                       NOISE_NXPSK2_HASHLEN, plaintext, plaintext_len,
                       ciphertext)) {
    return false;
  }

  ss_mix_hash(ss, ciphertext, plaintext_len + NOISE_TAG_SIZE_BYTES);

  return true;
}

/**
 * @brief decrypt and hash
 *
 * @param ss pointer to symmetric state structure,
 * @param ciphertext pointer to the ciphertext input of size defined by
 * `ciphertext_len`
 * @param ciphertext_len size of the ciphertext
 * @param plaintext pointer to the plaintext output of size defined by
 * `ciphertext_len - NOISE_TAG_SIZE_BYTES`
 * @return bool;
 */
static bool ss_decrypt_and_hash(noise_nxpsk2_symmetric_state_t *ss,
                                const uint8_t *ciphertext,
                                size_t ciphertext_len, uint8_t *plaintext) {
  if (!decrypt_with_ad(&ss->cipher_state, ss->handshake_hash,
                       NOISE_NXPSK2_HASHLEN, ciphertext, ciphertext_len,
                       plaintext)) {
    return false;
  }

  ss_mix_hash(ss, ciphertext, ciphertext_len);

  return true;
}

static bool noise_nxpsk2_init_state(noise_nxpsk2_handshake_state_t *state,
                                    const uint8_t psk[NOISE_NXPSK2_DHLEN],
                                    const uint8_t *prologue,
                                    size_t prologue_len) {
  static const uint8_t NX_PROTOCOL_NAME[] = "Noise_NXpsk2_25519_AESGCM_SHA256";

  if (prologue == NULL && prologue_len != 0) {
    return false;
  }

  ss_init(&state->symmetric_state, NX_PROTOCOL_NAME,
          sizeof(NX_PROTOCOL_NAME) - 1);  // -1 substract the string terminator

  ss_mix_hash(&state->symmetric_state, prologue, prologue_len);

  memcpy(state->psk, psk, NOISE_NXPSK2_DHLEN);

  state->has_ephemeral_private = false;
  state->has_remote_ephemeral_public = false;
  return true;
}

#ifdef USE_NOISE_NXPSK2_RESPONDER

bool noise_nxpsk2_responder_init(noise_nxpsk2_responder_t *rspn,
                                 const uint8_t psk[NOISE_NXPSK2_DHLEN]) {
  if (rspn == NULL) {
    return false;
  }

  if (rspn->initialized || psk == NULL) {
    goto cleanup;
  }

  // Clear the responder structure
  memset(rspn, 0, sizeof(noise_nxpsk2_responder_t));

  if (!noise_nxpsk2_init_state(&rspn->handshake_state, psk, NULL, 0)) {
    goto cleanup;
  }

  rspn->handshake_stage = NOISE_NXPSK2_RSPN_WAITING_FOR_REQUEST1;
  rspn->initialized = true;
  rspn->has_transport_state = false;
  return true;

cleanup:
  noise_nxpsk2_responder_deinit(rspn);
  return false;
}

void noise_nxpsk2_responder_deinit(noise_nxpsk2_responder_t *rspn) {
  if (rspn != NULL) {
    // Clear the responder structure
    memzero(rspn, sizeof(noise_nxpsk2_responder_t));
  }
}

bool noise_nxpsk2_responder_handle_request1(
    noise_nxpsk2_responder_t *rspn, const uint8_t *request, size_t request_len,
    uint8_t *payload, size_t max_payload_size, size_t *payload_size) {
  if (rspn == NULL) {
    return false;
  }

  if (!rspn->initialized ||
      rspn->handshake_stage != NOISE_NXPSK2_RSPN_WAITING_FOR_REQUEST1 ||
      request == NULL || (payload == NULL && max_payload_size != 0)) {
    goto cleanup;
  }

  if (request_len < NOISE_NXPSK2_DHLEN + NOISE_TAG_SIZE_BYTES) {
    goto cleanup;
  }

  noise_nxpsk2_handshake_state_t *state = &rspn->handshake_state;

  memcpy(state->remote_ephemeral_public, request, NOISE_NXPSK2_DHLEN);
  state->has_remote_ephemeral_public = true;
  ss_mix_hash(&state->symmetric_state, state->remote_ephemeral_public,
              NOISE_NXPSK2_DHLEN);

  // Calling ss_mix_key is required in PSK mode. See specification, Section 9.2:
  // https://noiseprotocol.org/noise.html#handshake-tokens
  ss_mix_key(&state->symmetric_state, &state->remote_ephemeral_public);

  size_t ciphertext_len = request_len - NOISE_NXPSK2_DHLEN;

  if (max_payload_size < ciphertext_len - NOISE_TAG_SIZE_BYTES) {
    goto cleanup;
  }

  // PSK mode established a key at the `e` token, so the payload is encrypted.
  if (!ss_decrypt_and_hash(&state->symmetric_state,
                           request + NOISE_NXPSK2_DHLEN, ciphertext_len,
                           payload)) {
    goto cleanup;
  }

  if (payload_size != NULL) {
    *payload_size = ciphertext_len - NOISE_TAG_SIZE_BYTES;
  }

  rspn->handshake_stage = NOISE_NXPSK2_RSPN_READY_FOR_RESPONSE1;
  return true;

cleanup:
  noise_nxpsk2_responder_deinit(rspn);
  return false;
}

bool noise_nxpsk2_responder_create_response1(
    noise_nxpsk2_responder_t *rspn,
    const uint8_t static_private_key[NOISE_NXPSK2_DHLEN],
    const uint8_t static_public_key[NOISE_NXPSK2_DHLEN], const uint8_t *payload,
    size_t payload_size, uint8_t *response, size_t max_response_size,
    size_t *response_size) {
  if (rspn == NULL) {
    return false;
  }

  noise_nxpsk2_handshake_state_t *state = &rspn->handshake_state;

  if (!rspn->initialized || static_private_key == NULL ||
      static_public_key == NULL || response == NULL || response_size == NULL ||
      rspn->handshake_stage != NOISE_NXPSK2_RSPN_READY_FOR_RESPONSE1 ||
      !state->has_remote_ephemeral_public ||
      (payload == NULL && payload_size != 0)) {
    goto cleanup;
  }

  // Check if response buffer is large enough to hold the response
  if (max_response_size <
      (2 * NOISE_NXPSK2_DHLEN + 2 * NOISE_TAG_SIZE_BYTES + payload_size)) {
    goto cleanup;
  }

  // Generate ephemeral keypair
  generate_keypair(&state->ephemeral_private,
                   (uint8_t (*)[NOISE_NXPSK2_DHLEN])response);
  state->has_ephemeral_private = true;

  ss_mix_hash(&state->symmetric_state, response, NOISE_NXPSK2_DHLEN);
  ss_mix_key(&state->symmetric_state,
             (uint8_t (*)[NOISE_NXPSK2_DHLEN])response);

  uint8_t input_key_material[NOISE_NXPSK2_DHLEN] = {0};
  dh(&state->ephemeral_private, &state->remote_ephemeral_public,
     &input_key_material);
  ss_mix_key(&state->symmetric_state, &input_key_material);
  memzero(input_key_material, sizeof(input_key_material));

  // Encrypt static public key
  if (!ss_encrypt_and_hash(&state->symmetric_state, static_public_key,
                           NOISE_NXPSK2_DHLEN, response + NOISE_NXPSK2_DHLEN)) {
    goto cleanup;
  }

  dh((const uint8_t (*)[NOISE_NXPSK2_DHLEN])static_private_key,
     &state->remote_ephemeral_public, &input_key_material);
  ss_mix_key(&state->symmetric_state, &input_key_material);
  memzero(input_key_material, sizeof(input_key_material));

  ss_mix_key_and_hash(&state->symmetric_state, &state->psk);

  // Encrypt payload
  if (!ss_encrypt_and_hash(
          &state->symmetric_state, payload, payload_size,
          response + (2 * NOISE_NXPSK2_DHLEN + NOISE_TAG_SIZE_BYTES))) {
    goto cleanup;
  }

  *response_size =
      2 * NOISE_NXPSK2_DHLEN + 2 * NOISE_TAG_SIZE_BYTES + payload_size;

  ss_ts_split(&state->symmetric_state, &rspn->transport_state, false);

  // Clean sensitive data from handler
  memzero(state, sizeof(noise_nxpsk2_handshake_state_t));

  rspn->has_transport_state = true;
  rspn->handshake_stage = NOISE_NXPSK2_RSPN_HANDSHAKE_COMPLETE;
  return true;

cleanup:
  noise_nxpsk2_responder_deinit(rspn);
  return false;
}

#endif  // USE_NOISE_NXPSK2_RESPONDER

#ifdef USE_NOISE_NXPSK2_INITIATOR

bool noise_nxpsk2_initiator_init(noise_nxpsk2_initiator_t *intr,
                                 const uint8_t psk[NOISE_NXPSK2_DHLEN]) {
  if (intr == NULL) {
    return false;
  }

  if (intr->initialized || psk == NULL) {
    goto cleanup;
  }

  // Clear the initiator structure
  memset(intr, 0, sizeof(noise_nxpsk2_initiator_t));

  if (!noise_nxpsk2_init_state(&intr->handshake_state, psk, NULL, 0)) {
    goto cleanup;
  }

  intr->handshake_stage = NOISE_NXPSK2_INTR_READY_FOR_REQUEST1;
  intr->initialized = true;
  intr->has_transport_state = false;
  return true;

cleanup:
  noise_nxpsk2_initiator_deinit(intr);
  return false;
}

void noise_nxpsk2_initiator_deinit(noise_nxpsk2_initiator_t *intr) {
  if (intr != NULL) {
    // Clear the initiator structure
    memzero(intr, sizeof(noise_nxpsk2_initiator_t));
  }
}

bool noise_nxpsk2_initiator_create_request1(
    noise_nxpsk2_initiator_t *intr, const uint8_t *payload, size_t payload_size,
    uint8_t *request, size_t max_request_size, size_t *request_size) {
  if (intr == NULL) {
    return false;
  }

  if (!intr->initialized ||
      intr->handshake_stage != NOISE_NXPSK2_INTR_READY_FOR_REQUEST1 ||
      (payload == NULL && payload_size != 0) || request == NULL ||
      request_size == NULL) {
    goto cleanup;
  }

  if (max_request_size <
      (NOISE_NXPSK2_DHLEN + payload_size + NOISE_TAG_SIZE_BYTES)) {
    goto cleanup;
  }

  noise_nxpsk2_handshake_state_t *state = &intr->handshake_state;

  // Generate ephemeral keypair
  generate_keypair(&state->ephemeral_private,
                   (uint8_t (*)[NOISE_NXPSK2_DHLEN])request);
  state->has_ephemeral_private = true;

  ss_mix_hash(&state->symmetric_state, request, NOISE_NXPSK2_DHLEN);
  ss_mix_key(&state->symmetric_state, (uint8_t (*)[NOISE_NXPSK2_DHLEN])request);

  // PSK mode established a key at the `e` token, so the payload is encrypted.
  if (!ss_encrypt_and_hash(&state->symmetric_state, payload, payload_size,
                           request + NOISE_NXPSK2_DHLEN)) {
    goto cleanup;
  }

  *request_size = NOISE_NXPSK2_DHLEN + payload_size + NOISE_TAG_SIZE_BYTES;
  intr->handshake_stage = NOISE_NXPSK2_INTR_WAITING_FOR_RESPONSE1;
  return true;

cleanup:
  noise_nxpsk2_initiator_deinit(intr);
  return false;
}

bool noise_nxpsk2_initiator_handle_response1(
    noise_nxpsk2_initiator_t *intr, const uint8_t *response,
    size_t response_len, uint8_t remote_static_public[NOISE_NXPSK2_DHLEN],
    uint8_t *payload, size_t max_payload_size, size_t *payload_size) {
  if (intr == NULL) {
    return false;
  }

  noise_nxpsk2_handshake_state_t *state = &intr->handshake_state;

  if (!intr->initialized ||
      intr->handshake_stage != NOISE_NXPSK2_INTR_WAITING_FOR_RESPONSE1 ||
      response == NULL || remote_static_public == NULL ||
      !state->has_ephemeral_private ||
      (payload == NULL && max_payload_size != 0)) {
    goto cleanup;
  }

  if (response_len < 2 * NOISE_NXPSK2_DHLEN + 2 * NOISE_TAG_SIZE_BYTES) {
    goto cleanup;
  }

  memcpy(state->remote_ephemeral_public, response, NOISE_NXPSK2_DHLEN);
  state->has_remote_ephemeral_public = true;
  ss_mix_hash(&state->symmetric_state, state->remote_ephemeral_public,
              NOISE_NXPSK2_DHLEN);
  ss_mix_key(&state->symmetric_state, &state->remote_ephemeral_public);

  uint8_t input_key_material[NOISE_NXPSK2_DHLEN] = {0};
  dh(&state->ephemeral_private, &state->remote_ephemeral_public,
     &input_key_material);
  ss_mix_key(&state->symmetric_state, &input_key_material);
  memzero(input_key_material, sizeof(input_key_material));

  if (!ss_decrypt_and_hash(
          &state->symmetric_state, response + NOISE_NXPSK2_DHLEN,
          NOISE_NXPSK2_DHLEN + NOISE_TAG_SIZE_BYTES, remote_static_public)) {
    goto cleanup;
  }

  dh(&state->ephemeral_private,
     (const uint8_t (*)[NOISE_NXPSK2_DHLEN])remote_static_public,
     &input_key_material);
  ss_mix_key(&state->symmetric_state, &input_key_material);
  memzero(input_key_material, sizeof(input_key_material));

  ss_mix_key_and_hash(&state->symmetric_state, &state->psk);

  size_t ciphertext_len =
      response_len - (2 * NOISE_NXPSK2_DHLEN + NOISE_TAG_SIZE_BYTES);

  if (max_payload_size < ciphertext_len - NOISE_TAG_SIZE_BYTES) {
    goto cleanup;
  }

  if (!ss_decrypt_and_hash(
          &state->symmetric_state,
          response + (2 * NOISE_NXPSK2_DHLEN + NOISE_TAG_SIZE_BYTES),
          ciphertext_len, payload)) {
    goto cleanup;
  }

  if (payload_size != NULL) {
    *payload_size = ciphertext_len - NOISE_TAG_SIZE_BYTES;
  }

  ss_ts_split(&state->symmetric_state, &intr->transport_state, true);

  // Clean sensitive data from handler
  memzero(state, sizeof(noise_nxpsk2_handshake_state_t));

  intr->has_transport_state = true;
  intr->handshake_stage = NOISE_NXPSK2_INTR_HANDSHAKE_COMPLETE;
  return true;

cleanup:
  if (remote_static_public != NULL) {
    memzero(remote_static_public, NOISE_NXPSK2_DHLEN);
  }
  noise_nxpsk2_initiator_deinit(intr);
  return false;
}

#endif  // USE_NOISE_NXPSK2_INITIATOR

bool noise_nxpsk2_send_message(noise_nxpsk2_transport_state_t *ts,
                               const uint8_t *payload, size_t payload_size,
                               uint8_t *ciphertext, size_t max_ciphertext_size,
                               size_t *ciphertext_size) {
  if (ts == NULL || (payload == NULL && payload_size != 0) ||
      ciphertext == NULL || ciphertext_size == NULL) {
    return false;
  }

  if (max_ciphertext_size < payload_size + NOISE_TAG_SIZE_BYTES) {
    return false;
  }

  if (!encrypt_with_ad(&ts->send_cipher_state, NULL, 0, payload, payload_size,
                       ciphertext)) {
    return false;
  }

  *ciphertext_size = payload_size + NOISE_TAG_SIZE_BYTES;
  return true;
}

bool noise_nxpsk2_receive_message(noise_nxpsk2_transport_state_t *ts,
                                  const uint8_t *ciphertext,
                                  size_t ciphertext_size, uint8_t *payload,
                                  size_t max_payload_size,
                                  size_t *payload_size) {
  if (ts == NULL || ciphertext == NULL || payload == NULL ||
      payload_size == NULL) {
    return false;
  }
  if (ciphertext_size < NOISE_TAG_SIZE_BYTES) {
    return false;
  }
  if (ciphertext_size > max_payload_size + NOISE_TAG_SIZE_BYTES) {
    return false;
  }

  if (!decrypt_with_ad(&ts->receive_cipher_state, NULL, 0, ciphertext,
                       ciphertext_size, payload)) {
    return false;
  }

  *payload_size = ciphertext_size - NOISE_TAG_SIZE_BYTES;
  return true;
}
