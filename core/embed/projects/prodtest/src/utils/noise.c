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

#include "noise.h"
#include <trezor_rtl.h>

#include "aes/aesgcm.h"
#include "ed25519-donna/ed25519.h"
#include "hmac.h"
#include "memzero.h"
#include "noise.h"
#include "rand.h"
#include "sha2.h"

#define NONCE_LIMIT 0xFFFFFFFFFFFFFFFFULL
#define NONCE_ARRAY_SIZE_BYTES 12
#define NOISE_TAG_SIZE_BYTES 16
#define NOISE_MAX_PAYLOAD_BYTES 255

/**
@brief translate nonce into 12 Byte Big-endian Array with
4 zero byte padding.

@param nonce
@param output byte array
*/
static void nonce_to_bytes(uint64_t nonce,
                           uint8_t (*arr)[NONCE_ARRAY_SIZE_BYTES]) {
  (*arr)[0] = 0x0;
  (*arr)[1] = 0x0;
  (*arr)[2] = 0x0;
  (*arr)[3] = 0x0;

  for (uint8_t i = 4; i < NONCE_ARRAY_SIZE_BYTES; i++) {
    (*arr)[i] = (nonce >> (56 - (i - 4) * 8)) & 0xFF;
  }
}

static void ss_init(symmetric_state_t *ss, const uint8_t *protocol_name,
                    size_t protocol_name_len) {
  if (protocol_name_len <= HASHLEN) {
    memcpy(ss->handshake_hash, protocol_name, protocol_name_len);
    memzero(ss->handshake_hash + protocol_name_len,
            HASHLEN - protocol_name_len);
  } else {
    sha256_Raw(protocol_name, protocol_name_len, ss->handshake_hash);
  }

  memcpy(ss->chaining_key, ss->handshake_hash, HASHLEN);
  ss->cipher_state.has_key = false;
  ss->cipher_state.nonce = 0;
}

static void ss_mix_hash(symmetric_state_t *ss, const uint8_t *data,
                        size_t len) {
  SHA256_CTX context = {0};
  sha256_Init(&context);
  sha256_Update(&context, ss->handshake_hash, HASHLEN);
  sha256_Update(&context, data, len);
  sha256_Final(&context, ss->handshake_hash);
  memzero(&context, sizeof(context));
}

static void hkdf3(uint8_t *chaining_key, size_t chaining_key_len, uint8_t *key,
                  size_t key_len, uint8_t (*output1)[HASHLEN],
                  uint8_t (*output2)[HASHLEN], uint8_t (*output3)[HASHLEN]) {
  uint8_t temp_key[HASHLEN] = {0};
  hmac_sha256(chaining_key, chaining_key_len, key, key_len, temp_key);

  uint8_t buf[HASHLEN + 1] = {0};
  buf[0] = 0x1;
  hmac_sha256(temp_key, HASHLEN, buf, 1, *output1);

  memcpy(buf, *output1, HASHLEN);
  buf[HASHLEN] = 0x2;

  hmac_sha256(temp_key, HASHLEN, buf, HASHLEN + 1, *output2);

  memcpy(buf, *output2, HASHLEN);
  buf[HASHLEN] = 0x3;

  hmac_sha256(temp_key, HASHLEN, buf, HASHLEN + 1, *output3);

  memzero(temp_key, sizeof(temp_key));  // Clear buffes from stack
  memzero(buf, sizeof(buf));
}

static void hkdf2(uint8_t *chaining_key, size_t chaining_key_len, uint8_t *key,
                  size_t key_len, uint8_t (*output1)[HASHLEN],
                  uint8_t (*output2)[HASHLEN]) {
  uint8_t temp_key[HASHLEN] = {0};
  hmac_sha256(chaining_key, chaining_key_len, key, key_len, temp_key);

  uint8_t buf[HASHLEN + 1] = {0};
  buf[0] = 0x1;
  hmac_sha256(temp_key, HASHLEN, buf, 1, *output1);

  memcpy(buf, *output1, HASHLEN);
  buf[HASHLEN] = 0x2;

  hmac_sha256(temp_key, HASHLEN, buf, HASHLEN + 1, *output2);

  memzero(temp_key, sizeof(temp_key));  // Clear buffers from stack
  memzero(buf, sizeof(buf));
}

