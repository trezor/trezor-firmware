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
#include "noise_xxpsk3.h"
#include "rand.h"
#include "sha2.h"

// The counter is restricted to 48 bits: 2^48 messages of at most 65535 bytes
// produce at most 2^60 AES blocks under one key, well below the 2^64 blocks
// per key that NIST SP 800-38D, Appendix B recommends as a limit.
// https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=51288
#define NONCE_LIMIT 0x1000000000000ULL  // 2^48
#define NONCE_ARRAY_SIZE_BYTES 12

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

static void ss_init(noise_xxpsk3_symmetric_state_t *ss,
                    const uint8_t *protocol_name, size_t protocol_name_len) {
  if (protocol_name_len <= NOISE_XXPSK3_HASHLEN) {
    memcpy(ss->handshake_hash, protocol_name, protocol_name_len);
    memset(ss->handshake_hash + protocol_name_len, 0,
           NOISE_XXPSK3_HASHLEN - protocol_name_len);
  } else {
    sha256_Raw(protocol_name, protocol_name_len, ss->handshake_hash);
  }

  memcpy(ss->chaining_key, ss->handshake_hash, NOISE_XXPSK3_HASHLEN);
  memzero(&ss->cipher_state, sizeof(ss->cipher_state));
}

static void ss_mix_hash(noise_xxpsk3_symmetric_state_t *ss, const uint8_t *data,
                        size_t len) {
  SHA256_CTX context = {0};
  sha256_Init(&context);
  sha256_Update(&context, ss->handshake_hash, NOISE_XXPSK3_HASHLEN);
  sha256_Update(&context, data, len);
  sha256_Final(&context, ss->handshake_hash);
  memzero(&context, sizeof(context));
}

static void hkdf3(const uint8_t *chaining_key, size_t chaining_key_len,
                  const uint8_t *key, size_t key_len,
                  uint8_t (*output1)[NOISE_XXPSK3_HASHLEN],
                  uint8_t (*output2)[NOISE_XXPSK3_HASHLEN],
                  uint8_t (*output3)[NOISE_XXPSK3_HASHLEN]) {
  uint8_t temp_key[NOISE_XXPSK3_HASHLEN] = {0};
  hmac_sha256(chaining_key, chaining_key_len, key, key_len, temp_key);

  uint8_t buf[NOISE_XXPSK3_HASHLEN + 1] = {0};
  buf[0] = 0x1;
  hmac_sha256(temp_key, NOISE_XXPSK3_HASHLEN, buf, 1, *output1);

  memcpy(buf, *output1, NOISE_XXPSK3_HASHLEN);
  buf[NOISE_XXPSK3_HASHLEN] = 0x2;

  hmac_sha256(temp_key, NOISE_XXPSK3_HASHLEN, buf, NOISE_XXPSK3_HASHLEN + 1,
              *output2);

  memcpy(buf, *output2, NOISE_XXPSK3_HASHLEN);
  buf[NOISE_XXPSK3_HASHLEN] = 0x3;

  hmac_sha256(temp_key, NOISE_XXPSK3_HASHLEN, buf, NOISE_XXPSK3_HASHLEN + 1,
              *output3);

  memzero(temp_key, sizeof(temp_key));  // Clear buffes from stack
  memzero(buf, sizeof(buf));
}

static void hkdf2(const uint8_t *chaining_key, size_t chaining_key_len,
                  const uint8_t *key, size_t key_len,
                  uint8_t (*output1)[NOISE_XXPSK3_HASHLEN],
                  uint8_t (*output2)[NOISE_XXPSK3_HASHLEN]) {
  uint8_t temp_key[NOISE_XXPSK3_HASHLEN] = {0};
  hmac_sha256(chaining_key, chaining_key_len, key, key_len, temp_key);

  uint8_t buf[NOISE_XXPSK3_HASHLEN + 1] = {0};
  buf[0] = 0x1;
  hmac_sha256(temp_key, NOISE_XXPSK3_HASHLEN, buf, 1, *output1);

  memcpy(buf, *output1, NOISE_XXPSK3_HASHLEN);
  buf[NOISE_XXPSK3_HASHLEN] = 0x2;

  hmac_sha256(temp_key, NOISE_XXPSK3_HASHLEN, buf, NOISE_XXPSK3_HASHLEN + 1,
              *output2);

  memzero(temp_key, sizeof(temp_key));  // Clear buffers from stack
  memzero(buf, sizeof(buf));
}

