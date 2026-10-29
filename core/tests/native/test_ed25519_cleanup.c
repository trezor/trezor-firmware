/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "memzero.h"
static unsigned scalar_wipes;
static void observed_memzero(void *p, size_t length) {
  memzero(p, length);
  for (size_t i = 0; i < length; i++) assert(((uint8_t *)p)[i] == 0);
  if (length == 36) scalar_wipes++;
}
#define memzero observed_memzero
#include "../../../crypto/ed25519-donna/ed25519.c"
#undef memzero
int main(void) {
  uint8_t key[32] = {42}, public[32], output[64], signature[64];
  ed25519_publickey(key, public);
  scalar_wipes = 0;
  ed25519_sign((const uint8_t *)"message", 7, key, signature);
  assert(ed25519_sign_open((const uint8_t *)"message", 7, public, signature) ==
         0);
  assert(scalar_wipes >= 3);
  bool rejected = false;
  for (unsigned byte = 0; byte < 256; byte++) {
    memset(public, byte, sizeof(public));
    memset(output, 0x5a, sizeof(output));
    scalar_wipes = 0;
    if (ed25519_scalarmult(output, key, public) != 0) {
      assert(scalar_wipes > 0);
      for (size_t i = 0; i < 32; i++) assert(output[i] == 0);
      rejected = true;
      break;
    }
  }
  assert(rejected);
  uint8_t nonce[32];
  memset(nonce, 255, sizeof(nonce));
  memset(output, 0x5a, 32);
  scalar_wipes = 0;
  assert(ed25519_cosi_sign((const uint8_t *)"message", 7, key, nonce, public,
                           public, output) != 0);
  assert(scalar_wipes >= 3);
  for (size_t i = 0; i < 32; i++) assert(output[i] == 0);
  puts("Ed25519 live-frame cleanup checks passed");
}

void random_buffer(uint8_t *out, size_t length) { memset(out, 0x5a, length); }
void __attribute__((noreturn)) __assert_impl(const char *file, int line) {
  fprintf(stderr, "assertion: %s:%d\n", file, line);
  abort();
}
void __attribute__((noreturn)) system_exit_error(const char *title,
                                                 const char *message,
                                                 const char *footer) {
  (void)footer;
  fprintf(stderr, "%s: %s\n", title, message);
  abort();
}