static void dh(uint8_t (*output)[DHLEN], uint8_t (*private_key)[DHLEN],
               uint8_t (*public_key)[DHLEN]) {
  curve25519_scalarmult(*output, *private_key, *public_key);
}

static void ss_mix_key(symmetric_state_t *ss,
                       uint8_t (*input_key_material)[DHLEN]) {
  // Mix key
  hkdf2(ss->chaining_key, HASHLEN, *input_key_material, DHLEN,
        &ss->chaining_key,     // <- Output 1
        &ss->cipher_state.key  // <- Output 2
  );
  ss->cipher_state.has_key = true;
  ss->cipher_state.nonce = 0;
}

static void ss_mix_key_and_hash(symmetric_state_t *ss,
                                uint8_t (*key)[HASHLEN]) {
  uint8_t temp_h[HASHLEN] = {0};

  hkdf3(ss->chaining_key, HASHLEN, (uint8_t *)key, HASHLEN, &ss->chaining_key,
        &temp_h, &ss->cipher_state.key);

  ss->cipher_state.has_key = true;
  ss->cipher_state.nonce = 0;
  ss_mix_hash(ss, temp_h, HASHLEN);
  memzero(temp_h, sizeof(temp_h));  // Remove temp keys from stack
}

static void ss_ts_split(symmetric_state_t *ss, transport_state_t *ts) {
  hkdf2(ss->chaining_key, HASHLEN, NULL, 0,
        &ts->send_cipher_state.key,    // <- Output 1
        &ts->receive_cipher_state.key  // <- Output 2
  );

  ts->send_cipher_state.has_key = true;
  ts->send_cipher_state.nonce = 0;
  ts->receive_cipher_state.has_key = true;
  ts->receive_cipher_state.nonce = 0;
  memcpy(ts->handshake_hash, ss->handshake_hash, HASHLEN);
}

/**
@brief generate new curve25519 keypair

@param private_key output buffer for generated private key
@param public_key output buffer for derived public key
*/
static void generate_keypair(uint8_t (*private_key)[DHLEN],
                             uint8_t (*public_key)[DHLEN]) {
  random_buffer(*private_key, DHLEN);
  curve25519_scalarmult_basepoint(*public_key, *private_key);
}

/**
 * @brief encrypt with associated data
 *
 * @param cs cipher state containing the key and nonce for encryption
 * @param ad pointer to the associated data
 * @param ad_len length of the associated data
 * @param dec_bytes pointer to the decrypted byte array input of size defined by
 * `len`
 * @param enc_bytes pointer to the encrypted byte array output of size defined
 * by `len + NOISE_TAG_SIZE_BYTES`
 * @param dec_bytes_len size of the decrypted byte array
 * @return ts_t;
 */
static ts_t encrypt_with_ad(cipher_state_t *cs, const uint8_t *ad,
                            size_t ad_len, const uint8_t *dec_bytes,
                            uint8_t *enc_bytes, size_t dec_bytes_len) {
  if (!cs->has_key || cs->nonce >= NONCE_LIMIT) {
    return TS_EINVAL;
  } else {
    // Encrypt with AEAD
    gcm_ctx ctx = {0};
    if (gcm_init_and_key(cs->key, HASHLEN, &ctx) != RETURN_GOOD) {
      memzero(&ctx, sizeof(ctx));
      return TS_EINVAL;
    }

    uint8_t nonce_bytes[NONCE_ARRAY_SIZE_BYTES] = {0};
    nonce_to_bytes(cs->nonce, &nonce_bytes);

    memcpy(enc_bytes, dec_bytes, dec_bytes_len);

    if (gcm_encrypt_message(nonce_bytes, NONCE_ARRAY_SIZE_BYTES, ad, ad_len,
                            enc_bytes, dec_bytes_len, enc_bytes + dec_bytes_len,
                            NOISE_TAG_SIZE_BYTES, &ctx) != RETURN_GOOD) {
      memzero(&ctx, sizeof(ctx));
      memzero(enc_bytes, dec_bytes_len + NOISE_TAG_SIZE_BYTES);
      memzero(nonce_bytes, sizeof(nonce_bytes));
      return TS_EINVAL;
    }

    memzero(&ctx, sizeof(ctx));
    memzero(nonce_bytes, sizeof(nonce_bytes));
    cs->nonce++;
  }

  return TS_OK;
}

