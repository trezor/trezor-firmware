/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <string.h>
#include "memzero.h"
/* RFC 3394 section 2.2, n=4. AES primitive uses an opaque hardware key.
 * A failed unwrap never releases partial key bytes. Private to the vault. */
typedef bool (*vault_wrap_block_t)(bool encrypt, const uint8_t in[16],
                                   uint8_t out[16]);
static bool vault_keywrap(bool encrypt, uint8_t value[40],
                          vault_wrap_block_t block) {
  uint8_t work[40] = {0};
  uint8_t b[16] __attribute__((aligned(4))) = {0};
  bool ok = false;
  memcpy(work, value, 40);
  if (encrypt) memset(work, 0xa6, 8);
  for (int round = 0; round < 6; round++) {
    int j = encrypt ? round : 5 - round;
    for (int step = 0; step < 4; step++) {
      int i = encrypt ? step + 1 : 4 - step;
      /* t <= 24; XOR into the least significant byte of big-endian A. */
      memcpy(b, work, 8);
      memcpy(b + 8, work + 8 * i, 8);
      if (!encrypt) b[7] ^= 4 * j + i;
      if (!block(encrypt, b, b)) goto cleanup;
      if (encrypt) b[7] ^= 4 * j + i;
      memcpy(work, b, 8);
      memcpy(work + 8 * i, b + 8, 8);
    }
  }
  if (!encrypt) {
    uint8_t diff = 0;
    for (size_t i = 0; i < 8; i++) diff |= work[i] ^ 0xa6;
    if (diff) goto cleanup;
  }
  memcpy(value, work, 40);
  ok = true;
cleanup:
  if (!ok) memzero(value, 40);
  memzero(work, sizeof(work));
  memzero(b, sizeof(b));
  return ok;
}
