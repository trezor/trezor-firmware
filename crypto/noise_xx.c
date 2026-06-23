/**
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

#include "noise_xx.h"
#include <string.h>
#include "noise_internal.h"

#include "ed25519-donna/ed25519.h"
#include "memzero.h"
#include "rand.h"

const uint8_t noise_xx_protocol_name[SHA256_DIGEST_LENGTH] = {
    'N', 'o', 'i', 's', 'e', '_', 'X',  'X',  '_',  '2', '5',
    '5', '1', '9', '_', 'A', 'E', 'S',  'G',  'C',  'M', '_',
    'S', 'H', 'A', '2', '5', '6', 0x00, 0x00, 0x00, 0x00};

const uint8_t nonce_0[NOISE_KEY_SIZE] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                         0x00, 0x00, 0x00, 0x00, 0x00, 0x00};
const uint8_t nonce_1[NOISE_KEY_SIZE] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                                         0x00, 0x00, 0x00, 0x00, 0x00, 0x01};

static void get_mask(curve25519_key mask,
                     const curve25519_key responder_static_public_key,
                     const curve25519_key responder_ephemeral_public_key) {
  uint8_t hash[SHA256_DIGEST_LENGTH];
  SHA256_CTX sha256_ctx = {0};
  sha256_Init(&sha256_ctx);
  sha256_Update(&sha256_ctx, responder_static_public_key,
                sizeof(curve25519_key));
  sha256_Update(&sha256_ctx, responder_ephemeral_public_key,
                sizeof(curve25519_key));
  sha256_Final(&sha256_ctx, hash);
  memcpy(mask, hash, sizeof(curve25519_key));
  _Static_assert(sizeof(curve25519_key) == SHA256_DIGEST_LENGTH,
                 "output_key must be truncated to SHA256_DIGEST_LENGTH");
}

bool noise_xx_create_initiation_request(
    noise_xx_handshake_context_t *hctx, const uint8_t *prologue,
    size_t prologue_len, uint8_t payload,
    noise_xx_initiation_request_t *request) {
  if (hctx->step != NOISE_XX_HANDSHAKE_INIT) {
    goto error;
  }

  // init
  memzero(hctx, sizeof(*hctx));
  random_buffer(hctx->ephemeral_private_key,
                sizeof(hctx->ephemeral_private_key));
  memcpy(hctx->chaining_key, noise_xx_protocol_name,
         sizeof(noise_xx_protocol_name));
  memcpy(hctx->handshake_hash, noise_xx_protocol_name,
         sizeof(noise_xx_protocol_name));
  noise_internal_mix_hash(hctx->handshake_hash, prologue, prologue_len);

  // -> e
  curve25519_scalarmult_basepoint(request->initiator_ephemeral_public_key,
                                  hctx->ephemeral_private_key);
  noise_internal_mix_hash(hctx->handshake_hash,
                          request->initiator_ephemeral_public_key,
                          sizeof(request->initiator_ephemeral_public_key));
  noise_internal_mix_hash(hctx->handshake_hash, &payload, sizeof(payload));

  // payload
  request->payload = payload;

  hctx->step = NOISE_XX_HANDSHAKE_I_SENT_INITIATION_REQUEST;
  return true;
error:
  hctx->step = NOISE_XX_HANDSHAKE_FAILED;
  return false;
}

bool noise_xx_handle_initiation_request(
    noise_xx_handshake_context_t *hctx, const uint8_t *prologue,
    size_t prologue_len, uint8_t *payload,
    const noise_xx_initiation_request_t *request) {
  if (hctx->step != NOISE_XX_HANDSHAKE_INIT) {
    goto error;
  }

  // init
  memzero(hctx, sizeof(*hctx));
  memcpy(hctx->chaining_key, noise_xx_protocol_name,
         sizeof(hctx->chaining_key));
  memcpy(hctx->handshake_hash, noise_xx_protocol_name,
         sizeof(hctx->handshake_hash));
  noise_internal_mix_hash(hctx->handshake_hash, prologue, prologue_len);

  // -> e
  memcpy(hctx->remote_ephemeral_public_key,
         request->initiator_ephemeral_public_key,
         sizeof(hctx->remote_ephemeral_public_key));
  noise_internal_mix_hash(hctx->handshake_hash,
                          hctx->remote_ephemeral_public_key,
                          sizeof(hctx->remote_ephemeral_public_key));

  // payload
  *payload = request->payload;
  noise_internal_mix_hash(hctx->handshake_hash, payload, sizeof(*payload));

  hctx->step = NOISE_XX_HANDSHAKE_R_RECEIVED_INITIATION_REQUEST;
  return true;
error:
  hctx->step = NOISE_XX_HANDSHAKE_FAILED;
  return false;
}

bool noise_xx_create_initiation_response(
    noise_xx_handshake_context_t *hctx,
    const curve25519_key responder_static_private_key,
    noise_xx_initiation_response_t *response) {
  if (hctx->step != NOISE_XX_HANDSHAKE_R_RECEIVED_INITIATION_REQUEST) {
    goto error;
  }

  // <- e
  random_buffer(hctx->ephemeral_private_key,
                sizeof(hctx->ephemeral_private_key));
  curve25519_scalarmult_basepoint(response->responder_ephemeral_public_key,
                                  hctx->ephemeral_private_key);
  noise_internal_mix_hash(hctx->handshake_hash,
                          response->responder_ephemeral_public_key,
                          sizeof(response->responder_ephemeral_public_key));

  // <- ee
  curve25519_key shared_secret = {0};
  curve25519_scalarmult(shared_secret, hctx->ephemeral_private_key,
                        hctx->remote_ephemeral_public_key);
  noise_internal_mix_key(hctx->chaining_key, shared_secret,
                         hctx->symmetric_key);
  memzero(shared_secret, sizeof(shared_secret));

  // masking
  curve25519_key responder_static_public_key = {0};
  curve25519_scalarmult_basepoint(responder_static_public_key,
                                  responder_static_private_key);
  curve25519_key mask = {0};
  get_mask(mask, responder_static_public_key,
           response->responder_ephemeral_public_key);

  curve25519_key responder_masked_static_public_key = {0};
  curve25519_scalarmult(responder_masked_static_public_key, mask,
                        responder_static_public_key);

  // <- s
  if (!noise_internal_encrypt(
          hctx->symmetric_key, nonce_0, hctx->handshake_hash,
          sizeof(hctx->handshake_hash), responder_masked_static_public_key,
          sizeof(responder_masked_static_public_key),
          response->encrypted_responder_static_public_key)) {
    memzero(mask, sizeof(*mask));
    goto error;
  }
  noise_internal_mix_hash(
      hctx->handshake_hash, response->encrypted_responder_static_public_key,
      sizeof(response->encrypted_responder_static_public_key));

  // <- es
  curve25519_key tmp = {0};
  curve25519_scalarmult(tmp, responder_static_private_key,
                        hctx->remote_ephemeral_public_key);
  curve25519_scalarmult(shared_secret, mask, tmp);
  memzero(mask, sizeof(*mask));
  memzero(tmp, sizeof(*tmp));
  noise_internal_mix_key(hctx->chaining_key, shared_secret,
                         hctx->symmetric_key);
  memzero(shared_secret, sizeof(*shared_secret));

  // payload (empty)
  if (!noise_internal_encrypt(
          hctx->symmetric_key, nonce_0, hctx->handshake_hash,
          sizeof(hctx->handshake_hash), NULL, 0, response->tag)) {
    goto error;
  }
  noise_internal_mix_hash(hctx->handshake_hash, response->tag,
                          sizeof(response->tag));

  hctx->step = NOISE_XX_HANDSHAKE_R_SENT_INITIATION_RESPONSE;
  return true;
error:
  memzero(hctx, sizeof(*hctx));
  hctx->step = NOISE_XX_HANDSHAKE_FAILED;
  return false;
}

bool noise_xx_handle_initiation_response(
    noise_xx_handshake_context_t *hctx,
    const noise_xx_initiation_response_t *response) {
  if (hctx->step != NOISE_XX_HANDSHAKE_I_SENT_INITIATION_REQUEST) {
    goto error;
  }

  // <- e
  memcpy(hctx->remote_ephemeral_public_key,
         response->responder_ephemeral_public_key,
         sizeof(hctx->remote_ephemeral_public_key));
  noise_internal_mix_hash(hctx->handshake_hash,
                          hctx->remote_ephemeral_public_key,
                          sizeof(hctx->remote_ephemeral_public_key));

  // <- ee
  curve25519_key shared_secret = {0};
  curve25519_scalarmult(shared_secret, hctx->ephemeral_private_key,
                        hctx->remote_ephemeral_public_key);
  noise_internal_mix_key(hctx->chaining_key, shared_secret,
                         hctx->symmetric_key);
  memzero(shared_secret, sizeof(shared_secret));

  // <- s
  if (!noise_internal_decrypt(
          hctx->symmetric_key, nonce_0, hctx->handshake_hash,
          sizeof(hctx->handshake_hash),
          response->encrypted_responder_static_public_key,
          sizeof(response->encrypted_responder_static_public_key),
          hctx->remote_static_public_key)) {
    goto error;
  }
  noise_internal_mix_hash(
      hctx->handshake_hash, response->encrypted_responder_static_public_key,
      sizeof(response->encrypted_responder_static_public_key));

  // <- es
  curve25519_scalarmult(shared_secret, hctx->ephemeral_private_key,
                        hctx->remote_static_public_key);
  memzero(hctx->ephemeral_private_key, sizeof(hctx->ephemeral_private_key));
  noise_internal_mix_key(hctx->chaining_key, shared_secret,
                         hctx->symmetric_key);
  memzero(shared_secret, sizeof(*shared_secret));

  // payload (empty)
  if (!noise_internal_decrypt(
          hctx->symmetric_key, nonce_0, hctx->handshake_hash,
          sizeof(hctx->handshake_hash), response->tag, NOISE_TAG_SIZE, NULL)) {
    goto error;
  }
  noise_internal_mix_hash(hctx->handshake_hash, response->tag,
                          sizeof(response->tag));

  hctx->step = NOISE_XX_HANDSHAKE_I_RECEIVED_INITIATION_RESPONSE;
  return true;
error:
  memzero(hctx, sizeof(*hctx));
  hctx->step = NOISE_XX_HANDSHAKE_FAILED;
  return false;
}

bool noise_xx_create_completion_request(
    noise_xx_handshake_context_t *hctx,
    const curve25519_key initiator_static_private_key, const uint8_t *payload,
    size_t payload_len, noise_context_t *cctx,
    noise_xx_completion_request_t *request) {
  if (hctx->step != NOISE_XX_HANDSHAKE_I_RECEIVED_INITIATION_RESPONSE) {
    goto error;
  }

  // -> s
  curve25519_key initiator_static_public_key = {0};
  curve25519_scalarmult_basepoint(initiator_static_public_key,
                                  initiator_static_private_key);

  if (!noise_internal_encrypt(
          hctx->symmetric_key, nonce_1, hctx->handshake_hash,
          sizeof(hctx->handshake_hash), initiator_static_public_key,
          sizeof(initiator_static_public_key),
          request->encrypted_initiator_static_public_key)) {
    goto error;
  }
  noise_internal_mix_hash(
      hctx->handshake_hash, request->encrypted_initiator_static_public_key,
      sizeof(request->encrypted_initiator_static_public_key));

  // -> se
  curve25519_key shared_secret = {0};
  curve25519_scalarmult(shared_secret, initiator_static_private_key,
                        hctx->remote_ephemeral_public_key);
  noise_internal_mix_key(hctx->chaining_key, shared_secret,
                         hctx->symmetric_key);
  memzero(shared_secret, sizeof(*shared_secret));

  // payload
  if (payload_len > NOISE_XX_MAX_PAYLOAD_LEN) {
    goto error;
  }
  if (!noise_internal_encrypt(hctx->symmetric_key, nonce_0,
                              hctx->handshake_hash,
                              sizeof(hctx->handshake_hash), payload,
                              payload_len, request->encrypted_payload)) {
    goto error;
  }
  memzero(hctx->symmetric_key, sizeof(hctx->symmetric_key));
  request->encrypted_payload_len = payload_len + NOISE_TAG_SIZE;
  noise_internal_mix_hash(hctx->handshake_hash, request->encrypted_payload,
                          request->encrypted_payload_len);

  // split
  memzero(cctx, sizeof(cctx));
  noise_internal_split(hctx->chaining_key, cctx->encryption_key,
                       cctx->decryption_key);
  cctx->initialized = true;

  memzero(hctx->chaining_key, sizeof(hctx->chaining_key));
  memzero(hctx->remote_ephemeral_public_key,
          sizeof(hctx->remote_ephemeral_public_key));
  hctx->step = NOISE_XX_HANDSHAKE_FINISHED;
  return true;
error:
  memzero(hctx, sizeof(*hctx));
  hctx->step = NOISE_XX_HANDSHAKE_FAILED;
  return false;
}

bool noise_xx_handle_completion_request(
    noise_xx_handshake_context_t *hctx,
    uint8_t payload[NOISE_XX_MAX_PAYLOAD_LEN], size_t *payload_len,
    noise_context_t *cctx, const noise_xx_completion_request_t *request) {
  if (hctx->step != NOISE_XX_HANDSHAKE_R_SENT_INITIATION_RESPONSE) {
    goto error;
  }

  // -> s
  if (!noise_internal_decrypt(
          hctx->symmetric_key, nonce_1, hctx->handshake_hash,
          sizeof(hctx->handshake_hash),
          request->encrypted_initiator_static_public_key,
          sizeof(request->encrypted_initiator_static_public_key),
          hctx->remote_static_public_key)) {
    goto error;
  }
  noise_internal_mix_hash(
      hctx->handshake_hash, request->encrypted_initiator_static_public_key,
      sizeof(request->encrypted_initiator_static_public_key));

  // -> se
  curve25519_key shared_secret = {0};
  curve25519_scalarmult(shared_secret, hctx->ephemeral_private_key,
                        hctx->remote_static_public_key);
  memzero(hctx->ephemeral_private_key, sizeof(hctx->ephemeral_private_key));
  noise_internal_mix_key(hctx->chaining_key, shared_secret,
                         hctx->symmetric_key);

  // payload
  if (request->encrypted_payload_len < NOISE_TAG_SIZE ||
      request->encrypted_payload_len >
          NOISE_XX_MAX_PAYLOAD_LEN + NOISE_TAG_SIZE) {
    goto error;
  }
  if (!noise_internal_decrypt(
          hctx->symmetric_key, nonce_0, hctx->handshake_hash,
          sizeof(hctx->handshake_hash), request->encrypted_payload,
          request->encrypted_payload_len, payload)) {
    goto error;
  }
  memzero(hctx->symmetric_key, sizeof(hctx->symmetric_key));
  *payload_len = request->encrypted_payload_len - NOISE_TAG_SIZE;
  noise_internal_mix_hash(hctx->handshake_hash, request->encrypted_payload,
                          request->encrypted_payload_len);

  // split
  memzero(cctx, sizeof(cctx));
  noise_internal_split(hctx->chaining_key, cctx->decryption_key,
                       cctx->encryption_key);
  cctx->initialized = true;

  memzero(hctx->chaining_key, sizeof(hctx->chaining_key));
  memzero(hctx->remote_ephemeral_public_key,
          sizeof(hctx->remote_ephemeral_public_key));
  hctx->step = NOISE_XX_HANDSHAKE_FINISHED;
  return true;
error:
  memzero(hctx, sizeof(*hctx));
  hctx->step = NOISE_XX_HANDSHAKE_FAILED;
  return false;
}