/**
 * @brief decrypt with associated data
 *
 * @param cs cipher state containing the key and nonce for decryption
 * @param ad pointer to the associated data
 * @param ad_len length of the associated data
 * @param enc_bytes pointer to the encrypted byte array input of size defined by
 * `len`
 * @param dec_bytes pointer to the decrypted byte array output of size defined
 * by `len - NOISE_TAG_SIZE_BYTES`
 * @param enc_bytes_len size of the encrypted byte array
 * @return ts_t;
 */
static ts_t decrypt_with_ad(cipher_state_t *cs, const uint8_t *ad,
                            size_t ad_len, const uint8_t *enc_bytes,
                            uint8_t *dec_bytes, size_t enc_bytes_len) {
  if (!cs->has_key || cs->nonce >= NONCE_LIMIT) {
    return TS_EINVAL;

  } else {
    if (enc_bytes_len < NOISE_TAG_SIZE_BYTES) {
      // encrypted message is too short to contain the auth. tag
      return TS_EINVAL;
    }

    // Decrypt with AEAD
    gcm_ctx ctx = {0};
    if (gcm_init_and_key(cs->key, HASHLEN, &ctx) != RETURN_GOOD) {
      memzero(&ctx, sizeof(ctx));
      return TS_EINVAL;
    }

    uint8_t nonce_bytes[NONCE_ARRAY_SIZE_BYTES] = {0};
    nonce_to_bytes(cs->nonce, &nonce_bytes);

    // decrypted message is shorter by auth. tag
    size_t dec_bytes_len = enc_bytes_len - NOISE_TAG_SIZE_BYTES;
    memcpy(dec_bytes, enc_bytes, dec_bytes_len);

    if (gcm_decrypt_message(nonce_bytes, NONCE_ARRAY_SIZE_BYTES, ad, ad_len,
                            dec_bytes, dec_bytes_len, enc_bytes + dec_bytes_len,
                            NOISE_TAG_SIZE_BYTES, &ctx) != RETURN_GOOD) {
      memzero(&ctx, sizeof(ctx));
      memzero(dec_bytes, dec_bytes_len);
      memzero(nonce_bytes, sizeof(nonce_bytes));
      return TS_EINVAL;
    }

    memzero(&ctx, sizeof(ctx));
    memzero(nonce_bytes, sizeof(nonce_bytes));
    cs->nonce++;
  }

  return TS_OK;
}

/**
 * @brief encrypt and hash
 *
 * @param ss pointer to symmetric state structure,
 * @param dec_bytes pointer to decrypted byte array input of size defined by
 * `len` param
 * @param enc_bytes pointer to encrypted byte array output of size defined by
 * `len` param + NOISE_TAG_SIZE_BYTES
 * @param dec_bytes_len size of the decrypted byte array
 * @return ts_t;
 */
static ts_t ss_encrypt_and_hash(symmetric_state_t *ss, const uint8_t *dec_bytes,
                                uint8_t *enc_bytes, size_t dec_bytes_len) {
  ts_t status = encrypt_with_ad(&ss->cipher_state, ss->handshake_hash, HASHLEN,
                                dec_bytes, enc_bytes, dec_bytes_len);
  if (ts_error(status)) {
    return status;
  }

  ss_mix_hash(ss, enc_bytes, dec_bytes_len + NOISE_TAG_SIZE_BYTES);

  return TS_OK;
}

/**
 * @brief decrypt and hash
 *
 * @param ss pointer to symmetric state structure,
 * @param enc_bytes pointer to encrypted byte array input of size defined by
 * `enc_bytes_len`
 * @param dec_bytes pointer to decrypted byte array output of size defined by
 * `enc_bytes_len - NOISE_TAG_SIZE_BYTES`
 * @param enc_bytes_len size of the encrypted byte array
 * @return ts_t;
 */
static ts_t ss_decrypt_and_hash(symmetric_state_t *ss, const uint8_t *enc_bytes,
                                uint8_t *dec_bytes, size_t enc_bytes_len) {
  ts_t status = decrypt_with_ad(&ss->cipher_state, ss->handshake_hash, HASHLEN,
                                enc_bytes, dec_bytes, enc_bytes_len);

  // In the decryption case, the hash is mixed even if decryption fails, as
  // specified in the Noise Protocol Framework.
  ss_mix_hash(ss, enc_bytes, enc_bytes_len);

  return status;
}

