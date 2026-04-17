#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

bool consteq(const void *s1, const void *s2, size_t n) {
  const unsigned char *p1 = s1;
  const unsigned char *p2 = s2;
  int diff = 0;
  for (size_t i = 0; i < n; i++) {
    // Accumulate differences using OR to prevent early termination
    diff |= p1[i] ^ p2[i];
  }
  return diff == 0;
}
