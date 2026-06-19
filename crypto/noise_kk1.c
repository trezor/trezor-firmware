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

#include "noise_kk1.h"
#include <string.h>
#include "noise_internal.h"

#include "ed25519-donna/ed25519.h"
#include "memzero.h"
#include "rand.h"
#include "sha2.h"

static uint8_t protocol_name[SHA256_DIGEST_LENGTH] = {
    'N', 'o', 'i', 's', 'e', '_', 'K', 'K',  '1',  '_', '2',
    '5', '5', '1', '9', '_', 'A', 'E', 'S',  'G',  'C', 'M',
    '_', 'S', 'H', 'A', '2', '5', '6', 0x00, 0x00, 0x00};

bool noise_create_handshake_request(noise_context_t *ctx,
                                    noise_kk1_request_t *request) {
  memzero(ctx, sizeof(*ctx));
  ctx->initialized = false;

  random_buffer(ctx->initiator_ephemeral_private_key,
                sizeof(ctx->initiator_ephemeral_private_key));
  curve25519_scalarmult_basepoint(request->initiator_ephemeral_public_key,
                                  ctx->initiator_ephemeral_private_key);
  return true;
}

bool noise_handle_handshake_request(noise_context_t *ctx,
                                    const curve25519_key initiator_public_key,
                                    const curve25519_key responder_private_key,
                                    const noise_kk1_request_t *request,
                                    noise_kk1_response_t *response) {
  memzero(ctx, sizeof(*ctx));

  curve25519_key responder_public_key = {0};
  curve25519_scalarmult_basepoint(responder_public_key, responder_private_key);

  curve25519_key responder_ephemeral_private_key = {0};
  random_buffer(responder_ephemeral_private_key,
                sizeof(responder_ephemeral_private_key));
  curve25519_key responder_ephemeral_public_key = {0};
  curve25519_scalarmult_basepoint(responder_ephemeral_public_key,
                                  responder_ephemeral_private_key);

  uint8_t handshake_hash[SHA256_DIGEST_LENGTH] = {0};
  memcpy(handshake_hash, protocol_name, sizeof(protocol_name));
  noise_internal_mix_hash(handshake_hash, NULL, 0);
  noise_internal_mix_hash(handshake_hash, initiator_public_key,
                          sizeof(curve25519_key));
  noise_internal_mix_hash(handshake_hash, responder_public_key,
                          sizeof(curve25519_key));
  noise_internal_mix_hash(handshake_hash,
                          request->initiator_ephemeral_public_key,
                          sizeof(curve25519_key));
  noise_internal_mix_hash(handshake_hash, NULL, 0);  // Empty message
  noise_internal_mix_hash(handshake_hash, responder_ephemeral_public_key,
                          sizeof(curve25519_key));

  curve25519_key shared_secret = {0};
  uint8_t chaining_key[SHA256_DIGEST_LENGTH] = {0};
  uint8_t kauth[NOISE_KEY_SIZE] = {0};
  memcpy(chaining_key, protocol_name, sizeof(protocol_name));
  curve25519_scalarmult(shared_secret, responder_ephemeral_private_key,
                        request->initiator_ephemeral_public_key);
  noise_internal_mix_key(chaining_key, shared_secret, NULL);
  curve25519_scalarmult(shared_secret, responder_ephemeral_private_key,
                        initiator_public_key);
  memzero(responder_ephemeral_private_key,
          sizeof(responder_ephemeral_private_key));
  noise_internal_mix_key(chaining_key, shared_secret, NULL);
  curve25519_scalarmult(shared_secret, responder_private_key,
                        request->initiator_ephemeral_public_key);
  noise_internal_mix_key(chaining_key, shared_secret, kauth);
  memzero(shared_secret, sizeof(shared_secret));
  noise_internal_split(chaining_key, ctx->decryption_key, ctx->encryption_key);
  memzero(chaining_key, sizeof(chaining_key));

  memcpy(response, responder_ephemeral_public_key, sizeof(curve25519_key));

  uint8_t zero_nonce[NOISE_NONCE_SIZE] = {0};
  noise_internal_encrypt(kauth, zero_nonce, handshake_hash,
                         sizeof(handshake_hash), NULL, 0, response->tag);
  memzero(kauth, sizeof(kauth));

  // This is unnecessary, as the handshake hash is no longer used.
  // noise_internal_mix_hash(handshake_hash, response->tag,
  // sizeof(response->tag));

  memset(ctx->encryption_nonce, 0, NOISE_NONCE_SIZE);
  memset(ctx->decryption_nonce, 0, NOISE_NONCE_SIZE);

  ctx->initialized = true;

  return true;
}