static void noise_init_state(noise_state_t *state, const uint8_t psk[DHLEN],
                             const uint8_t static_private_key[DHLEN]) {
  static uint8_t XX_PROTOCOL_NAME[] = "Noise_XXpsk3_25519_AESGCM_SHA256";
  static uint8_t prologue[] = "";

  ss_init(&state->symmetric_state, XX_PROTOCOL_NAME,
          sizeof(XX_PROTOCOL_NAME) - 1);  // -1 substract the string terminator

  memcpy(state->static_private, static_private_key, DHLEN);
  curve25519_scalarmult_basepoint(state->static_public, state->static_private);

  ss_mix_hash(&state->symmetric_state, (uint8_t *)prologue,
              sizeof(prologue) - 1);

  memcpy(state->psk, psk, DHLEN);

  state->has_ephemeral_private = false;
  state->has_remote_ephemeral_public = false;
  state->has_remote_static_public = false;
  state->has_transport_state = false;
}

#ifdef USE_NOISE_RESPONDER

ts_t noise_responder_init(responder_xxpsk3_t *rspn, const uint8_t psk[DHLEN],
                          const uint8_t static_private_key[DHLEN]) {
  TSH_DECLARE;

  TSH_CHECK_ARG(rspn != NULL);
  TSH_CHECK(!rspn->initialized, TS_EINIT);
  TSH_CHECK_ARG(psk != NULL);
  TSH_CHECK_ARG(static_private_key != NULL);

  // Clear the responder structure
  memzero(rspn, sizeof(responder_xxpsk3_t));

  noise_init_state(&rspn->state, psk, static_private_key);

  rspn->handshake_stage = WAITING_FOR_REQUEST1;
  rspn->initialized = true;

  TSH_RETURN;

cleanup:
  noise_responder_deinit(rspn);
  TSH_RETURN;
}

void noise_responder_deinit(responder_xxpsk3_t *rspn) {
  // Clear the responder structure
  memzero(rspn, sizeof(responder_xxpsk3_t));
}

ts_t noise_responder_handle_request1(responder_xxpsk3_t *rspn,
                                     const uint8_t *msg, size_t msg_len) {
  TSH_DECLARE;

  noise_state_t *state = &rspn->state;

  TSH_CHECK(rspn->initialized, TS_ENOINIT);
  TSH_CHECK(rspn->handshake_stage == WAITING_FOR_REQUEST1, TS_ENOEN);
  TSH_CHECK(msg != NULL, TS_EINVAL);
  TSH_CHECK(msg_len == DHLEN, TS_EINVAL);

  memcpy(state->remote_ephemeral_public, msg, DHLEN);
  state->has_remote_ephemeral_public = true;
  ss_mix_hash(&state->symmetric_state, state->remote_ephemeral_public, DHLEN);

  // in case of empty payload, just mix handshake_hash = hash(handshake_hash)
  ss_mix_hash(&state->symmetric_state, NULL, 0);
  rspn->handshake_stage = READY_FOR_RESPONSE1;

  TSH_RETURN;

cleanup:
  noise_responder_deinit(rspn);
  TSH_RETURN;
}

ts_t noise_responder_create_response1(responder_xxpsk3_t *rspn,
                                      const uint8_t *payload,
                                      uint8_t payload_size, uint8_t *response,
                                      size_t max_response_size,
                                      size_t *response_size) {
  TSH_DECLARE;
  ts_t status;

  noise_state_t *state = &rspn->state;
  uint8_t input_key_material[DHLEN] = {0};

  TSH_CHECK(rspn->initialized, TS_ENOINIT);
  TSH_CHECK(response != NULL, TS_EINVAL);
  TSH_CHECK(response_size != NULL, TS_EINVAL);
  TSH_CHECK(rspn->handshake_stage == READY_FOR_RESPONSE1, TS_ENOEN);
  TSH_CHECK(state->has_remote_ephemeral_public, TS_ENOEN);

  // Check if response buffer is large enough to hold the response
  TSH_CHECK(max_response_size >=
                (2 * DHLEN + 2 * NOISE_TAG_SIZE_BYTES + payload_size),
            TS_ENOMEM);

  TSH_CHECK(payload_size <= NOISE_MAX_PAYLOAD_BYTES, TS_EINVAL);

  // Generate ephemeral keypair
  generate_keypair(&state->ephemeral_private, (uint8_t (*)[DHLEN])response);
  state->has_ephemeral_private = true;

  ss_mix_hash(&state->symmetric_state, response, DHLEN);

  dh(&input_key_material, &state->ephemeral_private,
     &state->remote_ephemeral_public);
  ss_mix_key(&state->symmetric_state, &input_key_material);

  // Encrypt static public key
  status = ss_encrypt_and_hash(&state->symmetric_state, state->static_public,
                               response + DHLEN, DHLEN);
  TSH_CHECK_OK(status);

  dh(&input_key_material, &state->static_private,
     &state->remote_ephemeral_public);
  ss_mix_key(&state->symmetric_state, &input_key_material);

  // Encrypt payload
  status = ss_encrypt_and_hash(&state->symmetric_state, payload,
                               response + (2 * DHLEN + NOISE_TAG_SIZE_BYTES),
                               payload_size);
  TSH_CHECK_OK(status);

  *response_size = 2 * DHLEN + 2 * NOISE_TAG_SIZE_BYTES + payload_size;

  /* Cleanup local buffers */
  memzero(input_key_material, sizeof(input_key_material));

  rspn->handshake_stage = WAITING_FOR_REQUEST2;

  TSH_RETURN;

cleanup:
  noise_responder_deinit(rspn);

  /* Cleanup buffers */
  memzero(input_key_material, sizeof(input_key_material));

  TSH_RETURN;
}

