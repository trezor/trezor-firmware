/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include "../../embed/sec/vault/kwp.h"
#include "vault_kwp_vectors.h"

int main(void) {
  uint8_t key[32];
  for (size_t i = 0; i < sizeof(key); i++) key[i] = i;
  aes_encrypt_ctx encrypt;
  aes_decrypt_ctx decrypt;
  assert(!aes_encrypt_key256(key, &encrypt));
  assert(!aes_decrypt_key256(key, &decrypt));
  for (size_t n = 1; n <= VAULT_KWP_MAX_PLAINTEXT; n++) {
    uint8_t work[184] = {0};
    for (size_t i = 0; i < n; i++) work[8 + i] = i + n;
    size_t size = 8 + ((n + 7) & ~(size_t)7);
    assert(vault_kwp_crypt(true, work, n, vault_kwp_software_block, &encrypt));
    assert(!memcmp(work, kwp_vectors[n - 1], size));
    assert(vault_kwp_crypt(false, work, n, vault_kwp_software_block, &decrypt));
    for (size_t i = 0; i < n; i++) assert(work[8 + i] == (uint8_t)(i + n));
    memcpy(work, kwp_vectors[n - 1], size);
    work[size - 1] ^= 1;
    assert(
        !vault_kwp_crypt(false, work, n, vault_kwp_software_block, &decrypt));
    for (size_t i = 0; i < size; i++) assert(!work[i]);
  }
  /* This header also supplies the record adapter; verify its reserved-AAD
   * rejection without releasing either a secret or partial ciphertext. */
  uint8_t aad[32] = {0}, data[160] = {1}, tag[24] = {0};
  assert(vault_kwp_cipher_record(&encrypt, vault_kwp_software_block, true, aad,
                                 data, 8, tag));
  aad[31] = 1;
  assert(!vault_kwp_cipher_record(&decrypt, vault_kwp_software_block, false,
                                  aad, data, 8, tag));
  for (size_t i = 0; i < sizeof(data); i++) assert(!data[i]);
  memzero(&encrypt, sizeof(encrypt));
  memzero(&decrypt, sizeof(decrypt));
  puts("KWP independent vectors, lengths 1..172 and integrity checks passed");
}

void __attribute__((noreturn)) system_exit_error(const char *title,
                                                 const char *message,
                                                 const char *footer) {
  (void)title;
  (void)message;
  (void)footer;
  abort();
}
