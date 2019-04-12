/*
 * Low level API for Daan Sprenkels' Shamir secret sharing library
 * Copyright (c) 2017 Daan Sprenkels <hello@dsprenkels.com>
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
 *
 * Usage of this API is hazardous and is only reserved for beings with a
 * good understanding of the Shamir secret sharing scheme and who know how
 * crypto code is implemented. If you are unsure about this, use the
 * intermediate level API. You have been warned!
 */


#ifndef __SHAMIR_H__
#define __SHAMIR_H__

#include <stddef.h>
#include <stdint.h>

#define SHAMIR_MAX_LEN 32

/*
A list of pairs (x_i, y_i), where x_i is an integer and y_i is an array of bytes representing the evaluations of the polynomials in x_i.
The x coordinate of the result.
Evaluations of the polynomials in x.
 * Interpolate the `m` shares provided in `shares` and write the evaluation at
 * point `x` to `result`. The number of shares used to compute the result may
 * be larger than the threshold needed to .
 *
 * This function does *not* do *any* checking for integrity. If any of the
 * shares are not original, this will result in an invalid restored value.
 * All values written to `result` should be treated as secret. Even if some of
 * the shares that were provided as input were incorrect, the result *still*
 * allows an attacker to gain information about the correct result.
 *
 * This function treats `shares` and `result` as secret values. `m` is treated as
 * a public value (for performance reasons).
 */
void shamir_interpolate(uint8_t *result,
                        uint8_t result_index,
                        const uint8_t *share_indices,
                        const uint8_t **share_values,
                        uint8_t share_count,
                        size_t len);

#endif /* __SHAMIR_H__ */