ts_t noise_responder_handle_request2(responder_xxpsk3_t *rspn,
                                     const uint8_t *msg, size_t msg_len) {
  TSH_DECLARE;
  ts_t status;

  noise_state_t *state = &rspn->state;
  uint8_t input_key_material[DHLEN] = {0};

  TSH_CHECK(rspn->initialized, TS_ENOINIT);
  TSH_CHECK(msg != NULL, TS_EINVAL);
  TSH_CHECK(rspn->handshake_stage == WAITING_FOR_REQUEST2, TS_ENOEN);
  TSH_CHECK(state->has_ephemeral_private, TS_ENOEN);
  TSH_CHECK(msg_len == (DHLEN + NOISE_TAG_SIZE_BYTES), TS_EINVAL);

  status = ss_decrypt_and_hash(&state->symmetric_state, msg,
                               state->remote_static_public,  // <- Decrypt here
                               DHLEN + NOISE_TAG_SIZE_BYTES);
  TSH_CHECK_OK(status);

  state->has_remote_static_public = true;

  dh(&input_key_material, &state->ephemeral_private,
     &state->remote_static_public);
  ss_mix_key(&state->symmetric_state, &input_key_material);

  ss_mix_key_and_hash(&state->symmetric_state, &state->psk);

  // in case of empty payload, just mix handshake_hash = hash(handshake_hash)
  ss_mix_hash(&state->symmetric_state, NULL, 0);

  ss_ts_split(&state->symmetric_state, &state->transport_state);

  /* Responder swaps the send and recieve key */
  cipher_state_t temp = state->transport_state.send_cipher_state;
  state->transport_state.send_cipher_state =
      state->transport_state.receive_cipher_state;
  state->transport_state.receive_cipher_state = temp;
  memzero(&temp, sizeof(temp));

  // Clean sensitive data from handler
  memzero(state, sizeof(noise_state_t) - sizeof(transport_state_t));

  state->has_transport_state = true;

  memzero(input_key_material, sizeof(input_key_material));

  rspn->handshake_stage = RSPN_HANDSHAKE_COMPLETE;

  TSH_RETURN;
cleanup:
  memzero(input_key_material, sizeof(input_key_material));
  noise_responder_deinit(rspn);
  TSH_RETURN;
}

ts_t noise_responder_create_response2(responder_xxpsk3_t *rspn,
                                      uint8_t *response,
                                      size_t max_response_size,
                                      size_t *response_size) {
  TSH_DECLARE;
  ts_t status;

  noise_state_t *state = &rspn->state;
  uint8_t empty_payload[1] = {
      0};  // No payload, but buffer is needed for encryption function

  TSH_CHECK(rspn->initialized, TS_ENOINIT);
  TSH_CHECK(rspn->handshake_stage == RSPN_HANDSHAKE_COMPLETE, TS_ENOEN);
  TSH_CHECK(state->has_transport_state, TS_ENOEN);
  TSH_CHECK(response != NULL, TS_EINVAL);
  TSH_CHECK(response_size != NULL, TS_EINVAL);
  TSH_CHECK(max_response_size >= NOISE_TAG_SIZE_BYTES, TS_ENOMEM);

  status = encrypt_with_ad(&state->transport_state.send_cipher_state,
                           empty_payload, 0, NULL, response, 0);

  *response_size = NOISE_TAG_SIZE_BYTES;

  TSH_CHECK_OK(status);

  TSH_RETURN;

cleanup:
  memzero(empty_payload, sizeof(empty_payload));
  noise_responder_deinit(rspn);
  TSH_RETURN;
}

