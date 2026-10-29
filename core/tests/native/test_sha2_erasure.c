/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "memzero.h"

static size_t erased64, erased128;
static void observed_memzero(void *p, size_t len) {
  memzero(p, len);
  for (size_t i = 0; i < len; i++) assert(((uint8_t *)p)[i] == 0);
  if (len == 64) erased64++;
  if (len == 128) erased128++;
}
/* Instrument only this translation unit; use the actual erasure primitive. */
#define memzero observed_memzero
#include "../../../crypto/sha2.c"
#undef memzero

int main(void) {
  uint32_t block256[16] = {0x80000000};
  uint64_t block512[16] = {UINT64_C(0x8000000000000000)};
  uint32_t out256[8] = {0};
  uint64_t out512[8] = {0};
  const uint32_t expected256[8] = {0xe3b0c442, 0x98fc1c14, 0x9afbf4c8,
                                   0x996fb924, 0x27ae41e4, 0x649b934c,
                                   0xa495991b, 0x7852b855};
  const uint64_t expected512[8] = {
      UINT64_C(0xcf83e1357eefb8bd), UINT64_C(0xf1542850d66d8007),
      UINT64_C(0xd620e4050b5715dc), UINT64_C(0x83f4a921d36ce9ce),
      UINT64_C(0x47d0d13c5d85f2b0), UINT64_C(0xff8318d2877eec2f),
      UINT64_C(0x63b931bd47417a81), UINT64_C(0xa538327af927da3e)};
  erased64 = erased128 = 0;
  sha256_Transform(sha256_initial_hash_value, block256, out256);
  assert(memcmp(out256, expected256, sizeof(out256)) == 0);
  assert(erased64 == 1);
  sha512_Transform(sha512_initial_hash_value, block512, out512);
  assert(memcmp(out512, expected512, sizeof(out512)) == 0);
  assert(erased128 == 1);
  puts("SHA-2 vectors and scratch erasure passed");
}
