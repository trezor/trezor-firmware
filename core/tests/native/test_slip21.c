/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "bip39.h"
#include "hmac.h"
#include "slip21.h"

void tc_fault_handler(const char *message) {
  fprintf(stderr, "%s\n", message);
  abort();
}

static void expect_key(const uint8_t node[64], const char *hex) {
  for (size_t i = 0; i < 32; i++) {
    unsigned byte = 0;
    assert(sscanf(hex + 2 * i, "%2x", &byte) == 1);
    assert(node[32 + i] == byte);
  }
}

int main(void) {
  uint8_t seed[64], root[64], node[64], clone[64];
  mnemonic_to_seed("all all all all all all all all all all all all", "", seed,
                   NULL);
  slip21_from_seed(seed, sizeof(seed), root);
  expect_key(
      root, "dbf12b44133eaab506a740f6565cc117228cbf1dd70635cfa8ddfdc9af734756");
  memcpy(node, root, sizeof(node));
  assert(slip21_derive_path(node, (const uint8_t *)"\011SLIP-0021", 10));
  expect_key(
      node, "1d065e3ac1bbe5c7fad32cf2305f7d709dc070d672044a19e610c77cdf33de0d");
  memcpy(clone, node, sizeof(clone));
  assert(slip21_derive_path(node, (const uint8_t *)"\025Master encryption key",
                            22));
  expect_key(
      node, "ea163130e35bbafdf5ddee97a17b39cef2be4b4f390180d65b54cf05c6a82fde");
  assert(
      slip21_derive_path(clone, (const uint8_t *)"\022Authentication key", 19));
  expect_key(
      clone,
      "47194e938ab24cc82bfa25f6486ed54bebe79c40ae2a5a32ea6db294d81861a6");
  memcpy(node, root, sizeof(node));
  assert(slip21_derive_path(node, NULL, 0));
  assert(!memcmp(node, root, sizeof(node)));
  assert(!slip21_derive_path(node, (const uint8_t *)"\001a\005b", 4));
  assert(!memcmp(node, root, sizeof(node)));
  assert(!slip21_derive_path(node, (const uint8_t *)"\377", 1));
  assert(!memcmp(node, root, sizeof(node)));
  uint8_t empty_label = 0, reference[64];
  hmac_sha512(root, 32, &empty_label, 1, reference);
  assert(slip21_derive_path(node, &empty_label, 1));
  assert(!memcmp(node, reference, sizeof(node)));
  uint8_t longest[256] = {255};
  memset(longest + 1, 'a', 255);
  uint8_t message[256] = {0};
  memcpy(message + 1, longest + 1, 255);
  hmac_sha512(node, 32, message, sizeof(message), reference);
  assert(slip21_derive_path(node, longest, sizeof(longest)));
  assert(!memcmp(node, reference, sizeof(node)));
  puts("SLIP-0021 vectors and path boundaries passed");
}
