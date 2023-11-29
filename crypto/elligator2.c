/** Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions: The above copyright
 * notice and this permission notice shall be included in all copies or
 * substantial portions of the Software.
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
#include <stdbool.h>

#include "ed25519-donna/ed25519-donna.h"
#include "memzero.h"

#include "elligator2.h"

// Returns 1 if a equals b, returns 0 otherwise.
static int curve25519_isequal(bignum25519 a, const bignum25519 b) {
  bignum25519 difference;
  curve25519_sub(difference, a, b);
  int result = 1 - curve25519_isnonzero(difference);
  memzero(difference, sizeof(difference));
  return result;
}

// Sets out to a if c equals 0, sets out to b if c equals 1.
static void curve25519_cmov(bignum25519 out, const bignum25519 a,
                            const bignum25519 b, uint32_t c) {
  assert((int)(c == 1) | (int)(c == 0));

  bignum25519 a_copy = {0}, b_copy = {0};
  curve25519_copy(a_copy, a);
  curve25519_copy(b_copy, b);
  curve25519_swap_conditional(a_copy, b_copy, c);
  memzero(b_copy, sizeof(b_copy));
  curve25519_copy(out, a_copy);
  memzero(a_copy, sizeof(a_copy));
}

bool map_to_curve_elligator2_curve25519(const uint8_t input[32],
                                        curve25519_key output) {
  // https://www.rfc-editor.org/rfc/rfc9380.html#map-to-curve25519
  // The procedure from the above link is used, with the exception that the
  // y-coordinate of the output point is not computed, because it is not needed.
  bignum25519 input_bignum = {0};
  curve25519_expand(input_bignum, (unsigned char*)input);

  // c3 = sqrt(-1)
  bignum25519 c3 = {0};
  curve25519_set_sqrtneg1(c3);

  // J = 486662
  bignum25519 j = {0};
  curve25519_set(j, 486662);

  // tv1 = u^2
  bignum25519 tv1 = {0};
  curve25519_square(tv1, input_bignum);
  memzero(input_bignum, sizeof(input_bignum));

  // tv1 = 2 * tv1
  curve25519_add_reduce(tv1, tv1, tv1);

  // xd = tv1 + 1
  bignum25519 xd = {0};
  bignum25519 one = {0};
  curve25519_set(one, 1);
  curve25519_add_reduce(xd, tv1, one);
  memzero(one, sizeof(one));

  // x1n = -J
  bignum25519 x1n = {0};
  curve25519_neg(x1n, j);

  // tv2 = xd^2
  bignum25519 tv2 = {0};
  curve25519_square(tv2, xd);

  // gxd = tv2 * xd
  bignum25519 gxd = {0};
  curve25519_mul(gxd, tv2, xd);

  // gx1 = J * tv1
  bignum25519 gx1 = {0};
  curve25519_mul(gx1, j, tv1);
  memzero(j, sizeof(j));

  // gx1 = gx1 * x1n
  curve25519_mul(gx1, gx1, x1n);

  // gx1 = gx1 + tv2
  curve25519_add_reduce(gx1, gx1, tv2);

  // gx1 = gx1 * x1n
  curve25519_mul(gx1, gx1, x1n);

  // tv3 = gxd^2
  bignum25519 tv3 = {0};
  curve25519_square(tv3, gxd);

  // tv2 = tv3^2
  curve25519_square(tv2, tv3);

  // tv3 = tv3 * gxd
  curve25519_mul(tv3, tv3, gxd);

  // tv3 = tv3 * gx1
  curve25519_mul(tv3, tv3, gx1);

  // tv2 = tv2 * tv3
  curve25519_mul(tv2, tv2, tv3);

  // y11 = tv2^c4
  bignum25519 y11 = {0};
  curve25519_pow_two252m3(y11, tv2);

  // y11 = y11 * tv3
  curve25519_mul(y11, y11, tv3);
  memzero(tv3, sizeof(tv3));

  // y12 = y11 * c3
  bignum25519 y12 = {0};
  curve25519_mul(y12, y11, c3);
  memzero(c3, sizeof(c3));

  // tv2 = y11^2
  curve25519_square(tv2, y11);

  // tv2 = tv2 * gxd
  curve25519_mul(tv2, tv2, gxd);

  // e1 = tv2 == gx1
  int e1 = curve25519_isequal(tv2, gx1);

  // y1 = CMOV(y12, y11, e1)
  bignum25519 y1 = {0};
  curve25519_cmov(y1, y12, y11, e1);
  memzero(y12, sizeof(y12));
  memzero(y11, sizeof(y11));
  memzero(&e1, sizeof(e1));

  // x2n = x1n * tv1
  bignum25519 x2n = {0};
  curve25519_mul(x2n, x1n, tv1);
  memzero(tv1, sizeof(tv1));

  // tv2 = y1^2
  curve25519_square(tv2, y1);
  memzero(y1, sizeof(y1));

  // tv2 = tv2 * gxd
  curve25519_mul(tv2, tv2, gxd);
  memzero(gxd, sizeof(gxd));

  // e3 = tv2 == gx1
  int e3 = curve25519_isequal(tv2, gx1);
  memzero(tv2, sizeof(tv2));
  memzero(gx1, sizeof(gx1));

  // xn = CMOV(x2n, x1n, e3)
  bignum25519 xn = {0};
  curve25519_cmov(xn, x2n, x1n, e3);
  memzero(x1n, sizeof(x1n));
  memzero(x2n, sizeof(x2n));
  memzero(&e3, sizeof(e3));

  // Compute the x-coordinate of the output point
  // x = xn / xd
  bignum25519 x = {0};
  curve25519_recip(x, xd);
  memzero(xd, sizeof(xd));
  curve25519_mul(x, xn, x);
  memzero(xn, sizeof(xn));

  // output = x
  curve25519_contract(output, x);
  memzero(x, sizeof(x));

  return true;
}
