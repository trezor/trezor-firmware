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
#include <assert.h>
#include <stdint.h>
#include <string.h>

#include "bignum.h"
#include "ecdsa.h"
#include "memzero.h"
#include "nist256p1.h"
#include "sha2.h"

#include "hash_to_curve.h"

// https://www.rfc-editor.org/rfc/rfc9380.html#name-hash_to_field-implementatio
static bool hash_to_field(const uint8_t *msg, size_t msg_len,
                          const uint8_t *dst,  // domain separation tag
                          const size_t dst_len, size_t expansion_len,
                          const bignum256 *prime,
                          bool expand(const uint8_t *, size_t, const uint8_t *,
                                      size_t, uint8_t *, size_t),
                          bignum256 *out, size_t out_len) {
  const size_t max_expansion_len = 64;
  if (expansion_len > max_expansion_len) {
    // Not supported by this implementation
    return false;
  }

  const size_t expanded_msg_length = out_len * expansion_len;
  uint8_t expanded_msg[expanded_msg_length];
  memzero(expanded_msg, sizeof(expanded_msg));

  if (!expand(msg, msg_len, dst, dst_len, expanded_msg, expanded_msg_length)) {
    return false;
  }

  uint8_t raw_number[max_expansion_len];
  memzero(raw_number, sizeof(raw_number));
  bignum512 bn_number = {0};

  for (size_t i = 0; i < out_len; i++) {
    memcpy(raw_number + (max_expansion_len - expansion_len),
           expanded_msg + i * expansion_len, expansion_len);

    bn_read_be_512(raw_number, &bn_number);
    bn_reduce(&bn_number, prime);
    bn_copy_lower(&bn_number, &out[i]);
    bn_mod(&out[i], prime);
  }

  memzero(expanded_msg, sizeof(expanded_msg));
  memzero(raw_number, sizeof(raw_number));
  memzero(&bn_number, sizeof(bn_number));

  return true;
}

// Simplified Shallue-van de Woestijne-Ulas Method
// https://www.rfc-editor.org/rfc/rfc9380.html#name-simplified-shallue-van-de-w
// Algorithm assumptions:
//   * z is a non-square modulo p
//   * z != -1 modulo p
//   * x^2 + a * x + b - z is an irreducible polynomial modulo p
//   * (b/(z*a))^2 + a * (b/(z*a)) + b is a square modulo p
//   * z is not zero
//   * a is not zero
//   * b is not zero
//   * p is at least 6
//  Implementation assumptions:
//   * p is a prime
//   * 2**256 - 2**224 <= prime <= 2**256
//   * p % 4 == 3
static bool simple_swu(const bignum256 *u, const bignum256 *a,
                       const bignum256 *b, const bignum256 *p,
                       const bignum256 *z, int sign_function(const bignum256 *),
                       curve_point *point) {
  if (bn_is_zero(a) || bn_is_zero(b) || (p->val[0] % 4 != 3)) {
    return false;
  }

  // c1 = -b / a
  bignum256 c1 = {0};
  bn_copy(a, &c1);
  bn_subtract(p, &c1, &c1);
  bn_inverse(&c1, p);
  bn_multiply(b, &c1, p);
  bn_mod(&c1, p);

  // c2 = -1 / z
  bignum256 c2 = {0};
  bn_copy(z, &c2);
  bn_subtract(p, &c2, &c2);
  bn_inverse(&c2, p);
  bn_mod(&c2, p);

  // t1 = z * u^2
  bignum256 t1 = {0};
  bn_copy(u, &t1);
  bn_multiply(&t1, &t1, p);
  bn_mod(&t1, p);
  bn_multiply(z, &t1, p);
  bn_mod(&t1, p);

  // t2 = t1^2
  bignum256 t2 = {0};
  bn_copy(&t1, &t2);
  bn_multiply(&t2, &t2, p);
  bn_mod(&t2, p);

  // x1 = t1 + t2
  bignum256 x1 = {0};
  bn_copy(&t1, &x1);
  bn_add(&x1, &t2);
  bn_mod(&x1, p);

  // x1 = inv0(1)
  bn_inverse(&x1, p);

  // e1 = x1 == 0
  int e1 = bn_is_zero(&x1);

  // x1 = x1 + 1
  bn_addi(&x1, 1);
  bn_mod(&x1, p);

  // x1 = CMOV(x1, c2, e1)
  bn_cmov(&x1, e1, &c2, &x1);
  memzero(&c2, sizeof(c2));

  // x1 = x1 * c1
  bn_multiply(&c1, &x1, p);
  memzero(&c1, sizeof(c1));
  bn_mod(&x1, p);

  // gx1 = x1^2
  bignum256 gx1 = {0};
  bn_copy(&x1, &gx1);
  bn_multiply(&x1, &gx1, p);
  bn_mod(&gx1, p);

  // gx1 = gx1 + A
  bn_add(&gx1, a);
  bn_mod(&gx1, p);

  // gx1 = gx1 * x1
  bn_multiply(&x1, &gx1, p);
  bn_mod(&gx1, p);

  // gx1 = gx1 + B
  bn_add(&gx1, b);
  bn_mod(&gx1, p);

  // x2 = t1 * x1
  bignum256 x2 = {0};
  bn_copy(&t1, &x2);
  bn_multiply(&x1, &x2, p);
  bn_mod(&x2, p);

  // t2 = t1 * t2
  bn_multiply(&t1, &t2, p);
  memzero(&t1, sizeof(t1));
  bn_mod(&t2, p);

  // gx2 = gx1 * t2
  bignum256 gx2 = {0};
  bn_copy(&gx1, &gx2);
  bn_multiply(&t2, &gx2, p);
  memzero(&t2, sizeof(t2));
  bn_mod(&gx2, p);

  // e2 = is_square(gx1)
  int e2 = bn_legendre(&gx1, p) >= 0;

  // x = CMOV(x2, x1, e2)
  bignum256 x = {0};
  bn_cmov(&x, e2, &x1, &x2);
  memzero(&x1, sizeof(x1));
  memzero(&x2, sizeof(x2));

  // y2 = CMOV(gx2, gx1, e2)
  bignum256 y2 = {0};
  bn_cmov(&y2, e2, &gx1, &gx2);
  memzero(&gx1, sizeof(gx1));
  memzero(&gx2, sizeof(gx2));

  // y = sqrt(y2)
  bignum256 y = {0};
  bn_copy(&y2, &y);
  memzero(&y2, sizeof(y2));
  bn_sqrt(&y, p);  // This is the slowest operation

  // e3 = sgn0(u) == sgn0(y)
  int e3 = sign_function(u) == sign_function(&y);

  bignum256 minus_y = {0};
  bn_subtract(p, &y, &minus_y);

  // y = CMOV(-y, y, e3)
  bn_cmov(&y, e3, &y, &minus_y);
  memzero(&minus_y, sizeof(minus_y));

  bn_copy(&x, &point->x);
  bn_copy(&y, &point->y);
  memzero(&x, sizeof(x));
  memzero(&y, sizeof(y));

  return true;
}