static void dh(const uint8_t (*private_key)[NOISE_XXPSK3_DHLEN],
               const uint8_t (*public_key)[NOISE_XXPSK3_DHLEN],
               uint8_t (*output)[NOISE_XXPSK3_DHLEN]) {
  curve25519_scalarmult(*output, *private_key, *public_key);
}

// Derives the AES-GCM context from the key; the key itself is not retained.
// The context is reused for all messages of the session.
static void cs_set_key(noise_xxpsk3_cipher_state_t *cs,
                       const uint8_t key[NOISE_XXPSK3_HASHLEN]) {
  memzero(&cs->gcm, sizeof(cs->gcm));
  cs->has_key =
      gcm_init_and_key(key, NOISE_XXPSK3_HASHLEN, &cs->gcm) == RETURN_GOOD;
  cs->nonce = 0;
}

static void ss_mix_key(
    noise_xxpsk3_symmetric_state_t *ss,
    const uint8_t (*input_key_material)[NOISE_XXPSK3_DHLEN]) {
  uint8_t temp_ck[NOISE_XXPSK3_HASHLEN] = {0};
  uint8_t temp_k[NOISE_XXPSK3_HASHLEN] = {0};

  // Mix key
  hkdf2(ss->chaining_key, NOISE_XXPSK3_HASHLEN, *input_key_material,
        NOISE_XXPSK3_DHLEN,
        &temp_ck,  // <- Output 1
        &temp_k    // <- Output 2
  );

  memcpy(ss->chaining_key, temp_ck, NOISE_XXPSK3_HASHLEN);
  cs_set_key(&ss->cipher_state, temp_k);

  memzero(temp_ck, sizeof(temp_ck));  // Clear buffers from stack
  memzero(temp_k, sizeof(temp_k));
}

static void ss_mix_key_and_hash(noise_xxpsk3_symmetric_state_t *ss,
                                const uint8_t (*key)[NOISE_XXPSK3_HASHLEN]) {
  uint8_t temp_ck[NOISE_XXPSK3_HASHLEN] = {0};
  uint8_t temp_h[NOISE_XXPSK3_HASHLEN] = {0};
  uint8_t temp_k[NOISE_XXPSK3_HASHLEN] = {0};

  hkdf3(ss->chaining_key, NOISE_XXPSK3_HASHLEN, (uint8_t *)key,
        NOISE_XXPSK3_HASHLEN, &temp_ck, &temp_h, &temp_k);

  memcpy(ss->chaining_key, temp_ck, NOISE_XXPSK3_HASHLEN);
  cs_set_key(&ss->cipher_state, temp_k);

  ss_mix_hash(ss, temp_h, NOISE_XXPSK3_HASHLEN);

  memzero(temp_ck, sizeof(temp_ck));  // Remove temp keys from stack
  memzero(temp_h, sizeof(temp_h));
  memzero(temp_k, sizeof(temp_k));
}

static void ss_ts_split(noise_xxpsk3_symmetric_state_t *ss,
                        noise_xxpsk3_transport_state_t *ts, bool initiator) {
  uint8_t send_key[NOISE_XXPSK3_HASHLEN] = {0};
  uint8_t receive_key[NOISE_XXPSK3_HASHLEN] = {0};

  if (initiator) {
    hkdf2(ss->chaining_key, NOISE_XXPSK3_HASHLEN, NULL, 0, &send_key,
          &receive_key);
  } else {
    hkdf2(ss->chaining_key, NOISE_XXPSK3_HASHLEN, NULL, 0, &receive_key,
          &send_key);
  }

  cs_set_key(&ts->send_cipher_state, send_key);
  cs_set_key(&ts->receive_cipher_state, receive_key);
  memcpy(ts->handshake_hash, ss->handshake_hash, NOISE_XXPSK3_HASHLEN);

  memzero(send_key, sizeof(send_key));
  memzero(receive_key, sizeof(receive_key));
}

/**
 * @brief generate new curve25519 keypair
 *
 * @param private_key output buffer for generated private key
 * @param public_key output buffer for derived public key
 */
