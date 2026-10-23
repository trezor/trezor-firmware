/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifdef SECURE_MODE

#include <sec/secure_aes.h>
#include <sec/vault_kek.h>

#include "../../vault/keywrap.h"

static bool vault_kek_block(bool encrypt, const uint8_t in[16],
                            uint8_t out[16]) {
  /* BHK is held in locked backup registers/SAES and never leaves them. */
  return (encrypt ? secure_aes_ecb_encrypt_hw(in, 16, out, SECURE_AES_KEY_BHK)
                  : secure_aes_ecb_decrypt_hw(in, 16, out,
                                              SECURE_AES_KEY_BHK)) == sectrue;
}

secbool vault_kek_wrap(bool encrypt, uint8_t value[40]) {
  bool ok = secure_aes_init() == sectrue &&
            vault_keywrap(encrypt, value, vault_kek_block);
  /* Reset SAES data/key registers on both success and failure. Leave the
   * peripheral initialized for existing users of the secure_aes interface. */
  if (secure_aes_init() != sectrue) ok = false;
  if (!ok) memzero(value, 40);
  return ok ? sectrue : secfalse;
}

#endif  // SECURE_MODE
