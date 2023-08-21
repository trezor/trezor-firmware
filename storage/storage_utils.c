
#include <stdint.h>

uint32_t hamming_weight(uint32_t value) {
  value = value - ((value >> 1) & 0x55555555);
  value = (value & 0x33333333) + ((value >> 2) & 0x33333333);
  value = (value + (value >> 4)) & 0x0F0F0F0F;
  value = value + (value >> 8);
  value = value + (value >> 16);
  return value & 0x3F;
}