static void generate_keypair(uint8_t (*private_key)[NOISE_XXPSK3_DHLEN],
                             uint8_t (*public_key)[NOISE_XXPSK3_DHLEN]) {
  random_buffer(*private_key, NOISE_XXPSK3_DHLEN);
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
 * by `plaintext_len + NOISE_XXPSK3_TAG_SIZE`
 * @return bool;
 */
static bool encrypt_with_ad(noise_xxpsk3_cipher_state_t *cs, const uint8_t *ad,
                            size_t ad_len, const uint8_t *plaintext,
                            size_t plaintext_len, uint8_t *ciphertext) {
  // A nonce at the limit is never used, so the counter below cannot wrap and no
  // message is ever protected with a repeated nonce
  if (!cs->has_key || cs->nonce >= NONCE_LIMIT) {
    return false;
  } else {
    if (plaintext_len > NOISE_XXPSK3_MAX_PLAINTEXT_SIZE) {
      // The resulting Noise message would exceed the maximum message size
      return false;
    }

    uint8_t nonce_bytes[NONCE_ARRAY_SIZE_BYTES] = {0};
    nonce_to_bytes(cs->nonce, &nonce_bytes);

    if (ciphertext != NULL && plaintext != NULL) {  // to suppress asan warning
      memcpy(ciphertext, plaintext, plaintext_len);
    }

    if (gcm_encrypt_message(nonce_bytes, NONCE_ARRAY_SIZE_BYTES, ad, ad_len,
                            ciphertext, plaintext_len,
                            ciphertext + plaintext_len, NOISE_XXPSK3_TAG_SIZE,
                            &cs->gcm) != RETURN_GOOD) {
      if (ciphertext != NULL) {
        memzero(ciphertext, plaintext_len + NOISE_XXPSK3_TAG_SIZE);
      }
      memzero(nonce_bytes, sizeof(nonce_bytes));
      return false;
    }

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
 * by `ciphertext_len - NOISE_XXPSK3_TAG_SIZE`
 * @return bool;
 */
static bool decrypt_with_ad(noise_xxpsk3_cipher_state_t *cs, const uint8_t *ad,
                            size_t ad_len, const uint8_t *ciphertext,
                            size_t ciphertext_len, uint8_t *plaintext) {
  if (!cs->has_key || cs->nonce >= NONCE_LIMIT) {
    return false;

  } else {
    if (ciphertext_len < NOISE_XXPSK3_TAG_SIZE) {
      // encrypted message is too short to contain the auth. tag
      return false;
    }

    if (ciphertext_len > NOISE_XXPSK3_MAX_MESSAGE_SIZE) {
      // message exceeds the maximum message size
      return false;
    }

    uint8_t nonce_bytes[NONCE_ARRAY_SIZE_BYTES] = {0};
    nonce_to_bytes(cs->nonce, &nonce_bytes);

    // decrypted message is shorter by auth. tag
    size_t plaintext_len = ciphertext_len - NOISE_XXPSK3_TAG_SIZE;

    if (plaintext != NULL && ciphertext != NULL) {  // to suppress asan warning
      memcpy(plaintext, ciphertext, plaintext_len);
    }

    if (gcm_decrypt_message(nonce_bytes, NONCE_ARRAY_SIZE_BYTES, ad, ad_len,
                            plaintext, plaintext_len,
                            ciphertext + plaintext_len, NOISE_XXPSK3_TAG_SIZE,
                            &cs->gcm) != RETURN_GOOD) {
      if (plaintext != NULL) {
        memzero(plaintext, plaintext_len);
      }
      memzero(nonce_bytes, sizeof(nonce_bytes));
      return false;
    }

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
 * `plaintext_len + NOISE_XXPSK3_TAG_SIZE`
 * @return bool;
 */
static bool ss_encrypt_and_hash(noise_xxpsk3_symmetric_state_t *ss,
                                const uint8_t *plaintext, size_t plaintext_len,
                                uint8_t *ciphertext) {
  if (!encrypt_with_ad(&ss->cipher_state, ss->handshake_hash,
                       NOISE_XXPSK3_HASHLEN, plaintext, plaintext_len,
                       ciphertext)) {
    return false;
  }

  ss_mix_hash(ss, ciphertext, plaintext_len + NOISE_XXPSK3_TAG_SIZE);

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
 * `ciphertext_len - NOISE_XXPSK3_TAG_SIZE`
 * @return bool;
 */
static bool ss_decrypt_and_hash(noise_xxpsk3_symmetric_state_t *ss,
                                const uint8_t *ciphertext,
                                size_t ciphertext_len, uint8_t *plaintext) {
  if (!decrypt_with_ad(&ss->cipher_state, ss->handshake_hash,
                       NOISE_XXPSK3_HASHLEN, ciphertext, ciphertext_len,
                       plaintext)) {
    return false;
  }

  ss_mix_hash(ss, ciphertext, ciphertext_len);

  return true;
}

static bool noise_xxpsk3_init_state(
    noise_xxpsk3_handshake_state_t *state,
    const uint8_t psk[NOISE_XXPSK3_DHLEN],
    const uint8_t static_private_key[NOISE_XXPSK3_DHLEN],
    const uint8_t static_public_key[NOISE_XXPSK3_DHLEN],
    const uint8_t *prologue, size_t prologue_len) {
  static const uint8_t XX_PROTOCOL_NAME[] = "Noise_XXpsk3_25519_AESGCM_SHA256";

  if (prologue == NULL && prologue_len != 0) {
    return false;
  }

  ss_init(&state->symmetric_state, XX_PROTOCOL_NAME,
          sizeof(XX_PROTOCOL_NAME) - 1);  // -1 substract the string terminator

  memcpy(state->static_private, static_private_key, NOISE_XXPSK3_DHLEN);
  memcpy(state->static_public, static_public_key, NOISE_XXPSK3_DHLEN);

  ss_mix_hash(&state->symmetric_state, prologue, prologue_len);

  memcpy(state->psk, psk, NOISE_XXPSK3_DHLEN);

  state->has_ephemeral_private = false;
  state->has_remote_ephemeral_public = false;
  return true;
}

#ifdef USE_NOISE_XXPSK3_RESPONDER

bool noise_xxpsk3_responder_init(
    noise_xxpsk3_responder_t *rspn, const uint8_t psk[NOISE_XXPSK3_DHLEN],
    const uint8_t static_private_key[NOISE_XXPSK3_DHLEN],
    const uint8_t static_public_key[NOISE_XXPSK3_DHLEN]) {
  if (rspn == NULL) {
    return false;
  }

  if (rspn->initialized || psk == NULL || static_private_key == NULL ||
      static_public_key == NULL) {
    goto cleanup;
  }

  // Clear the responder structure
  memset(rspn, 0, sizeof(noise_xxpsk3_responder_t));

  if (!noise_xxpsk3_init_state(&rspn->handshake_state, psk, static_private_key,
                               static_public_key, NULL, 0)) {
    goto cleanup;
  }

  rspn->handshake_stage = NOISE_XXPSK3_RSPN_WAITING_FOR_REQUEST1;
  rspn->initialized = true;
  rspn->has_transport_state = false;
  return true;

cleanup:
  noise_xxpsk3_responder_deinit(rspn);
  return false;
}

void noise_xxpsk3_responder_deinit(noise_xxpsk3_responder_t *rspn) {
  if (rspn != NULL) {
    // Clear the responder structure
    memzero(rspn, sizeof(noise_xxpsk3_responder_t));
  }
}

bool noise_xxpsk3_responder_handle_request1(
    noise_xxpsk3_responder_t *rspn, const uint8_t *request, size_t request_len,
    uint8_t *payload, size_t max_payload_size, size_t *payload_size) {
  if (rspn == NULL) {
    return false;
  }

  if (!rspn->initialized ||
      rspn->handshake_stage != NOISE_XXPSK3_RSPN_WAITING_FOR_REQUEST1 ||
      request == NULL || (payload == NULL && max_payload_size != 0)) {
    goto cleanup;
  }

  if (request_len < NOISE_XXPSK3_DHLEN + NOISE_XXPSK3_TAG_SIZE ||
      request_len > NOISE_XXPSK3_MAX_MESSAGE_SIZE) {
    goto cleanup;
  }

  noise_xxpsk3_handshake_state_t *state = &rspn->handshake_state;

  memcpy(state->remote_ephemeral_public, request, NOISE_XXPSK3_DHLEN);
  state->has_remote_ephemeral_public = true;
  ss_mix_hash(&state->symmetric_state, state->remote_ephemeral_public,
              NOISE_XXPSK3_DHLEN);

  // Calling ss_mix_key is required in PSK mode. See specification, Section 9.2:
  // https://noiseprotocol.org/noise.html#handshake-tokens
  ss_mix_key(&state->symmetric_state, &state->remote_ephemeral_public);

  size_t ciphertext_len = request_len - NOISE_XXPSK3_DHLEN;

  if (max_payload_size < ciphertext_len - NOISE_XXPSK3_TAG_SIZE) {
    goto cleanup;
  }

  // PSK mode established a key at the `e` token, so the payload is encrypted.
  if (!ss_decrypt_and_hash(&state->symmetric_state,
                           request + NOISE_XXPSK3_DHLEN, ciphertext_len,
                           payload)) {
    goto cleanup;
  }

  if (payload_size != NULL) {
    *payload_size = ciphertext_len - NOISE_XXPSK3_TAG_SIZE;
  }

  rspn->handshake_stage = NOISE_XXPSK3_RSPN_READY_FOR_RESPONSE1;
  return true;

cleanup:
  noise_xxpsk3_responder_deinit(rspn);
  return false;
}

bool noise_xxpsk3_responder_create_response1(
    noise_xxpsk3_responder_t *rspn, const uint8_t *payload, size_t payload_size,
    uint8_t *response, size_t max_response_size, size_t *response_size) {
  if (rspn == NULL) {
    return false;
  }

  noise_xxpsk3_handshake_state_t *state = &rspn->handshake_state;

  if (!rspn->initialized || response == NULL || response_size == NULL ||
      rspn->handshake_stage != NOISE_XXPSK3_RSPN_READY_FOR_RESPONSE1 ||
      !state->has_remote_ephemeral_public ||
      (payload == NULL && payload_size != 0)) {
    goto cleanup;
  }

  if (payload_size > NOISE_XXPSK3_MAX_MESSAGE_SIZE -
                         (2 * NOISE_XXPSK3_DHLEN + 2 * NOISE_XXPSK3_TAG_SIZE)) {
    goto cleanup;
  }

  // Check if response buffer is large enough to hold the response
  if (max_response_size <
      (2 * NOISE_XXPSK3_DHLEN + 2 * NOISE_XXPSK3_TAG_SIZE + payload_size)) {
    goto cleanup;
  }

  // Generate ephemeral keypair
  generate_keypair(&state->ephemeral_private,
                   (uint8_t (*)[NOISE_XXPSK3_DHLEN])response);
  state->has_ephemeral_private = true;

  ss_mix_hash(&state->symmetric_state, response, NOISE_XXPSK3_DHLEN);
  ss_mix_key(&state->symmetric_state,
             (uint8_t (*)[NOISE_XXPSK3_DHLEN])response);

  uint8_t input_key_material[NOISE_XXPSK3_DHLEN] = {0};
  dh(&state->ephemeral_private, &state->remote_ephemeral_public,
     &input_key_material);
  ss_mix_key(&state->symmetric_state, &input_key_material);
  memzero(input_key_material, sizeof(input_key_material));

  // Encrypt static public key
  if (!ss_encrypt_and_hash(&state->symmetric_state, state->static_public,
                           NOISE_XXPSK3_DHLEN, response + NOISE_XXPSK3_DHLEN)) {
    goto cleanup;
  }

  dh(&state->static_private, &state->remote_ephemeral_public,
     &input_key_material);
  ss_mix_key(&state->symmetric_state, &input_key_material);
  memzero(input_key_material, sizeof(input_key_material));

  // Encrypt payload
  if (!ss_encrypt_and_hash(
          &state->symmetric_state, payload, payload_size,
          response + (2 * NOISE_XXPSK3_DHLEN + NOISE_XXPSK3_TAG_SIZE))) {
    goto cleanup;
  }

  *response_size =
      2 * NOISE_XXPSK3_DHLEN + 2 * NOISE_XXPSK3_TAG_SIZE + payload_size;

  rspn->handshake_stage = NOISE_XXPSK3_RSPN_WAITING_FOR_REQUEST2;
  return true;

cleanup:
  noise_xxpsk3_responder_deinit(rspn);
  return false;
}

bool noise_xxpsk3_responder_handle_request2(
    noise_xxpsk3_responder_t *rspn, const uint8_t *request, size_t request_len,
    uint8_t remote_static_public_key[NOISE_XXPSK3_DHLEN], uint8_t *payload,
    size_t max_payload_size, size_t *payload_size) {
  if (rspn == NULL) {
    return false;
  }

  noise_xxpsk3_handshake_state_t *state = &rspn->handshake_state;

  if (!rspn->initialized || request == NULL ||
      remote_static_public_key == NULL ||
      rspn->handshake_stage != NOISE_XXPSK3_RSPN_WAITING_FOR_REQUEST2 ||
      !state->has_ephemeral_private ||
      (payload == NULL && max_payload_size != 0)) {
    goto cleanup;
  }
  // Check if message is large enough to contain the encrypted remote static
  // public key and at least empty encrypted payload (just NOISE_TAG)
  if (request_len < (NOISE_XXPSK3_DHLEN + 2 * NOISE_XXPSK3_TAG_SIZE) ||
      request_len > NOISE_XXPSK3_MAX_MESSAGE_SIZE) {
    goto cleanup;
  }

  if (!ss_decrypt_and_hash(&state->symmetric_state, request,
                           NOISE_XXPSK3_DHLEN + NOISE_XXPSK3_TAG_SIZE,
                           remote_static_public_key)) {
    goto cleanup;
  }

  uint8_t input_key_material[NOISE_XXPSK3_DHLEN] = {0};
  dh(&state->ephemeral_private,
     (const uint8_t (*)[NOISE_XXPSK3_DHLEN])remote_static_public_key,
     &input_key_material);
  ss_mix_key(&state->symmetric_state, &input_key_material);
  memzero(input_key_material, sizeof(input_key_material));

  ss_mix_key_and_hash(&state->symmetric_state, &state->psk);

  size_t ciphertext_len =
      request_len - (NOISE_XXPSK3_DHLEN + NOISE_XXPSK3_TAG_SIZE);

  if (max_payload_size < ciphertext_len - NOISE_XXPSK3_TAG_SIZE) {
    goto cleanup;
  }

  if (!ss_decrypt_and_hash(&state->symmetric_state,
                           request + NOISE_XXPSK3_DHLEN + NOISE_XXPSK3_TAG_SIZE,
                           ciphertext_len, payload)) {
    goto cleanup;
  }

  if (payload_size != NULL) {
    *payload_size = ciphertext_len - NOISE_XXPSK3_TAG_SIZE;
  }

  ss_ts_split(&state->symmetric_state, &rspn->transport_state, false);

  // Clean sensitive data from handler
  memzero(state, sizeof(noise_xxpsk3_handshake_state_t));

  rspn->has_transport_state = true;
  rspn->handshake_stage = NOISE_XXPSK3_RSPN_HANDSHAKE_COMPLETE;
  return true;

cleanup:
  if (remote_static_public_key != NULL) {
    memzero(remote_static_public_key, NOISE_XXPSK3_DHLEN);
  }
  noise_xxpsk3_responder_deinit(rspn);
  return false;
}

#endif  // USE_NOISE_XXPSK3_RESPONDER

#ifdef USE_NOISE_XXPSK3_INITIATOR

bool noise_xxpsk3_initiator_init(
    noise_xxpsk3_initiator_t *intr, const uint8_t psk[NOISE_XXPSK3_DHLEN],
    const uint8_t static_private_key[NOISE_XXPSK3_DHLEN],
    const uint8_t static_public_key[NOISE_XXPSK3_DHLEN]) {
  if (intr == NULL) {
    return false;
  }

  if (intr->initialized || psk == NULL || static_private_key == NULL ||
      static_public_key == NULL) {
    goto cleanup;
  }

  // Clear the initiator structure
  memset(intr, 0, sizeof(noise_xxpsk3_initiator_t));

  if (!noise_xxpsk3_init_state(&intr->handshake_state, psk, static_private_key,
                               static_public_key, NULL, 0)) {
    goto cleanup;
  }

  intr->handshake_stage = NOISE_XXPSK3_INTR_READY_FOR_REQUEST1;
  intr->initialized = true;
  intr->has_transport_state = false;
  return true;

cleanup:
  noise_xxpsk3_initiator_deinit(intr);
  return false;
}

void noise_xxpsk3_initiator_deinit(noise_xxpsk3_initiator_t *intr) {
  if (intr != NULL) {
    // Clear the initiator structure
    memzero(intr, sizeof(noise_xxpsk3_initiator_t));
  }
}

bool noise_xxpsk3_initiator_create_request1(
    noise_xxpsk3_initiator_t *intr, const uint8_t *payload, size_t payload_size,
    uint8_t *request, size_t max_request_size, size_t *request_size) {
  if (intr == NULL) {
    return false;
  }

  if (!intr->initialized ||
      intr->handshake_stage != NOISE_XXPSK3_INTR_READY_FOR_REQUEST1 ||
      (payload == NULL && payload_size != 0) || request == NULL ||
      request_size == NULL) {
    goto cleanup;
  }

  if (payload_size > NOISE_XXPSK3_MAX_MESSAGE_SIZE -
                         (NOISE_XXPSK3_DHLEN + NOISE_XXPSK3_TAG_SIZE)) {
    goto cleanup;
  }

  if (max_request_size <
      (NOISE_XXPSK3_DHLEN + payload_size + NOISE_XXPSK3_TAG_SIZE)) {
    goto cleanup;
  }

  noise_xxpsk3_handshake_state_t *state = &intr->handshake_state;

  // Generate ephemeral keypair
  generate_keypair(&state->ephemeral_private,
                   (uint8_t (*)[NOISE_XXPSK3_DHLEN])request);
  state->has_ephemeral_private = true;

  ss_mix_hash(&state->symmetric_state, request, NOISE_XXPSK3_DHLEN);
  ss_mix_key(&state->symmetric_state, (uint8_t (*)[NOISE_XXPSK3_DHLEN])request);

  // PSK mode established a key at the `e` token, so the payload is encrypted.
  if (!ss_encrypt_and_hash(&state->symmetric_state, payload, payload_size,
                           request + NOISE_XXPSK3_DHLEN)) {
    goto cleanup;
  }

  *request_size = NOISE_XXPSK3_DHLEN + payload_size + NOISE_XXPSK3_TAG_SIZE;
  intr->handshake_stage = NOISE_XXPSK3_INTR_WAITING_FOR_RESPONSE1;
  return true;

cleanup:
  noise_xxpsk3_initiator_deinit(intr);
  return false;
}

bool noise_xxpsk3_initiator_handle_response1(
    noise_xxpsk3_initiator_t *intr, const uint8_t *response,
    size_t response_len, uint8_t remote_static_public_key[NOISE_XXPSK3_DHLEN],
    uint8_t *payload, size_t max_payload_size, size_t *payload_size) {
  if (intr == NULL) {
    return false;
  }

  if (!intr->initialized ||
      intr->handshake_stage != NOISE_XXPSK3_INTR_WAITING_FOR_RESPONSE1 ||
      response == NULL || remote_static_public_key == NULL ||
      (payload == NULL && max_payload_size != 0)) {
    goto cleanup;
  }

  if (response_len < 2 * NOISE_XXPSK3_DHLEN + 2 * NOISE_XXPSK3_TAG_SIZE ||
      response_len > NOISE_XXPSK3_MAX_MESSAGE_SIZE) {
    goto cleanup;
  }

  noise_xxpsk3_handshake_state_t *state = &intr->handshake_state;

  memcpy(state->remote_ephemeral_public, response, NOISE_XXPSK3_DHLEN);
  state->has_remote_ephemeral_public = true;
  ss_mix_hash(&state->symmetric_state, state->remote_ephemeral_public,
              NOISE_XXPSK3_DHLEN);
  ss_mix_key(&state->symmetric_state, &state->remote_ephemeral_public);

  uint8_t input_key_material[NOISE_XXPSK3_DHLEN] = {0};
  dh(&state->ephemeral_private, &state->remote_ephemeral_public,
     &input_key_material);
  ss_mix_key(&state->symmetric_state, &input_key_material);
  memzero(input_key_material, sizeof(input_key_material));

  if (!ss_decrypt_and_hash(&state->symmetric_state,
                           response + NOISE_XXPSK3_DHLEN,
                           NOISE_XXPSK3_DHLEN + NOISE_XXPSK3_TAG_SIZE,
                           remote_static_public_key)) {
    goto cleanup;
  }

  dh(&state->ephemeral_private,
     (const uint8_t (*)[NOISE_XXPSK3_DHLEN])remote_static_public_key,
     &input_key_material);
  ss_mix_key(&state->symmetric_state, &input_key_material);
  memzero(input_key_material, sizeof(input_key_material));

  size_t ciphertext_len =
      response_len - (2 * NOISE_XXPSK3_DHLEN + NOISE_XXPSK3_TAG_SIZE);

  if (max_payload_size < ciphertext_len - NOISE_XXPSK3_TAG_SIZE) {
    goto cleanup;
  }

  if (!ss_decrypt_and_hash(
          &state->symmetric_state,
          response + (2 * NOISE_XXPSK3_DHLEN + NOISE_XXPSK3_TAG_SIZE),
          ciphertext_len, payload)) {
    goto cleanup;
  }

  if (payload_size != NULL) {
    *payload_size = ciphertext_len - NOISE_XXPSK3_TAG_SIZE;
  }

  intr->handshake_stage = NOISE_XXPSK3_INTR_READY_FOR_REQUEST2;

  return true;

cleanup:
  if (remote_static_public_key != NULL) {
    memzero(remote_static_public_key, NOISE_XXPSK3_DHLEN);
  }
  noise_xxpsk3_initiator_deinit(intr);
  return false;
}

bool noise_xxpsk3_initiator_create_request2(
    noise_xxpsk3_initiator_t *intr, const uint8_t *payload, size_t payload_size,
    uint8_t *request, size_t max_request_size, size_t *request_size) {
  if (intr == NULL) {
    return false;
  }

  if (!intr->initialized ||
      intr->handshake_stage != NOISE_XXPSK3_INTR_READY_FOR_REQUEST2 ||
      (payload == NULL && payload_size != 0) || request == NULL ||
      request_size == NULL) {
    goto cleanup;
  }

  if (payload_size > NOISE_XXPSK3_MAX_MESSAGE_SIZE -
                         (NOISE_XXPSK3_DHLEN + 2 * NOISE_XXPSK3_TAG_SIZE)) {
    goto cleanup;
  }

  if (max_request_size <
      (NOISE_XXPSK3_DHLEN + 2 * NOISE_XXPSK3_TAG_SIZE + payload_size)) {
    goto cleanup;
  }

  noise_xxpsk3_handshake_state_t *state = &intr->handshake_state;

  if (!ss_encrypt_and_hash(&state->symmetric_state, state->static_public,
                           NOISE_XXPSK3_DHLEN, request)) {
    goto cleanup;
  }

  uint8_t input_key_material[NOISE_XXPSK3_DHLEN] = {0};
  dh(&state->static_private, &state->remote_ephemeral_public,
     &input_key_material);
  ss_mix_key(&state->symmetric_state, &input_key_material);
  memzero(input_key_material, sizeof(input_key_material));

  ss_mix_key_and_hash(&state->symmetric_state, &state->psk);

  if (!ss_encrypt_and_hash(
          &state->symmetric_state, payload, payload_size,
          request + NOISE_XXPSK3_DHLEN + NOISE_XXPSK3_TAG_SIZE)) {
    goto cleanup;
  }

  *request_size = NOISE_XXPSK3_DHLEN + 2 * NOISE_XXPSK3_TAG_SIZE + payload_size;

  ss_ts_split(&state->symmetric_state, &intr->transport_state, true);
  memzero(state, sizeof(noise_xxpsk3_handshake_state_t));
  intr->has_transport_state = true;

  intr->handshake_stage = NOISE_XXPSK3_INTR_HANDSHAKE_COMPLETE;

  return true;

cleanup:
  noise_xxpsk3_initiator_deinit(intr);
  return false;
}

#endif  // USE_NOISE_XXPSK3_INITIATOR

bool noise_xxpsk3_send_message(noise_xxpsk3_transport_state_t *ts,
                               const uint8_t *payload, size_t payload_size,
                               uint8_t *ciphertext, size_t max_ciphertext_size,
                               size_t *ciphertext_size) {
  if (ts == NULL || (payload == NULL && payload_size != 0) ||
      ciphertext == NULL || ciphertext_size == NULL) {
    return false;
  }

  if (payload_size > NOISE_XXPSK3_MAX_PLAINTEXT_SIZE) {
    return false;
  }

  if (max_ciphertext_size < payload_size + NOISE_XXPSK3_TAG_SIZE) {
    return false;
  }

  if (!encrypt_with_ad(&ts->send_cipher_state, NULL, 0, payload, payload_size,
                       ciphertext)) {
    return false;
  }

  *ciphertext_size = payload_size + NOISE_XXPSK3_TAG_SIZE;
  return true;
}

bool noise_xxpsk3_receive_message(noise_xxpsk3_transport_state_t *ts,
                                  const uint8_t *ciphertext,
                                  size_t ciphertext_size, uint8_t *payload,
                                  size_t max_payload_size,
                                  size_t *payload_size) {
  if (ts == NULL || ciphertext == NULL || payload == NULL ||
      payload_size == NULL) {
    return false;
  }
  if (ciphertext_size < NOISE_XXPSK3_TAG_SIZE) {
    return false;
  }
  if (ciphertext_size > NOISE_XXPSK3_MAX_MESSAGE_SIZE) {
    return false;
  }
  if (ciphertext_size > max_payload_size + NOISE_XXPSK3_TAG_SIZE) {
    return false;
  }

  if (!decrypt_with_ad(&ts->receive_cipher_state, NULL, 0, ciphertext,
                       ciphertext_size, payload)) {
    return false;
  }

  *payload_size = ciphertext_size - NOISE_XXPSK3_TAG_SIZE;
  return true;
}