bool noise_handle_handshake_response(noise_context_t *ctx,
                                     const curve25519_key initiator_private_key,
                                     const curve25519_key responder_public_key,
                                     const noise_kk1_response_t *response) {
  curve25519_key initiator_public_key = {0};
  curve25519_scalarmult_basepoint(initiator_public_key, initiator_private_key);

  curve25519_key initiator_ephemeral_public_key = {0};
  curve25519_scalarmult_basepoint(initiator_ephemeral_public_key,
                                  ctx->initiator_ephemeral_private_key);

  uint8_t handshake_hash[SHA256_DIGEST_LENGTH] = {0};
  memcpy(handshake_hash, protocol_name, sizeof(protocol_name));
  noise_internal_mix_hash(handshake_hash, NULL, 0);
  noise_internal_mix_hash(handshake_hash, initiator_public_key,
                          sizeof(curve25519_key));
  noise_internal_mix_hash(handshake_hash, responder_public_key,
                          sizeof(curve25519_key));
  noise_internal_mix_hash(handshake_hash, initiator_ephemeral_public_key,
                          sizeof(curve25519_key));
  noise_internal_mix_hash(handshake_hash, NULL, 0);  // Empty message
  noise_internal_mix_hash(handshake_hash,
                          response->responder_ephemeral_public_key,
                          sizeof(curve25519_key));

  curve25519_key shared_secret = {0};
  uint8_t chaining_key[SHA256_DIGEST_LENGTH] = {0};
  uint8_t kauth[NOISE_KEY_SIZE] = {0};
  memcpy(chaining_key, protocol_name, sizeof(protocol_name));
  curve25519_scalarmult(shared_secret, ctx->initiator_ephemeral_private_key,
                        response->responder_ephemeral_public_key);
  noise_internal_mix_key(chaining_key, shared_secret, NULL);
  curve25519_scalarmult(shared_secret, initiator_private_key,
                        response->responder_ephemeral_public_key);
  noise_internal_mix_key(chaining_key, shared_secret, NULL);
  curve25519_scalarmult(shared_secret, ctx->initiator_ephemeral_private_key,
                        responder_public_key);
  memzero(ctx->initiator_ephemeral_private_key,
          sizeof(ctx->initiator_ephemeral_private_key));
  noise_internal_mix_key(chaining_key, shared_secret, kauth);
  memzero(shared_secret, sizeof(shared_secret));
  noise_internal_split(chaining_key, ctx->encryption_key, ctx->decryption_key);
  memzero(chaining_key, sizeof(chaining_key));

  uint8_t zero_nonce[NOISE_NONCE_SIZE] = {0};
  if (!noise_internal_decrypt(kauth, zero_nonce, handshake_hash,
                              sizeof(handshake_hash), response->tag,
                              NOISE_TAG_SIZE, NULL)) {
    // Wrong tag
    memzero(kauth, sizeof(kauth));
    return false;
  }
  memzero(kauth, sizeof(kauth));

  // This is unnecessary, as the handshake hash is no longer used.
  // noise_internal_mix_hash(handshake_hash, response->tag,
  // sizeof(response->tag));

  memset(ctx->encryption_nonce, 0, NOISE_NONCE_SIZE);
  memset(ctx->decryption_nonce, 0, NOISE_NONCE_SIZE);

  ctx->initialized = true;

  return true;
}

bool noise_handle_handshake_response_multiple_keys(
    noise_context_t *ctx, const curve25519_key initiator_private_key,
    const curve25519_key *responder_public_keys,
    size_t responder_public_keys_count, const noise_kk1_response_t *response) {
  curve25519_key ephemeral_key_backup = {0};
  memcpy(ephemeral_key_backup, ctx->initiator_ephemeral_private_key,
         sizeof(ephemeral_key_backup));
  for (size_t i = 0; i < responder_public_keys_count; i++) {
    memcpy(ctx->initiator_ephemeral_private_key, ephemeral_key_backup,
           sizeof(ephemeral_key_backup));
    if (noise_handle_handshake_response(ctx, initiator_private_key,
                                        responder_public_keys[i], response)) {
      memzero(ephemeral_key_backup, sizeof(ephemeral_key_backup));
      return true;
    }
  }
  return false;
}
