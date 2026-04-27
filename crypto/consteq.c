#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

bool consteq(const uint8_t *sec, size_t seclen, const uint8_t *pub,
             size_t publen) {
  size_t diff = seclen - publen;
  for (size_t i = 0; i < publen; i++) {
    diff |= sec[i] - pub[i];
  }
  return diff == 0;
}
