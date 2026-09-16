/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included
 * in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
 * OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
 * OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 * ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 */

#include <string.h>

#include "aes/aesgcm.h"
#include "hmac.h"
#include "memzero.h"
#include "noise_pqikpsk1.h"
#include "rand.h"
#include "sha2.h"
#include "xwing.h"

// The counter is restricted to 48 bits: 2^48 messages of at most 65535 bytes
// produce at most 2^60 AES blocks under one key, well below the 2^64 blocks
// per key that NIST SP 800-38D, Appendix B recommends as a limit.
// https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=51288
#define NONCE_LIMIT 0x1000000000000ULL  // 2^48
#define NONCE_ARRAY_SIZE_BYTES 12

// Offsets of the handshake message fields, see the wire format in
// noise_pqikpsk1.h.
#define REQUEST_CT_R_OFFSET 0
#define REQUEST_PK_E_OFFSET XWING_CIPHERTEXT_SIZE
#define REQUEST_ENC_S_OFFSET (XWING_CIPHERTEXT_SIZE + XWING_PUBLIC_KEY_SIZE)
#define REQUEST_PAYLOAD_OFFSET                                 \
  (XWING_CIPHERTEXT_SIZE + 2 * XWING_PUBLIC_KEY_SIZE + \
   NOISE_PQIKPSK1_TAG_SIZE)

#define RESPONSE_CT_E_OFFSET 0
#define RESPONSE_ENC_CT_I_OFFSET XWING_CIPHERTEXT_SIZE
#define RESPONSE_PAYLOAD_OFFSET \
  (2 * XWING_CIPHERTEXT_SIZE + NOISE_PQIKPSK1_TAG_SIZE)

_Static_assert(
    NOISE_PQIKPSK1_REQUEST_OVERHEAD < NOISE_PQIKPSK1_MAX_MESSAGE_SIZE,
    "The handshake request does not fit the maximal Noise message size");
_Static_assert(
    NOISE_PQIKPSK1_RESPONSE_OVERHEAD < NOISE_PQIKPSK1_MAX_MESSAGE_SIZE,
    "The handshake response does not fit the maximal Noise message size");

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

static void ss_init(noise_pqikpsk1_symmetric_state_t *ss,
                    const uint8_t *protocol_name, size_t protocol_name_len) {
  if (protocol_name_len <= NOISE_PQIKPSK1_HASHLEN) {
    memcpy(ss->handshake_hash, protocol_name, protocol_name_len);
    memset(ss->handshake_hash + protocol_name_len, 0,
           NOISE_PQIKPSK1_HASHLEN - protocol_name_len);
  } else {
    sha256_Raw(protocol_name, protocol_name_len, ss->handshake_hash);
  }

  memcpy(ss->chaining_key, ss->handshake_hash, NOISE_PQIKPSK1_HASHLEN);
  ss->cipher_state.has_key = false;
  ss->cipher_state.nonce = 0;
}

static void ss_mix_hash(noise_pqikpsk1_symmetric_state_t *ss,
                        const uint8_t *data, size_t len) {
  SHA256_CTX context = {0};
  sha256_Init(&context);
  sha256_Update(&context, ss->handshake_hash, NOISE_PQIKPSK1_HASHLEN);
  sha256_Update(&context, data, len);
  sha256_Final(&context, ss->handshake_hash);
  memzero(&context, sizeof(context));
}

static void hkdf3(const uint8_t *chaining_key, size_t chaining_key_len,
                  const uint8_t *key, size_t key_len,
                  uint8_t (*output1)[NOISE_PQIKPSK1_HASHLEN],
                  uint8_t (*output2)[NOISE_PQIKPSK1_HASHLEN],
                  uint8_t (*output3)[NOISE_PQIKPSK1_HASHLEN]) {
  uint8_t temp_key[NOISE_PQIKPSK1_HASHLEN] = {0};
  hmac_sha256(chaining_key, chaining_key_len, key, key_len, temp_key);

  uint8_t buf[NOISE_PQIKPSK1_HASHLEN + 1] = {0};
  buf[0] = 0x1;
  hmac_sha256(temp_key, NOISE_PQIKPSK1_HASHLEN, buf, 1, *output1);

  memcpy(buf, *output1, NOISE_PQIKPSK1_HASHLEN);
  buf[NOISE_PQIKPSK1_HASHLEN] = 0x2;

  hmac_sha256(temp_key, NOISE_PQIKPSK1_HASHLEN, buf,
              NOISE_PQIKPSK1_HASHLEN + 1, *output2);

  memcpy(buf, *output2, NOISE_PQIKPSK1_HASHLEN);
  buf[NOISE_PQIKPSK1_HASHLEN] = 0x3;

  hmac_sha256(temp_key, NOISE_PQIKPSK1_HASHLEN, buf,
              NOISE_PQIKPSK1_HASHLEN + 1, *output3);

  memzero(temp_key, sizeof(temp_key));  // Clear buffers from stack
  memzero(buf, sizeof(buf));
}