static void bn_read_int32(int32_t in_number, const bignum256 *prime,
                          bignum256 *out_number) {
  if (in_number < 0) {
    bn_read_uint32(-in_number, out_number);
    bn_subtract(prime, out_number, out_number);
  } else {
    bn_read_uint32(in_number, out_number);
  }
}

// https://www.rfc-editor.org/rfc/rfc9380.html#name-encoding-byte-strings-to-el
static bool hash_to_curve(const uint8_t *msg, size_t msg_len,
                          const ecdsa_curve *curve, const uint8_t *suite_id,
                          const uint8_t suite_id_len, int z, int cofactor,
                          bool expand_function(const uint8_t *, size_t,
                                               const uint8_t *, size_t,
                                               uint8_t *, size_t),
                          int sign_function(const bignum256 *),
                          curve_point *point) {
  if (cofactor != 1) {
    // Not supported by this implementation
    return false;
  }

  bignum256 bn_z = {0};
  bn_read_int32(z, &curve->prime, &bn_z);

  bignum256 bn_a = {0};
  bn_read_int32(curve->a, &curve->prime, &bn_a);

  bignum256 u[2] = {0};

  if (!hash_to_field(msg, msg_len, suite_id, suite_id_len, 48, &curve->prime,
                     expand_function, u, 2)) {
    return false;
  }

  curve_point point1 = {0}, point2 = {0};

  if (!simple_swu(&u[0], &bn_a, &curve->b, &curve->prime, &bn_z, sign_function,
                  &point1)) {
    memzero(&u[0], sizeof(u[0]));
    return false;
  }
  memzero(&u[0], sizeof(u[0]));

  if (!simple_swu(&u[1], &bn_a, &curve->b, &curve->prime, &bn_z, sign_function,
                  &point2)) {
    memzero(&u[1], sizeof(u[1]));
    return false;
  }
  memzero(&u[1], sizeof(u[1]));

  point_add(curve, &point1, &point2);

  point->x = point2.x;
  point->y = point2.y;

  memzero(&point1, sizeof(point1));
  memzero(&point2, sizeof(point2));

  return true;
}

