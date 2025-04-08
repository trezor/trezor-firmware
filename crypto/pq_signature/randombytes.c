#include "rand.h"

int PQCLEAN_randombytes(uint8_t *output, size_t n) {
  random_buffer(output, n);
  return 0;
}

int randombytes(uint8_t *output, size_t n) {
  random_buffer(output, n);
  return 0;
}