static void hkdf2(const uint8_t *chaining_key, size_t chaining_key_len,
                  const uint8_t *key, size_t key_len,
                  uint8_t (*output1)[NOISE_PQIKPSK1_HASHLEN],
                  uint8_t (*output2)[NOISE_PQIKPSK1_HASHLEN]) {
  uint8_t temp_key[NOISE_PQIKPSK1_HASHLEN] = {0};
  hmac_sha256(chaining_key, chaining_key_len, key, key_len, temp_key);

  uint8_t buf[NOISE_PQIKPSK1_HASHLEN + 1] = {0};
  buf[0] = 0x1;
  hmac_sha256(temp_key, NOISE_PQIKPSK1_HASHLEN, buf, 1, *output1);

  memcpy(buf, *output1, NOISE_PQIKPSK1_HASHLEN);
  buf[NOISE_PQIKPSK1_HASHLEN] = 0x2;

  hmac_sha256(temp_key, NOISE_PQIKPSK1_HASHLEN, buf,
              NOISE_PQIKPSK1_HASHLEN + 1, *output2);

  memzero(temp_key, sizeof(temp_key));  // Clear buffers from stack
  memzero(buf, sizeof(buf));
}

static void ss_mix_key(noise_pqikpsk1_symmetric_state_t *ss,
                       const uint8_t *input_key_material,
                       size_t input_key_material_len) {
  hkdf2(ss->chaining_key, NOISE_PQIKPSK1_HASHLEN, input_key_material,
        input_key_material_len,
        &ss->chaining_key,     // <- Output 1
        &ss->cipher_state.key  // <- Output 2
  );
  ss->cipher_state.has_key = true;
  ss->cipher_state.nonce = 0;
}

static void ss_mix_key_and_hash(noise_pqikpsk1_symmetric_state_t *ss,
                                const uint8_t *input_key_material,
                                size_t input_key_material_len) {
  uint8_t temp_h[NOISE_PQIKPSK1_HASHLEN] = {0};

  hkdf3(ss->chaining_key, NOISE_PQIKPSK1_HASHLEN, input_key_material,
        input_key_material_len, &ss->chaining_key, &temp_h,
        &ss->cipher_state.key);

  ss->cipher_state.has_key = true;
  ss->cipher_state.nonce = 0;
  ss_mix_hash(ss, temp_h, NOISE_PQIKPSK1_HASHLEN);
  memzero(temp_h, sizeof(temp_h));  // Remove temp keys from stack
}

