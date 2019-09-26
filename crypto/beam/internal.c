#ifndef BEAM_DEBUG
#include "mpconfigport.h"
#endif

#include <string.h>
#include "../aes/aes.h"
#include "internal.h"
#include "multi_mac.h"

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"
#include "beam/lib/secp256k1-zkp/src/field_impl.h"
#include "beam/lib/secp256k1-zkp/src/group_impl.h"
#include "beam/lib/secp256k1-zkp/src/scalar_impl.h"
#pragma GCC diagnostic pop

int memis0(const void *p, size_t n) {
  for (size_t i = 0; i < n; i++)
    if (((const uint8_t *)p)[i]) return 0;
  return 1;
}

void memxor(uint8_t *pDst, const uint8_t *pSrc, size_t n) {
  for (size_t i = 0; i < n; i++) pDst[i] ^= pSrc[i];
}

void assing_aligned(uint8_t *dest, uint8_t *src, size_t bytes) {
  for (size_t i = bytes; i--; src++) dest[i] = *src;
}

void sha256_write_8(SHA256_CTX *hash, uint8_t b) {
  sha256_Update(hash, &b, sizeof(b));
}

void sha256_write_64(SHA256_CTX *hash, uint64_t v) {
  for (; v >= 0x80; v >>= 7) {
    sha256_write_8(hash, (uint8_t)((uint8_t)v | 0x80));
  }

  sha256_write_8(hash, (uint8_t)v);
}

int scalar_import_nnz(secp256k1_scalar *scalar, const uint8_t *data32) {
  int overflow;
  secp256k1_scalar_set_b32(scalar, data32, &overflow);
  int zero = secp256k1_scalar_is_zero(scalar);
  return !(overflow || zero);
}

void scalar_create_nnz(SHA256_CTX *oracle, secp256k1_scalar *out_scalar) {
  uint8_t data[32];
  secp256k1_scalar_clear(out_scalar);
  do {
    SHA256_CTX new_oracle;
    memcpy(&new_oracle, oracle, sizeof(SHA256_CTX));
    sha256_Final(&new_oracle, data);
    sha256_Update(oracle, data, sizeof(data) / sizeof(data[0]));
  } while (!scalar_import_nnz(out_scalar, data));
}

int point_import_nnz(secp256k1_gej *gej, const point_t *point) {
  if (point->y > 1) return 0;  // should always be well-formed

  secp256k1_fe nx;
  if (!secp256k1_fe_set_b32(&nx, point->x)) return 0;

  secp256k1_ge ge;
  if (!secp256k1_ge_set_xo_var(&ge, &nx, point->y)) return 0;

  secp256k1_gej_set_ge(gej, &ge);

  return 1;
}

int point_import(secp256k1_gej *gej, const point_t *point) {
  if (point_import_nnz(gej, point)) return 1;

  secp256k1_gej_set_infinity(gej);
  return memis0(point, sizeof(point_t));
}

void point_create_nnz(SHA256_CTX *oracle, secp256k1_gej *out_gej) {
  point_t pt;
  pt.y = 0;

  do {
    SHA256_CTX new_oracle;
    memcpy(&new_oracle, oracle, sizeof(SHA256_CTX));
    sha256_Final(&new_oracle, pt.x);
    sha256_Update(oracle, pt.x, SHA256_DIGEST_LENGTH);
  } while (!point_import_nnz(out_gej, &pt));
}

int export_gej_to_point(const secp256k1_gej *native_point, point_t *out_point) {
  if (secp256k1_gej_is_infinity(native_point) != 0) {
    memset(out_point, 0, sizeof(point_t));
    return 0;
  }

  secp256k1_gej pt = *native_point;
  secp256k1_ge ge;
  secp256k1_ge_set_gej(&ge, &pt);

  // seems like normalization can be omitted (already done by
  // secp256k1_ge_set_gej), but not guaranteed according to docs.
  // But this has a negligible impact on the performance
  secp256k1_fe_normalize(&ge.x);
  secp256k1_fe_normalize(&ge.y);

  secp256k1_fe_get_b32(out_point->x, &ge.x);
  out_point->y = (secp256k1_fe_is_odd(&ge.y) != 0);

  return 1;
}

