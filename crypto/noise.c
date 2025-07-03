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

#include "noise.h"
#include <string.h>

#include "aes/aesgcm.h"
#include "ed25519-donna/ed25519.h"
#include "hmac.h"
#include "memzero.h"
#include "rand.h"
#include "sha2.h"

static uint8_t protocol_name[SHA256_DIGEST_LENGTH] = {
    'N', 'o', 'i', 's', 'e', '_', 'K', 'K',  '1',  '_', '2',
    '5', '5', '1', '9', '_', 'A', 'E', 'S',  'G',  'C', 'M',
    '_', 'S', 'H', 'A', '2', '5', '6', 0x00, 0x00, 0x00};

static bool encrypt(const uint8_t key[NOISE_KEY_SIZE],
                    const uint8_t nonce[NOISE_NONCE_SIZE],
                    const uint8_t *associated_data,
                    size_t associated_data_length, const uint8_t *plaintext,
                    size_t plaintext_length, uint8_t *ciphertext) {
  // ciphertext = AES-GCM-Encrypt(key, nonce, associated_data, plaintext)
  gcm_ctx ctx = {0};
  if (gcm_init_and_key(key, NOISE_KEY_SIZE, &ctx) != RETURN_GOOD) {
    return false;
  }

  memcpy(ciphertext, plaintext, plaintext_length);

  if (gcm_encrypt_message(nonce, NOISE_NONCE_SIZE, associated_data,
                          associated_data_length, ciphertext, plaintext_length,
                          ciphertext + plaintext_length, NOISE_TAG_SIZE,
                          &ctx) != RETURN_GOOD) {
    memzero(&ctx, sizeof(ctx));
    memzero(ciphertext, plaintext_length);
    return false;
  }
  memzero(&ctx, sizeof(ctx));

  return true;
}

static bool decrypt(const uint8_t key[NOISE_KEY_SIZE],
                    const uint8_t nonce[NOISE_NONCE_SIZE],
                    const uint8_t *associated_data,
                    size_t associated_data_length, const uint8_t *ciphertext,
                    size_t ciphertext_length, uint8_t *plaintext) {
  // plaintext = AES-GCM-Decrypt(key, nonce, associated_data, ciphertext)
  if (ciphertext_length < NOISE_TAG_SIZE) {
    return false;
  }
  const size_t plaintext_length = ciphertext_length - NOISE_TAG_SIZE;

  gcm_ctx ctx = {0};
  if (gcm_init_and_key(key, NOISE_KEY_SIZE, &ctx) != RETURN_GOOD) {
    return false;
  }

  memcpy(plaintext, ciphertext, plaintext_length);

  if (gcm_decrypt_message(nonce, NOISE_NONCE_SIZE, associated_data,
                          associated_data_length, plaintext, plaintext_length,
                          ciphertext + plaintext_length, NOISE_TAG_SIZE,
                          &ctx) != RETURN_GOOD) {
    memzero(&ctx, sizeof(ctx));
    memzero(plaintext, plaintext_length);
    return false;
  }
  memzero(&ctx, sizeof(ctx));

  return true;
}

static void mix_hash(uint8_t hash[SHA256_DIGEST_LENGTH], const uint8_t *data,
                     size_t data_length) {
  // hash = SHA256(hash || data)
  SHA256_CTX sha256_ctx;
  sha256_Init(&sha256_ctx);
  sha256_Update(&sha256_ctx, hash, SHA256_DIGEST_LENGTH);
  sha256_Update(&sha256_ctx, data, data_length);
  sha256_Final(&sha256_ctx, hash);
}

static void hkdf(const uint8_t *salt, size_t salt_length, const uint8_t *key,
                 size_t key_length, uint8_t output1[SHA256_DIGEST_LENGTH],
                 uint8_t output2[SHA256_DIGEST_LENGTH]) {
  // output1 || output2 = HKDF(salt, key, output_length=2*SHA256_DIGEST_LENGTH)
  uint8_t prk[SHA256_DIGEST_LENGTH] = {0};
  hmac_sha256(salt, salt_length, key, key_length, prk);

  uint8_t message[SHA256_DIGEST_LENGTH + 1] = {0};
  message[0] = 1;
  hmac_sha256(prk, sizeof(prk), message, 1, output1);

  if (output2) {
    memcpy(message, output1, SHA256_DIGEST_LENGTH);
    message[SHA256_DIGEST_LENGTH] = 2;
    hmac_sha256(prk, sizeof(prk), message, SHA256_DIGEST_LENGTH + 1, output2);
  }

  memzero(message, sizeof(message));
  memzero(prk, sizeof(prk));
}