static void ss_ts_split(noise_pqikpsk1_symmetric_state_t *ss,
                        noise_pqikpsk1_transport_state_t *ts, bool initiator) {
  if (initiator) {
    hkdf2(ss->chaining_key, NOISE_PQIKPSK1_HASHLEN, NULL, 0,
          &ts->send_cipher_state.key, &ts->receive_cipher_state.key);
  } else {
    hkdf2(ss->chaining_key, NOISE_PQIKPSK1_HASHLEN, NULL, 0,
          &ts->receive_cipher_state.key, &ts->send_cipher_state.key);
  }

  ts->send_cipher_state.has_key = true;
  ts->send_cipher_state.nonce = 0;
  ts->receive_cipher_state.has_key = true;
  ts->receive_cipher_state.nonce = 0;
  memcpy(ts->handshake_hash, ss->handshake_hash, NOISE_PQIKPSK1_HASHLEN);
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
 * by `plaintext_len + NOISE_PQIKPSK1_TAG_SIZE`
 * @return bool;
 */
static bool encrypt_with_ad(noise_pqikpsk1_cipher_state_t *cs,
                            const uint8_t *ad, size_t ad_len,
                            const uint8_t *plaintext, size_t plaintext_len,
                            uint8_t *ciphertext) {
  // A nonce at the limit is never used, so the counter below cannot wrap and no
  // message is ever protected with a repeated nonce
  if (!cs->has_key || cs->nonce >= NONCE_LIMIT) {
    cs->has_key = false;
    memzero(cs->key, NOISE_PQIKPSK1_HASHLEN);
    return false;
  } else {
    // Encrypt with AEAD
    gcm_ctx ctx = {0};
    if (gcm_init_and_key(cs->key, NOISE_PQIKPSK1_HASHLEN, &ctx) !=
        RETURN_GOOD) {
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
                            ciphertext + plaintext_len,
                            NOISE_PQIKPSK1_TAG_SIZE, &ctx) != RETURN_GOOD) {
      memzero(&ctx, sizeof(ctx));
      if (ciphertext != NULL) {
        memzero(ciphertext, plaintext_len + NOISE_PQIKPSK1_TAG_SIZE);
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
 * @brief decrypt with associated data
 *
 * @param cs cipher state containing the key and nonce for decryption
 * @param ad pointer to the associated data
 * @param ad_len length of the associated data
 * @param ciphertext pointer to the ciphertext input of size defined
 * by `ciphertext_len`
 * @param ciphertext_len size of the ciphertext
 * @param plaintext pointer to the plaintext output of size defined
 * by `ciphertext_len - NOISE_PQIKPSK1_TAG_SIZE`
 * @return bool;
 */
static bool decrypt_with_ad(noise_pqikpsk1_cipher_state_t *cs,
                            const uint8_t *ad, size_t ad_len,
                            const uint8_t *ciphertext, size_t ciphertext_len,
                            uint8_t *plaintext) {
  if (!cs->has_key || cs->nonce >= NONCE_LIMIT) {
    cs->has_key = false;
    memzero(cs->key, NOISE_PQIKPSK1_HASHLEN);
    return false;
  } else {
    if (ciphertext_len < NOISE_PQIKPSK1_TAG_SIZE) {
      // encrypted message is too short to contain the auth. tag
      return false;
    }

    // Decrypt with AEAD
    gcm_ctx ctx = {0};
    if (gcm_init_and_key(cs->key, NOISE_PQIKPSK1_HASHLEN, &ctx) !=
        RETURN_GOOD) {
      memzero(&ctx, sizeof(ctx));
      return false;
    }

    uint8_t nonce_bytes[NONCE_ARRAY_SIZE_BYTES] = {0};
    nonce_to_bytes(cs->nonce, &nonce_bytes);

    // decrypted message is shorter by auth. tag
    size_t plaintext_len = ciphertext_len - NOISE_PQIKPSK1_TAG_SIZE;

    if (plaintext != NULL && ciphertext != NULL) {  // to suppress asan warning
      memcpy(plaintext, ciphertext, plaintext_len);
    }

    if (gcm_decrypt_message(nonce_bytes, NONCE_ARRAY_SIZE_BYTES, ad, ad_len,
                            plaintext, plaintext_len,
                            ciphertext + plaintext_len,
                            NOISE_PQIKPSK1_TAG_SIZE, &ctx) != RETURN_GOOD) {
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
 * `plaintext_len + NOISE_PQIKPSK1_TAG_SIZE`
 * @return bool;
 */
static bool ss_encrypt_and_hash(noise_pqikpsk1_symmetric_state_t *ss,
                                const uint8_t *plaintext, size_t plaintext_len,
                                uint8_t *ciphertext) {
  if (!encrypt_with_ad(&ss->cipher_state, ss->handshake_hash,
                       NOISE_PQIKPSK1_HASHLEN, plaintext, plaintext_len,
                       ciphertext)) {
    return false;
  }

  ss_mix_hash(ss, ciphertext, plaintext_len + NOISE_PQIKPSK1_TAG_SIZE);

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
 * `ciphertext_len - NOISE_PQIKPSK1_TAG_SIZE`
 * @return bool;
 */
static bool ss_decrypt_and_hash(noise_pqikpsk1_symmetric_state_t *ss,
                                const uint8_t *ciphertext,
                                size_t ciphertext_len, uint8_t *plaintext) {
  if (!decrypt_with_ad(&ss->cipher_state, ss->handshake_hash,
                       NOISE_PQIKPSK1_HASHLEN, ciphertext, ciphertext_len,
                       plaintext)) {
    return false;
  }

  ss_mix_hash(ss, ciphertext, ciphertext_len);

  return true;
}

static bool noise_pqikpsk1_init_state(
    noise_pqikpsk1_handshake_state_t *state,
    const uint8_t psk[NOISE_PQIKPSK1_PSK_SIZE],
    const uint8_t static_private_key[XWING_PRIVATE_KEY_SIZE],
    const uint8_t static_public_key[XWING_PUBLIC_KEY_SIZE],
    const uint8_t *prologue, size_t prologue_len) {
  static const uint8_t PQIK_PROTOCOL_NAME[] =
      "Noise_pqIKpsk1_XWing_AESGCM_SHA256";

  if (prologue == NULL && prologue_len != 0) {
    return false;
  }

  ss_init(&state->symmetric_state, PQIK_PROTOCOL_NAME,
          sizeof(PQIK_PROTOCOL_NAME) - 1);  // -1 subtract the string terminator

  memcpy(state->psk, psk, NOISE_PQIKPSK1_PSK_SIZE);
  memcpy(state->static_private, static_private_key, XWING_PRIVATE_KEY_SIZE);
  memcpy(state->static_public, static_public_key, XWING_PUBLIC_KEY_SIZE);

  ss_mix_hash(&state->symmetric_state, prologue, prologue_len);

  state->has_remote_static_public = false;
  state->has_ephemeral_private = false;
  state->has_remote_ephemeral_public = false;
  return true;
}

bool noise_pqikpsk1_initiator_init(
    noise_pqikpsk1_initiator_t *intr,
    const uint8_t psk[NOISE_PQIKPSK1_PSK_SIZE],
    const uint8_t static_private_key[XWING_PRIVATE_KEY_SIZE],
    const uint8_t static_public_key[XWING_PUBLIC_KEY_SIZE],
    const uint8_t responder_static_public_key[XWING_PUBLIC_KEY_SIZE],
    const uint8_t *prologue, size_t prologue_size) {
  if (intr == NULL) {
    return false;
  }

  if (intr->initialized || psk == NULL || static_private_key == NULL ||
      static_public_key == NULL || responder_static_public_key == NULL) {
    goto cleanup;
  }

  // Clear the initiator structure
  memset(intr, 0, sizeof(noise_pqikpsk1_initiator_t));

  if (!noise_pqikpsk1_init_state(&intr->handshake_state, psk,
                                 static_private_key, static_public_key,
                                 prologue, prologue_size)) {
    goto cleanup;
  }

  // Pre-message `<- s`: the responder's static public key is mixed into the
  // handshake hash.
  memcpy(intr->handshake_state.remote_static_public,
         responder_static_public_key, XWING_PUBLIC_KEY_SIZE);
  intr->handshake_state.has_remote_static_public = true;
  ss_mix_hash(&intr->handshake_state.symmetric_state,
              intr->handshake_state.remote_static_public,
              XWING_PUBLIC_KEY_SIZE);

  intr->handshake_stage = NOISE_PQIKPSK1_INTR_READY_FOR_REQUEST;
  intr->initialized = true;
  intr->has_transport_state = false;
  return true;

cleanup:
  noise_pqikpsk1_initiator_deinit(intr);
  return false;
}

void noise_pqikpsk1_initiator_deinit(noise_pqikpsk1_initiator_t *intr) {
  if (intr != NULL) {
    // Clear the initiator structure
    memzero(intr, sizeof(noise_pqikpsk1_initiator_t));
  }
}

bool noise_pqikpsk1_initiator_create_request_derand(
    noise_pqikpsk1_initiator_t *intr,
    const uint8_t skem_seed[XWING_ENCAPSULATION_SEED_SIZE],
    const uint8_t ephemeral_private_key[XWING_PRIVATE_KEY_SIZE],
    const uint8_t *payload, size_t payload_size, uint8_t *request,
    size_t max_request_size, size_t *request_size) {
  if (intr == NULL) {
    return false;
  }

  noise_pqikpsk1_handshake_state_t *state = &intr->handshake_state;
  uint8_t shared_secret[XWING_SHARED_SECRET_SIZE] = {0};

  if (!intr->initialized ||
      intr->handshake_stage != NOISE_PQIKPSK1_INTR_READY_FOR_REQUEST ||
      skem_seed == NULL || ephemeral_private_key == NULL ||
      (payload == NULL && payload_size != 0) || request == NULL ||
      request_size == NULL) {
    goto cleanup;
  }

  if (payload_size > NOISE_PQIKPSK1_MAX_REQUEST_PAYLOAD_SIZE) {
    goto cleanup;
  }

  if (max_request_size < NOISE_PQIKPSK1_REQUEST_OVERHEAD + payload_size) {
    goto cleanup;
  }

  // `skem` token: encapsulate to the responder's static public key.  There is
  // no symmetric key yet, so the ciphertext is sent in cleartext.
  if (!xwing_encapsulate_from_seed(skem_seed, state->remote_static_public,
                                   request + REQUEST_CT_R_OFFSET,
                                   shared_secret)) {
    goto cleanup;
  }
  ss_mix_hash(&state->symmetric_state, request + REQUEST_CT_R_OFFSET,
              XWING_CIPHERTEXT_SIZE);
  ss_mix_key_and_hash(&state->symmetric_state, shared_secret,
                      XWING_SHARED_SECRET_SIZE);
  memzero(shared_secret, sizeof(shared_secret));

  // `e` token: the ephemeral public key is sent in cleartext.  Calling
  // ss_mix_key is required in PSK mode.  See specification, Section 9.2:
  // https://noiseprotocol.org/noise.html#handshake-tokens
  memcpy(state->ephemeral_private, ephemeral_private_key,
         XWING_PRIVATE_KEY_SIZE);
  state->has_ephemeral_private = true;
  if (!xwing_derive_public_key(state->ephemeral_private,
                               request + REQUEST_PK_E_OFFSET)) {
    goto cleanup;
  }
  ss_mix_hash(&state->symmetric_state, request + REQUEST_PK_E_OFFSET,
              XWING_PUBLIC_KEY_SIZE);
  ss_mix_key(&state->symmetric_state, request + REQUEST_PK_E_OFFSET,
             XWING_PUBLIC_KEY_SIZE);

  // `s` token: encrypt the initiator's static public key
  if (!ss_encrypt_and_hash(&state->symmetric_state, state->static_public,
                           XWING_PUBLIC_KEY_SIZE,
                           request + REQUEST_ENC_S_OFFSET)) {
    goto cleanup;
  }

  // `psk` token
  ss_mix_key_and_hash(&state->symmetric_state, state->psk,
                      NOISE_PQIKPSK1_PSK_SIZE);

  // Encrypt payload
  if (!ss_encrypt_and_hash(&state->symmetric_state, payload, payload_size,
                           request + REQUEST_PAYLOAD_OFFSET)) {
    goto cleanup;
  }

  *request_size = NOISE_PQIKPSK1_REQUEST_OVERHEAD + payload_size;
  intr->handshake_stage = NOISE_PQIKPSK1_INTR_WAITING_FOR_RESPONSE;
  return true;

cleanup:
  memzero(shared_secret, sizeof(shared_secret));
  noise_pqikpsk1_initiator_deinit(intr);
  return false;
}

bool noise_pqikpsk1_initiator_create_request(
    noise_pqikpsk1_initiator_t *intr, const uint8_t *payload,
    size_t payload_size, uint8_t *request, size_t max_request_size,
    size_t *request_size) {
  uint8_t skem_seed[XWING_ENCAPSULATION_SEED_SIZE] = {0};
  uint8_t ephemeral_private_key[XWING_PRIVATE_KEY_SIZE] = {0};
  random_buffer(skem_seed, sizeof(skem_seed));
  random_buffer(ephemeral_private_key, sizeof(ephemeral_private_key));

  bool result = noise_pqikpsk1_initiator_create_request_derand(
      intr, skem_seed, ephemeral_private_key, payload, payload_size, request,
      max_request_size, request_size);

  memzero(skem_seed, sizeof(skem_seed));
  memzero(ephemeral_private_key, sizeof(ephemeral_private_key));
  return result;
}

bool noise_pqikpsk1_initiator_handle_response(
    noise_pqikpsk1_initiator_t *intr, const uint8_t *response,
    size_t response_size, uint8_t *payload, size_t max_payload_size,
    size_t *payload_size) {
  if (intr == NULL) {
    return false;
  }

  noise_pqikpsk1_handshake_state_t *state = &intr->handshake_state;
  uint8_t shared_secret[XWING_SHARED_SECRET_SIZE] = {0};
  uint8_t ciphertext[XWING_CIPHERTEXT_SIZE] = {0};

  if (!intr->initialized ||
      intr->handshake_stage != NOISE_PQIKPSK1_INTR_WAITING_FOR_RESPONSE ||
      !state->has_ephemeral_private || response == NULL ||
      (payload == NULL && max_payload_size != 0)) {
    goto cleanup;
  }

  if (response_size < NOISE_PQIKPSK1_RESPONSE_OVERHEAD ||
      response_size > NOISE_PQIKPSK1_MAX_MESSAGE_SIZE) {
    goto cleanup;
  }

  size_t payload_ciphertext_len = response_size - RESPONSE_PAYLOAD_OFFSET;

  if (max_payload_size < payload_ciphertext_len - NOISE_PQIKPSK1_TAG_SIZE) {
    goto cleanup;
  }

  // `ekem` token: decapsulate with the ephemeral private key
  ss_mix_hash(&state->symmetric_state, response + RESPONSE_CT_E_OFFSET,
              XWING_CIPHERTEXT_SIZE);
  if (!xwing_decapsulate(state->ephemeral_private,
                         response + RESPONSE_CT_E_OFFSET, shared_secret)) {
    goto cleanup;
  }
  ss_mix_key(&state->symmetric_state, shared_secret,
             XWING_SHARED_SECRET_SIZE);

  // `skem` token: decrypt the encapsulation for the initiator's static key
  // and decapsulate with the static private key
  if (!ss_decrypt_and_hash(
          &state->symmetric_state, response + RESPONSE_ENC_CT_I_OFFSET,
          XWING_CIPHERTEXT_SIZE + NOISE_PQIKPSK1_TAG_SIZE, ciphertext)) {
    goto cleanup;
  }
  if (!xwing_decapsulate(state->static_private, ciphertext, shared_secret)) {
    goto cleanup;
  }
  ss_mix_key_and_hash(&state->symmetric_state, shared_secret,
                      XWING_SHARED_SECRET_SIZE);
  memzero(shared_secret, sizeof(shared_secret));
  memzero(ciphertext, sizeof(ciphertext));

  // Decrypt payload
  if (!ss_decrypt_and_hash(&state->symmetric_state,
                           response + RESPONSE_PAYLOAD_OFFSET,
                           payload_ciphertext_len, payload)) {
    goto cleanup;
  }

  if (payload_size != NULL) {
    *payload_size = payload_ciphertext_len - NOISE_PQIKPSK1_TAG_SIZE;
  }

  ss_ts_split(&state->symmetric_state, &intr->transport_state, true);

  // Clean sensitive data from handler
  memzero(state, sizeof(noise_pqikpsk1_handshake_state_t));

  intr->has_transport_state = true;
  intr->handshake_stage = NOISE_PQIKPSK1_INTR_HANDSHAKE_COMPLETE;
  return true;

cleanup:
  memzero(shared_secret, sizeof(shared_secret));
  memzero(ciphertext, sizeof(ciphertext));
  noise_pqikpsk1_initiator_deinit(intr);
  return false;
}

bool noise_pqikpsk1_responder_init(
    noise_pqikpsk1_responder_t *rspn,
    const uint8_t psk[NOISE_PQIKPSK1_PSK_SIZE],
    const uint8_t static_private_key[XWING_PRIVATE_KEY_SIZE],
    const uint8_t static_public_key[XWING_PUBLIC_KEY_SIZE],
    const uint8_t *prologue, size_t prologue_size) {
  if (rspn == NULL) {
    return false;
  }

  if (rspn->initialized || psk == NULL || static_private_key == NULL ||
      static_public_key == NULL) {
    goto cleanup;
  }

  // Clear the responder structure
  memset(rspn, 0, sizeof(noise_pqikpsk1_responder_t));

  if (!noise_pqikpsk1_init_state(&rspn->handshake_state, psk,
                                 static_private_key, static_public_key,
                                 prologue, prologue_size)) {
    goto cleanup;
  }

  // Pre-message `<- s`: the responder's static public key is mixed into the
  // handshake hash.
  ss_mix_hash(&rspn->handshake_state.symmetric_state,
              rspn->handshake_state.static_public, XWING_PUBLIC_KEY_SIZE);

  rspn->handshake_stage = NOISE_PQIKPSK1_RSPN_WAITING_FOR_REQUEST;
  rspn->initialized = true;
  rspn->has_transport_state = false;
  return true;

cleanup:
  noise_pqikpsk1_responder_deinit(rspn);
  return false;
}

void noise_pqikpsk1_responder_deinit(noise_pqikpsk1_responder_t *rspn) {
  if (rspn != NULL) {
    // Clear the responder structure
    memzero(rspn, sizeof(noise_pqikpsk1_responder_t));
  }
}

bool noise_pqikpsk1_responder_handle_request(
    noise_pqikpsk1_responder_t *rspn, const uint8_t *request,
    size_t request_size,
    uint8_t initiator_static_public_key[XWING_PUBLIC_KEY_SIZE],
    uint8_t *payload, size_t max_payload_size, size_t *payload_size) {
  if (rspn == NULL) {
    return false;
  }

  noise_pqikpsk1_handshake_state_t *state = &rspn->handshake_state;
  uint8_t shared_secret[XWING_SHARED_SECRET_SIZE] = {0};

  if (!rspn->initialized ||
      rspn->handshake_stage != NOISE_PQIKPSK1_RSPN_WAITING_FOR_REQUEST ||
      request == NULL || initiator_static_public_key == NULL ||
      (payload == NULL && max_payload_size != 0)) {
    goto cleanup;
  }

  if (request_size < NOISE_PQIKPSK1_REQUEST_OVERHEAD ||
      request_size > NOISE_PQIKPSK1_MAX_MESSAGE_SIZE) {
    goto cleanup;
  }

  size_t payload_ciphertext_len = request_size - REQUEST_PAYLOAD_OFFSET;

  if (max_payload_size < payload_ciphertext_len - NOISE_PQIKPSK1_TAG_SIZE) {
    goto cleanup;
  }

  // `skem` token: decapsulate with the responder's static private key
  ss_mix_hash(&state->symmetric_state, request + REQUEST_CT_R_OFFSET,
              XWING_CIPHERTEXT_SIZE);
  if (!xwing_decapsulate(state->static_private, request + REQUEST_CT_R_OFFSET,
                         shared_secret)) {
    goto cleanup;
  }
  ss_mix_key_and_hash(&state->symmetric_state, shared_secret,
                      XWING_SHARED_SECRET_SIZE);
  memzero(shared_secret, sizeof(shared_secret));

  // `e` token.  Calling ss_mix_key is required in PSK mode.  See
  // specification, Section 9.2:
  // https://noiseprotocol.org/noise.html#handshake-tokens
  memcpy(state->remote_ephemeral_public, request + REQUEST_PK_E_OFFSET,
         XWING_PUBLIC_KEY_SIZE);
  state->has_remote_ephemeral_public = true;
  ss_mix_hash(&state->symmetric_state, state->remote_ephemeral_public,
              XWING_PUBLIC_KEY_SIZE);
  ss_mix_key(&state->symmetric_state, state->remote_ephemeral_public,
             XWING_PUBLIC_KEY_SIZE);

  // `s` token: decrypt the initiator's static public key
  if (!ss_decrypt_and_hash(&state->symmetric_state,
                           request + REQUEST_ENC_S_OFFSET,
                           XWING_PUBLIC_KEY_SIZE + NOISE_PQIKPSK1_TAG_SIZE,
                           state->remote_static_public)) {
    goto cleanup;
  }
  state->has_remote_static_public = true;
  memcpy(initiator_static_public_key, state->remote_static_public,
         XWING_PUBLIC_KEY_SIZE);

  // `psk` token
  ss_mix_key_and_hash(&state->symmetric_state, state->psk,
                      NOISE_PQIKPSK1_PSK_SIZE);

  // Decrypt payload
  if (!ss_decrypt_and_hash(&state->symmetric_state,
                           request + REQUEST_PAYLOAD_OFFSET,
                           payload_ciphertext_len, payload)) {
    goto cleanup;
  }

  if (payload_size != NULL) {
    *payload_size = payload_ciphertext_len - NOISE_PQIKPSK1_TAG_SIZE;
  }

  rspn->handshake_stage = NOISE_PQIKPSK1_RSPN_READY_FOR_RESPONSE;
  return true;

cleanup:
  memzero(shared_secret, sizeof(shared_secret));
  if (initiator_static_public_key != NULL) {
    memzero(initiator_static_public_key, XWING_PUBLIC_KEY_SIZE);
  }
  noise_pqikpsk1_responder_deinit(rspn);
  return false;
}

bool noise_pqikpsk1_responder_create_response_derand(
    noise_pqikpsk1_responder_t *rspn,
    const uint8_t ekem_seed[XWING_ENCAPSULATION_SEED_SIZE],
    const uint8_t skem_seed[XWING_ENCAPSULATION_SEED_SIZE],
    const uint8_t *payload, size_t payload_size, uint8_t *response,
    size_t max_response_size, size_t *response_size) {
  if (rspn == NULL) {
    return false;
  }

  noise_pqikpsk1_handshake_state_t *state = &rspn->handshake_state;
  uint8_t shared_secret[XWING_SHARED_SECRET_SIZE] = {0};
  uint8_t ciphertext[XWING_CIPHERTEXT_SIZE] = {0};

  if (!rspn->initialized ||
      rspn->handshake_stage != NOISE_PQIKPSK1_RSPN_READY_FOR_RESPONSE ||
      !state->has_remote_ephemeral_public ||
      !state->has_remote_static_public || ekem_seed == NULL ||
      skem_seed == NULL || (payload == NULL && payload_size != 0) ||
      response == NULL || response_size == NULL) {
    goto cleanup;
  }

  if (payload_size > NOISE_PQIKPSK1_MAX_RESPONSE_PAYLOAD_SIZE) {
    goto cleanup;
  }

  if (max_response_size < NOISE_PQIKPSK1_RESPONSE_OVERHEAD + payload_size) {
    goto cleanup;
  }

  // `ekem` token: encapsulate to the initiator's ephemeral public key.  The
  // ciphertext is sent in cleartext.
  if (!xwing_encapsulate_from_seed(ekem_seed, state->remote_ephemeral_public,
                                   response + RESPONSE_CT_E_OFFSET,
                                   shared_secret)) {
    goto cleanup;
  }
  ss_mix_hash(&state->symmetric_state, response + RESPONSE_CT_E_OFFSET,
              XWING_CIPHERTEXT_SIZE);
  ss_mix_key(&state->symmetric_state, shared_secret,
             XWING_SHARED_SECRET_SIZE);

  // `skem` token: encapsulate to the initiator's static public key and
  // encrypt the ciphertext
  if (!xwing_encapsulate_from_seed(skem_seed, state->remote_static_public,
                                   ciphertext, shared_secret)) {
    goto cleanup;
  }
  if (!ss_encrypt_and_hash(&state->symmetric_state, ciphertext,
                           XWING_CIPHERTEXT_SIZE,
                           response + RESPONSE_ENC_CT_I_OFFSET)) {
    goto cleanup;
  }
  ss_mix_key_and_hash(&state->symmetric_state, shared_secret,
                      XWING_SHARED_SECRET_SIZE);
  memzero(shared_secret, sizeof(shared_secret));
  memzero(ciphertext, sizeof(ciphertext));

  // Encrypt payload
  if (!ss_encrypt_and_hash(&state->symmetric_state, payload, payload_size,
                           response + RESPONSE_PAYLOAD_OFFSET)) {
    goto cleanup;
  }

  *response_size = NOISE_PQIKPSK1_RESPONSE_OVERHEAD + payload_size;

  ss_ts_split(&state->symmetric_state, &rspn->transport_state, false);

  // Clean sensitive data from handler
  memzero(state, sizeof(noise_pqikpsk1_handshake_state_t));

  rspn->has_transport_state = true;
  rspn->handshake_stage = NOISE_PQIKPSK1_RSPN_HANDSHAKE_COMPLETE;
  return true;

cleanup:
  memzero(shared_secret, sizeof(shared_secret));
  memzero(ciphertext, sizeof(ciphertext));
  noise_pqikpsk1_responder_deinit(rspn);
  return false;
}

bool noise_pqikpsk1_responder_create_response(
    noise_pqikpsk1_responder_t *rspn, const uint8_t *payload,
    size_t payload_size, uint8_t *response, size_t max_response_size,
    size_t *response_size) {
  uint8_t ekem_seed[XWING_ENCAPSULATION_SEED_SIZE] = {0};
  uint8_t skem_seed[XWING_ENCAPSULATION_SEED_SIZE] = {0};
  random_buffer(ekem_seed, sizeof(ekem_seed));
  random_buffer(skem_seed, sizeof(skem_seed));

  bool result = noise_pqikpsk1_responder_create_response_derand(
      rspn, ekem_seed, skem_seed, payload, payload_size, response,
      max_response_size, response_size);

  memzero(ekem_seed, sizeof(ekem_seed));
  memzero(skem_seed, sizeof(skem_seed));
  return result;
}

bool noise_pqikpsk1_send_message(noise_pqikpsk1_transport_state_t *ts,
                                 const uint8_t *payload, size_t payload_size,
                                 uint8_t *ciphertext,
                                 size_t max_ciphertext_size,
                                 size_t *ciphertext_size) {
  if (ts == NULL || (payload == NULL && payload_size != 0) ||
      ciphertext == NULL || ciphertext_size == NULL) {
    return false;
  }

  if (payload_size > NOISE_PQIKPSK1_MAX_PLAINTEXT_SIZE) {
    return false;
  }

  if (max_ciphertext_size < payload_size + NOISE_PQIKPSK1_TAG_SIZE) {
    return false;
  }

  if (!encrypt_with_ad(&ts->send_cipher_state, NULL, 0, payload, payload_size,
                       ciphertext)) {
    return false;
  }

  *ciphertext_size = payload_size + NOISE_PQIKPSK1_TAG_SIZE;
  return true;
}

bool noise_pqikpsk1_receive_message(noise_pqikpsk1_transport_state_t *ts,
                                    const uint8_t *ciphertext,
                                    size_t ciphertext_size, uint8_t *payload,
                                    size_t max_payload_size,
                                    size_t *payload_size) {
  if (ts == NULL || ciphertext == NULL || payload == NULL ||
      payload_size == NULL) {
    return false;
  }
  if (ciphertext_size < NOISE_PQIKPSK1_TAG_SIZE) {
    return false;
  }
  if (ciphertext_size > NOISE_PQIKPSK1_MAX_MESSAGE_SIZE) {
    return false;
  }
  // The tag length check above rules out underflow
  if (ciphertext_size - NOISE_PQIKPSK1_TAG_SIZE > max_payload_size) {
    return false;
  }

  if (!decrypt_with_ad(&ts->receive_cipher_state, NULL, 0, ciphertext,
                       ciphertext_size, payload)) {
    return false;
  }

  *payload_size = ciphertext_size - NOISE_PQIKPSK1_TAG_SIZE;
  return true;
}