#endif  // USE_NOISE_RESPONDER

#ifdef USE_NOISE_INITIATOR

ts_t noise_initiator_init(initiator_xxpsk3_t *intr, const uint8_t psk[DHLEN],
                          const uint8_t static_private_key[DHLEN]) {
  TSH_DECLARE;

  TSH_CHECK_ARG(intr != NULL);
  TSH_CHECK(!intr->initialized, TS_EINIT);
  TSH_CHECK_ARG(psk != NULL);
  TSH_CHECK_ARG(static_private_key != NULL);

  // Clear the initiator structure
  memzero(intr, sizeof(initiator_xxpsk3_t));

  noise_init_state(&intr->state, psk, static_private_key);

  intr->handshake_stage = READY_FOR_REQUEST1;
  intr->initialized = true;

  TSH_RETURN;

cleanup:
  noise_initiator_deinit(intr);
  TSH_RETURN;
}

void noise_initiator_deinit(initiator_xxpsk3_t *intr) {
  // Clear the initiator structure
  memzero(intr, sizeof(initiator_xxpsk3_t));
}

ts_t noise_initiator_create_request1(initiator_xxpsk3_t *intr, uint8_t *request,
                                     size_t max_request_size,
                                     size_t *request_size) {
  TSH_DECLARE;

  noise_state_t *state = &intr->state;

  TSH_CHECK(intr->initialized, TS_ENOINIT);
  TSH_CHECK(intr->handshake_stage == READY_FOR_REQUEST1, TS_ENOEN);
  TSH_CHECK(request != NULL, TS_EINVAL);
  TSH_CHECK(request_size != NULL, TS_EINVAL);
  TSH_CHECK(max_request_size >= DHLEN, TS_ENOMEM);

  // Generate ephemeral keypair
  generate_keypair(&state->ephemeral_private, (uint8_t (*)[DHLEN])request);
  state->has_ephemeral_private = true;
  ss_mix_hash(&state->symmetric_state, request, DHLEN);

  // in case of empty payload, just mix handshake_hash = hash(handshake_hash)
  ss_mix_hash(&state->symmetric_state, NULL, 0);

  *request_size = DHLEN;

  intr->handshake_stage = WAITING_FOR_RESPONSE1;

  TSH_RETURN;

cleanup:
  noise_initiator_deinit(intr);
  TSH_RETURN;
}

ts_t noise_initiator_handle_response1(initiator_xxpsk3_t *intr,
                                      const uint8_t *msg, size_t msg_len,
                                      uint8_t *payload, size_t max_payload_size,
                                      size_t *payload_size) {
  TSH_DECLARE;
  ts_t status;

  noise_state_t *state = &intr->state;
  uint8_t input_key_material[DHLEN] = {0};

  TSH_CHECK(intr->initialized, TS_ENOINIT);
  TSH_CHECK(intr->handshake_stage == WAITING_FOR_RESPONSE1, TS_ENOEN);
  TSH_CHECK(payload != NULL, TS_EINVAL);
  TSH_CHECK(payload_size != NULL, TS_EINVAL);
  TSH_CHECK(msg != NULL, TS_EINVAL);
  TSH_CHECK(msg_len >= (2 * DHLEN + 2 * NOISE_TAG_SIZE_BYTES), TS_EINVAL);
  TSH_CHECK(
      msg_len - (2 * DHLEN + 2 * NOISE_TAG_SIZE_BYTES) <= max_payload_size,
      TS_EINVAL);

  // TODO: Local buffers here could be replaces with the response buffer
  // directly, but for the better readability we keep like this for now.
  // Cleanup once tested.

  memcpy(state->remote_ephemeral_public, msg, DHLEN);
  state->has_remote_ephemeral_public = true;
  ss_mix_hash(&state->symmetric_state, state->remote_ephemeral_public, DHLEN);

  dh(&input_key_material, &state->ephemeral_private,
     &state->remote_ephemeral_public);
  ss_mix_key(&state->symmetric_state, &input_key_material);

  status = ss_decrypt_and_hash(&state->symmetric_state, msg + DHLEN,
                               state->remote_static_public,  // <- Decrypt here
                               DHLEN + NOISE_TAG_SIZE_BYTES);
  TSH_CHECK_OK(status);
  state->has_remote_static_public = true;

  dh(&input_key_material, &state->ephemeral_private,
     &state->remote_static_public);
  ss_mix_key(&state->symmetric_state, &input_key_material);

  // decrypt received payload
  status = ss_decrypt_and_hash(
      &state->symmetric_state, msg + (2 * DHLEN + NOISE_TAG_SIZE_BYTES),
      payload, msg_len - (2 * DHLEN + NOISE_TAG_SIZE_BYTES));
  TSH_CHECK_OK(status);

  *payload_size = msg_len - (2 * DHLEN + 2 * NOISE_TAG_SIZE_BYTES);
  memzero(input_key_material, sizeof(input_key_material));

  intr->handshake_stage = READY_FOR_REQUEST2;

  TSH_RETURN;

cleanup:
  memzero(input_key_material, sizeof(input_key_material));
  noise_initiator_deinit(intr);
  TSH_RETURN;
}