static int sgn0(const bignum256 *a) {
  // https://datatracker.ietf.org/doc/html/draft-irtf-cfrg-hash-to-curve-05#section-4.1.2
  if (bn_is_even(a)) {
    return 1;
  }

  return -1;
}

// https://www.rfc-editor.org/rfc/rfc9380.html#hashtofield-expand-xmd
bool expand_message_xmd_sha256(const uint8_t *msg, size_t msg_len,
                               const uint8_t *dst,  // domain separation tag
                               size_t dst_len, uint8_t *output,
                               size_t output_len) {
  if (dst_len > 255) {
    return false;
  }

  if ((output_len > 65535) || (output_len > 255 * SHA256_DIGEST_LENGTH)) {
    return false;
  }

  const uint8_t zero_block[SHA256_BLOCK_LENGTH] = {0};
  const uint8_t output_len_bytes[2] = {(output_len >> 8) & 255,
                                       output_len & 255};
  const uint8_t dst_len_bytes[1] = {dst_len & 255};
  const uint8_t zero[1] = {0};

  SHA256_CTX ctx = {0};
  sha256_Init(&ctx);

  // Z_pad = I2OSP(0, s_in_bytes)
  sha256_Update(&ctx, zero_block, sizeof(zero_block));

  // msg
  sha256_Update(&ctx, msg, msg_len);

  // l_i_b_str = I2OSP(len_in_bytes, 2)
  sha256_Update(&ctx, output_len_bytes, sizeof(output_len_bytes));

  // I2OSP(0, 1)
  sha256_Update(&ctx, zero, sizeof(zero));

  // DST_prime = DST || I2OSP(len(DST), 1)
  sha256_Update(&ctx, dst, dst_len);
  sha256_Update(&ctx, dst_len_bytes, sizeof(dst_len_bytes));

  uint8_t first_digest[SHA256_DIGEST_LENGTH] = {0};  // b_0
  sha256_Final(&ctx, first_digest);

  uint8_t current_digest[SHA256_DIGEST_LENGTH] = {0};  // b_i

  size_t output_position = 0;
  size_t remaining_output_length = output_len;
  int i = 1;

  while (remaining_output_length > 0) {
    const uint8_t i_bytes[1] = {i & 255};

    // strxor(b_0, b_(i - 1))
    for (size_t j = 0; j < sizeof(current_digest); j++) {
      current_digest[j] ^= first_digest[j];
    }

    sha256_Init(&ctx);

    // strxor(b_0, b_(i - 1))
    sha256_Update(&ctx, current_digest, sizeof(current_digest));

    // I2OSP(i, 1)
    sha256_Update(&ctx, i_bytes, sizeof(i_bytes));

    // DST_prime = DST || I2OSP(len(DST), 1)
    sha256_Update(&ctx, dst, dst_len);
    sha256_Update(&ctx, dst_len_bytes, sizeof(dst_len_bytes));

    sha256_Final(&ctx, current_digest);

    const size_t copy_length = remaining_output_length > SHA256_DIGEST_LENGTH
                                   ? SHA256_DIGEST_LENGTH
                                   : remaining_output_length;
    memcpy(output + output_position, current_digest, copy_length);

    output_position += copy_length;
    remaining_output_length -= copy_length;
    i++;
  }

  memzero(&ctx, sizeof(ctx));
  memzero(first_digest, sizeof(first_digest));
  memzero(current_digest, sizeof(current_digest));

  return true;
}

bool hash_to_curve_p256(const uint8_t *msg, size_t msg_len, const uint8_t *dst,
                        size_t dst_len, curve_point *point) {
  // https://www.rfc-editor.org/rfc/rfc9380.html#suites-p256
  // P256_XMD:SHA-256_SSWU_RO_
  if (!hash_to_curve(msg, msg_len, &nist256p1, dst, dst_len, -10, 1,
                     expand_message_xmd_sha256, sgn0, point)) {
    return false;
  }

  return true;
}

bool hash_to_curve_optiga(const uint8_t input[32], uint8_t public_key[65]) {
  char dst[] = "OPTIGA-SECRET-V0-P256_XMD:SHA-256_SSWU_RO_";
  curve_point point = {0};

  if (!hash_to_curve_p256(input, 32, (uint8_t *)dst, sizeof(dst) - 1, &point)) {
    return false;
  }

  public_key[0] = 0x04;
  bn_write_be(&point.x, public_key + 1);
  bn_write_be(&point.y, public_key + 33);

  memzero(&point, sizeof(point));

  return true;
}
