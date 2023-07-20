/**
 * Copyright (c) 2023 Andrew R. Kozlik
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

/*
 * For a specification of TLS-PRF see
 * https://datatracker.ietf.org/doc/html/rfc5246#section-5
 */

#include <string.h>

#include "hmac.h"
#include "memzero.h"
#include "sha2.h"

void tls_prf_sha256(const uint8_t *secret, size_t secret_len,
                    const uint8_t *label, size_t label_len, const uint8_t *seed,
                    size_t seed_len, uint8_t *output, size_t out_len) {
  uint32_t idig[SHA256_DIGEST_LENGTH / sizeof(uint32_t)] = {0};
  uint32_t odig[SHA256_DIGEST_LENGTH / sizeof(uint32_t)] = {0};
  uint8_t a[SHA256_DIGEST_LENGTH] = {0};
  uint8_t result[SHA256_DIGEST_LENGTH] = {0};
  SHA256_CTX ctx = {0};

  // Prepare inner and outer digest.
  hmac_sha256_prepare(secret, secret_len, odig, idig);

  // a = HMAC(secret, label + seed)
  sha256_Init_ex(&ctx, idig, 8 * SHA256_BLOCK_LENGTH);
  sha256_Update(&ctx, label, label_len);
  sha256_Update(&ctx, seed, seed_len);
  sha256_Final(&ctx, a);
  sha256_Init_ex(&ctx, odig, 8 * SHA256_BLOCK_LENGTH);
  sha256_Update(&ctx, a, SHA256_DIGEST_LENGTH);
  sha256_Final(&ctx, a);

  while (1) {
    // result = HMAC(secret, a + label + seed)
    sha256_Init_ex(&ctx, idig, 8 * SHA256_BLOCK_LENGTH);
    sha256_Update(&ctx, a, SHA256_DIGEST_LENGTH);
    sha256_Update(&ctx, label, label_len);
    sha256_Update(&ctx, seed, seed_len);
    sha256_Final(&ctx, result);
    sha256_Init_ex(&ctx, odig, 8 * SHA256_BLOCK_LENGTH);
    sha256_Update(&ctx, result, SHA256_DIGEST_LENGTH);
    sha256_Final(&ctx, result);

    if (out_len <= SHA256_DIGEST_LENGTH) {
      break;
    }

    memcpy(output, result, SHA256_DIGEST_LENGTH);
    output += SHA256_DIGEST_LENGTH;
    out_len -= SHA256_DIGEST_LENGTH;

    // a = HMAC(secret, a)
    sha256_Init_ex(&ctx, idig, 8 * SHA256_BLOCK_LENGTH);
    sha256_Update(&ctx, a, SHA256_DIGEST_LENGTH);
    sha256_Final(&ctx, a);
    sha256_Init_ex(&ctx, odig, 8 * SHA256_BLOCK_LENGTH);
    sha256_Update(&ctx, a, SHA256_DIGEST_LENGTH);
    sha256_Final(&ctx, a);
  }

  memcpy(output, result, out_len);
  memzero(idig, sizeof(idig));
  memzero(odig, sizeof(odig));
  memzero(a, sizeof(a));
  memzero(result, sizeof(result));
}