ts_t noise_initiator_create_request2(initiator_xxpsk3_t *intr, uint8_t *request,
                                     size_t max_request_size,
                                     size_t *request_size) {
  TSH_DECLARE;
  ts_t status;

  noise_state_t *state = &intr->state;
  uint8_t input_key_material[DHLEN] = {0};

  TSH_CHECK(intr->initialized, TS_ENOINIT);
  TSH_CHECK(intr->handshake_stage == READY_FOR_REQUEST2, TS_ENOEN);
  TSH_CHECK(request != NULL, TS_EINVAL);
  TSH_CHECK(request_size != NULL, TS_EINVAL);
  TSH_CHECK(max_request_size >= (DHLEN + NOISE_TAG_SIZE_BYTES), TS_ENOMEM);

  status = ss_encrypt_and_hash(&state->symmetric_state, state->static_public,
                               request, DHLEN);
  TSH_CHECK_OK(status);

  dh(&input_key_material, &state->static_private,
     &state->remote_ephemeral_public);
  ss_mix_key(&state->symmetric_state, &input_key_material);

  ss_mix_key_and_hash(&state->symmetric_state, &state->psk);

  // in case of empty payload, just mix handshake_hash = hash(handshake_hash)
  ss_mix_hash(&state->symmetric_state, NULL, 0);

  *request_size = DHLEN + NOISE_TAG_SIZE_BYTES;

  ss_ts_split(&state->symmetric_state, &state->transport_state);
  memzero(state, sizeof(noise_state_t) - sizeof(transport_state_t));
  state->has_transport_state = true;

  intr->handshake_stage = INTR_HANDSHAKE_COMPLETE;

  memzero(input_key_material, sizeof(input_key_material));

  TSH_RETURN;
cleanup:
  memzero(input_key_material, sizeof(input_key_material));
  noise_initiator_deinit(intr);
  TSH_RETURN;
}

ts_t noise_initiator_handle_response2(initiator_xxpsk3_t *intr,
                                      const uint8_t *msg, size_t msg_len) {
  TSH_DECLARE;
  ts_t status;

  noise_state_t *state = &intr->state;
  uint8_t empty_payload[1] = {
      0};  // No payload, but buffer is needed for decryption function

  TSH_CHECK(intr->initialized, TS_ENOINIT);
  TSH_CHECK(msg != NULL, TS_EINVAL);
  TSH_CHECK(intr->handshake_stage == INTR_HANDSHAKE_COMPLETE, TS_ENOEN);
  TSH_CHECK(state->has_transport_state, TS_ENOEN);
  TSH_CHECK(msg_len == NOISE_TAG_SIZE_BYTES, TS_EINVAL);

  status = decrypt_with_ad(&state->transport_state.receive_cipher_state, NULL,
                           0, msg, empty_payload, msg_len);
  TSH_CHECK_OK(status);
  memzero(empty_payload, sizeof(empty_payload));

  TSH_RETURN;

cleanup:
  memzero(empty_payload, sizeof(empty_payload));
  noise_initiator_deinit(intr);
  TSH_RETURN;
}

#endif  // USE_NOISE_INITIATOR
