#include <sec/rng_strong.h>
#include <trezor_rtl.h>

void randombytes(unsigned char *x, unsigned long long xlen) {
  ensure_true(rng_fill_buffer_strong(x, (size_t)xlen),
              "Strong RNG failed while signing");
}
