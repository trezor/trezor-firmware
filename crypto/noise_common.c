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

#include "noise_common.h"
#include <string.h>
#include "noise_internal.h"

#include "aes/aesgcm.h"
#include "ed25519-donna/ed25519.h"
#include "hmac.h"
#include "memzero.h"
#include "sha2.h"

bool noise_internal_encrypt_inplace(const uint8_t key[NOISE_KEY_SIZE],
                                    const uint8_t nonce[NOISE_NONCE_SIZE],
                                    const uint8_t *associated_data,
                                    size_t associated_data_length,
                                    uint8_t *in_out, size_t plaintext_length) {
  gcm_ctx ctx = {0};
  if (gcm_init_and_key(key, NOISE_KEY_SIZE, &ctx) != RETURN_GOOD) {
    return false;
  }

  if (gcm_encrypt_message(nonce, NOISE_NONCE_SIZE, associated_data,
                          associated_data_length, in_out, plaintext_length,
                          in_out + plaintext_length, NOISE_TAG_SIZE,
                          &ctx) != RETURN_GOOD) {
    memzero(&ctx, sizeof(ctx));
    return false;
  }
  memzero(&ctx, sizeof(ctx));

  return true;
}

bool noise_internal_encrypt(const uint8_t key[NOISE_KEY_SIZE],
                            const uint8_t nonce[NOISE_NONCE_SIZE],
                            const uint8_t *associated_data,
                            size_t associated_data_length,
                            const uint8_t *plaintext, size_t plaintext_length,
                            uint8_t *ciphertext) {
  // ciphertext = AES-GCM-Encrypt(key, nonce, associated_data, plaintext)
  memcpy(ciphertext, plaintext, plaintext_length);

  if (!noise_internal_encrypt_inplace(key, nonce, associated_data,
                                      associated_data_length, ciphertext,
                                      plaintext_length)) {
    memzero(ciphertext, plaintext_length);
    return false;
  }

  return true;
}

bool noise_internal_decrypt_inplace(const uint8_t key[NOISE_KEY_SIZE],
                                    const uint8_t nonce[NOISE_NONCE_SIZE],
                                    const uint8_t *associated_data,
                                    size_t associated_data_length,
                                    uint8_t *in_out, size_t ciphertext_length) {
  if (ciphertext_length < NOISE_TAG_SIZE) {
    return false;
  }
  const size_t plaintext_length = ciphertext_length - NOISE_TAG_SIZE;

  gcm_ctx ctx = {0};
  if (gcm_init_and_key(key, NOISE_KEY_SIZE, &ctx) != RETURN_GOOD) {
    return false;
  }

  if (gcm_decrypt_message(nonce, NOISE_NONCE_SIZE, associated_data,
                          associated_data_length, in_out, plaintext_length,
                          in_out + plaintext_length, NOISE_TAG_SIZE,
                          &ctx) != RETURN_GOOD) {
    memzero(&ctx, sizeof(ctx));
    return false;
  }
  memzero(&ctx, sizeof(ctx));

  return true;
}

bool noise_internal_decrypt(const uint8_t key[NOISE_KEY_SIZE],
                            const uint8_t nonce[NOISE_NONCE_SIZE],
                            const uint8_t *associated_data,
                            size_t associated_data_length,
                            const uint8_t *ciphertext, size_t ciphertext_length,
                            uint8_t *plaintext) {
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

void noise_internal_mix_hash(uint8_t hash[SHA256_DIGEST_LENGTH],
                             const uint8_t *data, size_t data_length) {
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

void noise_internal_mix_key(uint8_t chaining_key[SHA256_DIGEST_LENGTH],
                            curve25519_key input_key,
                            uint8_t output_key[NOISE_KEY_SIZE]) {
  // chaining_key || output_key =
  //   HKDF(salt=chaining_key, key=input_key, output_length=2*NOISE_KEY_SIZE)
  hkdf(chaining_key, SHA256_DIGEST_LENGTH, input_key, sizeof(curve25519_key),
       chaining_key, output_key);
  _Static_assert(NOISE_KEY_SIZE == SHA256_DIGEST_LENGTH,
                 "output_key must be truncated to NOISE_KEY_SIZE");
}

void noise_internal_split(uint8_t chaining_key[SHA256_DIGEST_LENGTH],
                          uint8_t output1[NOISE_KEY_SIZE],
                          uint8_t output2[NOISE_KEY_SIZE]) {
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

bool noise_send_message(noise_context_t *ctx, const uint8_t *associated_data,
                        size_t associated_data_length, const uint8_t *plaintext,
                        size_t plaintext_length, uint8_t *ciphertext) {
  if (!ctx->initialized) {
    return false;
  }
  if (!noise_internal_encrypt(ctx->encryption_key, ctx->encryption_nonce,
                              associated_data, associated_data_length,
                              plaintext, plaintext_length, ciphertext)) {
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
  if (!noise_internal_decrypt(ctx->decryption_key, ctx->decryption_nonce,
                              associated_data, associated_data_length,
                              ciphertext, ciphertext_length, plaintext)) {
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

bool noise_send_message_inplace(noise_context_t *ctx,
                                const uint8_t *associated_data,
                                size_t associated_data_length, uint8_t *in_out,
                                size_t plaintext_length) {
  if (!ctx->initialized) {
    return false;
  }
  if (!noise_internal_encrypt_inplace(
          ctx->encryption_key, ctx->encryption_nonce, associated_data,
          associated_data_length, in_out, plaintext_length)) {
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

bool noise_receive_message_inplace(noise_context_t *ctx,
                                   const uint8_t *associated_data,
                                   size_t associated_data_length,
                                   uint8_t *in_out, size_t ciphertext_length) {
  if (!ctx->initialized) {
    return false;
  }
  if (!noise_internal_decrypt_inplace(
          ctx->decryption_key, ctx->decryption_nonce, associated_data,
          associated_data_length, in_out, ciphertext_length)) {
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