void generator_mul_scalar(secp256k1_gej *res, const secp256k1_gej *pPts,
                          const secp256k1_scalar *sk) {
#ifndef BEAM_GENERATE_TABLES
  gej_mul_scalar(pPts, sk, res);
#else
  const uint32_t *p = sk->d;
  const int nWords = sizeof(sk->d) / sizeof(sk->d[0]);

  int bSet = 1;
  static_assert(8 % N_BITS_PER_LEVEL == 0);
  const int nLevelsPerWord = (sizeof(uint32_t) << 3) / N_BITS_PER_LEVEL;
  static_assert(
      !(nLevelsPerWord & (nLevelsPerWord - 1)));  // should be power-of-2

  // iterating in lsb to msb order
  for (int iWord = 0; iWord < nWords; iWord++) {
    uint32_t n = p[iWord];
    for (int j = 0; j < nLevelsPerWord; j++, pPts += N_POINTS_PER_LEVEL) {
      uint32_t nSel = (N_POINTS_PER_LEVEL - 1) & n;
      n >>= N_BITS_PER_LEVEL;

      /** This uses a conditional move to avoid any secret data in array
       * indexes.
       *   _Any_ use of secret indexes has been
       * demonstrated to result in timing
       *   sidechannels, even when the
       * cache-line access patterns are uniform.
       *  See also:
       *   "A word of warning", CHES 2013 Rump
       * Session, by Daniel J. Bernstein and Peter Schwabe
       *    (https://cryptojedi.org/peter/data/chesrump-20130822.pdf)
       * and
       *   "Cache Attacks and Countermeasures:
       * the Case of AES", RSA 2006,
       *    by Dag Arne Osvik, Adi Shamir, and
       * Eran Tromer
       *    (http://www.tau.ac.il/~tromer/papers/cache.pdf)
       */

      const secp256k1_gej *pSel;
      pSel = pPts + nSel;

      if (bSet) {
        *res = *pSel;
      } else {
        secp256k1_gej_add_var(res, res, pSel, NULL);
      }
      bSet = 0;
    }
  }
#endif
}

void signature_get_challenge(const secp256k1_gej *pt, const uint8_t *msg32,
                             secp256k1_scalar *out_scalar) {
  point_t p;
  secp256k1_gej point;
  memcpy(&point, pt, sizeof(secp256k1_gej));
  export_gej_to_point(&point, &p);

  SHA256_CTX oracle;
  sha256_Init(&oracle);
  sha256_Update(&oracle, p.x, 32);
  sha256_Update(&oracle, &p.y, 1);
  sha256_Update(&oracle, msg32, 32);

  scalar_create_nnz(&oracle, out_scalar);
}

void signature_sign_partial(const secp256k1_scalar *multisig_nonce,
                            const secp256k1_gej *multisig_nonce_pub,
                            const uint8_t *msg, const secp256k1_scalar *sk,
                            secp256k1_scalar *out_k) {
  signature_get_challenge(multisig_nonce_pub, msg, out_k);

  secp256k1_scalar_mul(out_k, out_k, sk);
  secp256k1_scalar_add(out_k, out_k, multisig_nonce);
  secp256k1_scalar_negate(out_k, out_k);
}

void gej_mul_scalar(const secp256k1_gej *pt, const secp256k1_scalar *sk,
                    secp256k1_gej *res) {
  multi_mac_casual_t mc;
  multi_mac_casual_init(&mc, pt, sk);

  multi_mac_t mm;
  mm.casual = &mc;
  mm.n_casual = 1;
  mm.n_prepared = 0;
  multi_mac_calculate(&mm, res);
}

void generate_HKdfPub(const uint8_t *secret_key,
                      const secp256k1_scalar *cofactor,
                      const secp256k1_gej *G_pts, const secp256k1_gej *J_pts,
                      HKdf_pub_packed_t *packed) {
  secp256k1_gej pkG, pkJ;
  generator_mul_scalar(&pkG, G_pts, cofactor);
  generator_mul_scalar(&pkJ, J_pts, cofactor);

  memcpy(packed->secret, secret_key, DIGEST_LENGTH);
  export_gej_to_point(&pkG, &packed->pkG);
  export_gej_to_point(&pkJ, &packed->pkJ);
}

void xcrypt(const uint8_t *secret_digest, uint8_t *data, size_t mac_value_size,
            size_t data_size) {
  uint8_t hvIV[32];
  SHA256_CTX x;
  sha256_Init(&x);
  sha256_Update(&x, secret_digest, DIGEST_LENGTH);
  sha256_Final(&x, hvIV);

  HMAC_SHA256_CTX y;
  hmac_sha256_Init(&y, secret_digest, DIGEST_LENGTH);
  hmac_sha256_Update(&y, data + mac_value_size, data_size);
  uint8_t cbuf[16];
  memcpy(cbuf, hvIV + 16, 16);
  hmac_sha256_Final(&y, hvIV);

  aes_encrypt_ctx ctxe;
  aes_encrypt_key256(secret_digest, &ctxe);
  aes_ctr_encrypt(data + mac_value_size, data + mac_value_size, data_size, cbuf,
                  aes_ctr_cbuf_inc, &ctxe);

  memcpy(data, hvIV + 32 - mac_value_size, mac_value_size);
}

uint8_t *export_encrypted(const void *p, size_t size, uint8_t code,
                          const uint8_t *secret, size_t secret_size,
                          const uint8_t *meta, size_t meta_size) {
  const size_t mac_value_size = 8;
  const size_t data_size = size + 1 + meta_size;
  const size_t buff_size = mac_value_size + data_size;
  uint8_t *mac_value = malloc(buff_size);
  memset(mac_value, 0, buff_size);

  mac_value[mac_value_size] = code;
  memcpy(mac_value + 1 + mac_value_size, p, size);
  memcpy(mac_value + 1 + mac_value_size + size, meta, meta_size);

  uint8_t hv_secret[32];
  pbkdf2_hmac_sha512(secret, secret_size, NULL, 0, 65536, hv_secret, 32);

  xcrypt(hv_secret, mac_value, mac_value_size, data_size);

  return mac_value;
}
