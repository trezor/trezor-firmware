/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "slip21.h"
#include "hmac.h"
#include "memzero.h"

void slip21_from_seed(const uint8_t *seed, size_t length, uint8_t node[64]) {
  static const uint8_t salt[] = "Symmetric key seed";
  hmac_sha512(salt, sizeof(salt) - 1, seed, length, node);
}

bool slip21_derive_path(uint8_t node[64], const uint8_t *path, size_t length) {
  for (size_t i = 0; i < length;) {
    size_t n = path[i++];
    if (n > length - i) return false;
    i += n;
  }
  static const uint8_t zero = 0;
  for (size_t i = 0; i < length;) {
    size_t n = path[i++];
    HMAC_SHA512_CTX ctx = {0};
    hmac_sha512_Init(&ctx, node, 32);
    hmac_sha512_Update(&ctx, &zero, 1);
    hmac_sha512_Update(&ctx, path + i, n);
    hmac_sha512_Final(&ctx, node);
    memzero(&ctx, sizeof(ctx));
    i += n;
  }
  return true;
}
