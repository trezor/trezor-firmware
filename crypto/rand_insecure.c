/**
 * Copyright (c) 2013-2014 Tomas Dzetkulic
 * Copyright (c) 2013-2014 Pavol Rusnak
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

// Guard against this file ever being compiled into a production build.
#if defined(PRODUCTION) && PRODUCTION
#error "Insecure PRNG must not be compiled into a production build"
#endif

// Guard against this file ever being compiled into a bare-metal build.
_Static_assert(
    sizeof(void *) == 8,
    "Insecure PRNG compiled for a non 64-bit target, a device build?");
#if !defined(__linux__) && !defined(__APPLE__) && !defined(_WIN32)
#error "Insecure PRNG must not be compiled for a bare-metal target"
#endif
#if __STDC_HOSTED__ == 0
#error "Insecure PRNG must not be compiled for a freestanding target"
#endif

#include "rand.h"

#ifdef USE_INSECURE_PRNG

#pragma message( \
    "NOT SUITABLE FOR PRODUCTION USE! Replace random_buffer() function with your own secure code.")

static uint32_t seed = 0;

void random_reseed(const uint32_t value) { seed = value; }

static uint32_t lcg_get_u32(void) {
  // Linear congruential generator from Numerical Recipes
  // https://en.wikipedia.org/wiki/Linear_congruential_generator
  seed = 1664525 * seed + 1013904223;
  return seed;
}

void random_buffer(uint8_t *buf, size_t len) {
  uint32_t r = 0;
  for (size_t i = 0; i < len; i++) {
    if (i % 4 == 0) {
      r = lcg_get_u32();
    }
    buf[i] = (r >> ((i % 4) * 8)) & 0xFF;
  }
}

#endif /* USE_INSECURE_PRNG */
