#include "schnorr.h"

// r = H(Q, kpub, m)
static void calc_r(const curve_point *Q,
                   const uint8_t pub_key[33], const uint8_t *msg,
                   const uint32_t msg_len, bignum256 *r) {
  uint8_t Q_compress[33];
  compress_coords(Q, Q_compress);

  SHA256_CTX ctx;
  uint8_t digest[SHA256_DIGEST_LENGTH];
  sha256_Init(&ctx);
  sha256_Update(&ctx, Q_compress, 33);
  sha256_Update(&ctx, pub_key, 33);
  sha256_Update(&ctx, msg, msg_len);
  sha256_Final(&ctx, digest);
  bn_read_be(digest, r);
}

// returns 0 if verification succeeded
int schnorr_sign(const ecdsa_curve *curve, const uint8_t *priv_key,
                 const bignum256 *k, const uint8_t *msg, const uint32_t msg_len,
                 schnorr_sign_pair *result) {
  uint8_t pub_key[33];
  curve_point Q;
  bignum256 private_key_scalar;

  bn_read_be(priv_key, &private_key_scalar);
  ecdsa_get_public_key33(curve, priv_key, pub_key);

  /* Q = kG */
  point_multiply(curve, k, &curve->G, &Q);

  /* r = H(Q, kpub, m) */
  calc_r(&Q, pub_key, msg, msg_len, &result->r);

  /* s = k - r*kpriv mod(order) */
  bignum256 s_temp = {0};
  bn_copy(&result->r, &s_temp);
  bn_multiply(&private_key_scalar, &s_temp, &curve->order);
  bn_subtractmod(k, &s_temp, &result->s, &curve->order);

  while (bn_is_less(&curve->order, &result->s) ||
         bn_is_equal(&curve->order, &result->s)) {
    bn_mod(&result->s, &curve->order);
  }

  return 0;
}

int schnorr_verify(const ecdsa_curve *curve, const uint8_t *pub_key,
                   const uint8_t *msg, const uint32_t msg_len,
                   const schnorr_sign_pair *sign) {
  if (msg_len == 0) return 1;
  if (bn_is_zero(&sign->r)) return 2;
  if (bn_is_zero(&sign->s)) return 3;
  if (bn_is_less(&curve->order, &sign->r)) return 4;
  if (bn_is_less(&curve->order, &sign->s)) return 5;

  curve_point pub_key_point;
  if (!ecdsa_read_pubkey(curve, pub_key, &pub_key_point)) {
    return 6;
  }

  // Compute Q = sG + r*kpub
  curve_point sG, Q;
  point_multiply(curve, &sign->s, &curve->G, &sG);
  point_multiply(curve, &sign->r, &pub_key_point, &Q);
  point_add(curve, &sG, &Q);

  /* r = H(Q, kpub, m) */
  bignum256 r;
  calc_r(&Q, pub_key, msg, msg_len, &r);

  if (bn_is_equal(&r, &sign->r)) return 0;  // success

  return 10;
}