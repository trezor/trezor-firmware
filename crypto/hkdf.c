/**
 * HKDF-SHA256 implementation (RFC 5869)
 *
 * Used for quantum-safe key derivation in SPHINCS+ (FIPS 205).
 */

#include <string.h>

#include "hkdf.h"
#include "hmac.h"
#include "memzero.h"

void hkdf_sha256_extract(const uint8_t *salt, size_t salt_len,
                         const uint8_t *ikm, size_t ikm_len,
                         uint8_t prk[32]) {
  // RFC 5869 Section 2.2: if salt not provided, use HashLen zero octets
  const uint8_t default_salt[32] = {0};
  if (salt == NULL || salt_len == 0) {
    salt = default_salt;
    salt_len = 32;
  }

  hmac_sha256(salt, (uint32_t)salt_len, ikm, (uint32_t)ikm_len, prk);
}

int hkdf_sha256_expand(const uint8_t prk[32],
                       const uint8_t *info, size_t info_len,
                       uint8_t *okm, size_t okm_len) {
  // RFC 5869 Section 2.3: L <= 255*HashLen
  if (okm_len > 255 * 32) {
    return -1;
  }

  uint8_t t[32] = {0};  // T(0) = empty string
  size_t t_len = 0;
  size_t offset = 0;
  uint8_t counter = 1;

  while (offset < okm_len) {
    HMAC_SHA256_CTX hctx;
    hmac_sha256_Init(&hctx, prk, 32);

    if (t_len > 0) {
      hmac_sha256_Update(&hctx, t, (uint32_t)t_len);
    }
    if (info != NULL && info_len > 0) {
      hmac_sha256_Update(&hctx, info, (uint32_t)info_len);
    }
    hmac_sha256_Update(&hctx, &counter, 1);

    hmac_sha256_Final(&hctx, t);
    t_len = 32;

    size_t copy_len = okm_len - offset;
    if (copy_len > 32) {
      copy_len = 32;
    }
    memcpy(okm + offset, t, copy_len);

    offset += copy_len;
    counter++;

    memzero(&hctx, sizeof(hctx));
  }

  memzero(t, sizeof(t));
  return 0;
}

int hkdf_sha256(const uint8_t *salt, size_t salt_len,
                const uint8_t *ikm, size_t ikm_len,
                const uint8_t *info, size_t info_len,
                uint8_t *okm, size_t okm_len) {
  uint8_t prk[32];

  hkdf_sha256_extract(salt, salt_len, ikm, ikm_len, prk);
  int ret = hkdf_sha256_expand(prk, info, info_len, okm, okm_len);

  memzero(prk, sizeof(prk));
  return ret;
}