static void mix_key(uint8_t chaining_key[SHA256_DIGEST_LENGTH],
                    curve25519_key input_key,
                    uint8_t output_key[NOISE_KEY_SIZE]) {
  // chaining_key || output_key =
  //   HKDF(salt=chaining_key, key=input_key, output_length=2*NOISE_KEY_SIZE)
  hkdf(chaining_key, SHA256_DIGEST_LENGTH, input_key, sizeof(curve25519_key),
       chaining_key, output_key);
  _Static_assert(NOISE_KEY_SIZE == SHA256_DIGEST_LENGTH,
                 "output_key must be truncated to NOISE_KEY_SIZE");
}

void split(uint8_t chaining_key[SHA256_DIGEST_LENGTH],
           uint8_t output1[NOISE_KEY_SIZE], uint8_t output2[NOISE_KEY_SIZE]) {
  // output1 || output2 =
  //   HKDF(salt=chaining_key, key=b"", output_length=2*NOISE_KEY_SIZE)
  hkdf(chaining_key, SHA256_DIGEST_LENGTH, NULL, 0, output1, output2);
  _Static_assert(NOISE_KEY_SIZE == SHA256_DIGEST_LENGTH,
                 "output1 and output2 must be truncated to NOISE_KEY_SIZE");
}

static bool increase_nonce(uint8_t nonce[NOISE_NONCE_SIZE]) {
  // The first 4 bytes of the nonce are zeros
  // The last 8 bytes of the nonce are a big-endian encoded counter
  for (int i = NOISE_NONCE_SIZE - 1; i >= 4; i--) {
    nonce[i]++;
    if (nonce[i] != 0) {
      return true;
    }
  }

  // Nonce overflow
  return false;
}

bool noise_create_handshake_request(noise_context_t *ctx,
                                    noise_request_t *request) {
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
                                    const noise_request_t *request,
                                    noise_response_t *response) {
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
  mix_hash(handshake_hash, NULL, 0);
  mix_hash(handshake_hash, initiator_public_key, sizeof(curve25519_key));
  mix_hash(handshake_hash, responder_public_key, sizeof(curve25519_key));
  mix_hash(handshake_hash, request->initiator_ephemeral_public_key,
           sizeof(curve25519_key));
  mix_hash(handshake_hash, NULL, 0);  // Empty message
  mix_hash(handshake_hash, responder_ephemeral_public_key,
           sizeof(curve25519_key));

  curve25519_key shared_secret = {0};
  uint8_t chaining_key[SHA256_DIGEST_LENGTH] = {0};
  uint8_t kauth[NOISE_KEY_SIZE] = {0};
  memcpy(chaining_key, protocol_name, sizeof(protocol_name));
  curve25519_scalarmult(shared_secret, responder_ephemeral_private_key,
                        request->initiator_ephemeral_public_key);
  mix_key(chaining_key, shared_secret, NULL);
  curve25519_scalarmult(shared_secret, responder_ephemeral_private_key,
                        initiator_public_key);
  memzero(responder_ephemeral_private_key,
          sizeof(responder_ephemeral_private_key));
  mix_key(chaining_key, shared_secret, NULL);
  curve25519_scalarmult(shared_secret, responder_private_key,
                        request->initiator_ephemeral_public_key);
  mix_key(chaining_key, shared_secret, kauth);
  memzero(shared_secret, sizeof(shared_secret));
  split(chaining_key, ctx->decryption_key, ctx->encryption_key);
  memzero(chaining_key, sizeof(chaining_key));

  memcpy(response, responder_ephemeral_public_key, sizeof(curve25519_key));

  uint8_t zero_nonce[NOISE_NONCE_SIZE] = {0};
  encrypt(kauth, zero_nonce, handshake_hash, sizeof(handshake_hash), NULL, 0,
          response->tag);
  memzero(kauth, sizeof(kauth));

  // This is unnecessary, as the handshake hash is no longer used.
  // mix_hash(handshake_hash, response->tag, sizeof(response->tag));

  memset(ctx->encryption_nonce, 0, NOISE_NONCE_SIZE);
  memset(ctx->decryption_nonce, 0, NOISE_NONCE_SIZE);

  ctx->initialized = true;

  return true;
}

bool noise_handle_handshake_response(noise_context_t *ctx,
                                     const curve25519_key initiator_private_key,
                                     const curve25519_key responder_public_key,
                                     const noise_response_t *response) {
  curve25519_key initiator_public_key = {0};
  curve25519_scalarmult_basepoint(initiator_public_key, initiator_private_key);

  curve25519_key initiator_ephemeral_public_key = {0};
  curve25519_scalarmult_basepoint(initiator_ephemeral_public_key,
                                  ctx->initiator_ephemeral_private_key);

  uint8_t handshake_hash[SHA256_DIGEST_LENGTH] = {0};
  memcpy(handshake_hash, protocol_name, sizeof(protocol_name));
  mix_hash(handshake_hash, NULL, 0);
  mix_hash(handshake_hash, initiator_public_key, sizeof(curve25519_key));
  mix_hash(handshake_hash, responder_public_key, sizeof(curve25519_key));
  mix_hash(handshake_hash, initiator_ephemeral_public_key,
           sizeof(curve25519_key));
  mix_hash(handshake_hash, NULL, 0);  // Empty message
  mix_hash(handshake_hash, response->responder_ephemeral_public_key,
           sizeof(curve25519_key));

  curve25519_key shared_secret = {0};
  uint8_t chaining_key[SHA256_DIGEST_LENGTH] = {0};
  uint8_t kauth[NOISE_KEY_SIZE] = {0};
  memcpy(chaining_key, protocol_name, sizeof(protocol_name));
  curve25519_scalarmult(shared_secret, ctx->initiator_ephemeral_private_key,
                        response->responder_ephemeral_public_key);
  mix_key(chaining_key, shared_secret, NULL);
  curve25519_scalarmult(shared_secret, initiator_private_key,
                        response->responder_ephemeral_public_key);
  mix_key(chaining_key, shared_secret, NULL);
  curve25519_scalarmult(shared_secret, ctx->initiator_ephemeral_private_key,
                        responder_public_key);
  memzero(ctx->initiator_ephemeral_private_key,
          sizeof(ctx->initiator_ephemeral_private_key));
  mix_key(chaining_key, shared_secret, kauth);
  memzero(shared_secret, sizeof(shared_secret));
  split(chaining_key, ctx->encryption_key, ctx->decryption_key);
  memzero(chaining_key, sizeof(chaining_key));

  uint8_t zero_nonce[NOISE_NONCE_SIZE] = {0};
  if (!decrypt(kauth, zero_nonce, handshake_hash, sizeof(handshake_hash),
               response->tag, NOISE_TAG_SIZE, NULL)) {
    // Wrong tag
    memzero(kauth, sizeof(kauth));
    return false;
  }
  memzero(kauth, sizeof(kauth));

  // This is unnecessary, as the handshake hash is no longer used.
  // mix_hash(handshake_hash, response->tag, sizeof(response->tag));

  memset(ctx->encryption_nonce, 0, NOISE_NONCE_SIZE);
  memset(ctx->decryption_nonce, 0, NOISE_NONCE_SIZE);

  ctx->initialized = true;

  return true;
}

bool noise_send_message(noise_context_t *ctx, const uint8_t *associated_data,
                        size_t associated_data_length, const uint8_t *plaintext,
                        size_t plaintext_length, uint8_t *ciphertext) {
  if (!ctx->initialized) {
    return false;
  }
  if (!encrypt(ctx->encryption_key, ctx->encryption_nonce, associated_data,
               associated_data_length, plaintext, plaintext_length,
               ciphertext)) {
    return false;
  }
  if (!increase_nonce(ctx->encryption_nonce)) {
    // Nonce overflow
    memzero(ctx, sizeof(*ctx));
    ctx->initialized = false;
    return false;
  }

  return true;
}

bool noise_receive_message(noise_context_t *ctx, const uint8_t *associated_data,
                           size_t associated_data_length,
                           const uint8_t *ciphertext, size_t ciphertext_length,
                           uint8_t *plaintext) {
  if (!ctx->initialized) {
    return false;
  }
  if (!decrypt(ctx->decryption_key, ctx->decryption_nonce, associated_data,
               associated_data_length, ciphertext, ciphertext_length,
               plaintext)) {
    // Wrong tag
    return false;
  }
  if (!increase_nonce(ctx->decryption_nonce)) {
    // Nonce overflow
    memzero(ctx, sizeof(*ctx));
    ctx->initialized = false;
    return false;
  }
  return true;
}
