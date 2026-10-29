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

/* secret_bhk_load() fills the BHK registers with zeros when the secret area
 * cannot be read. Refuse to wrap under that key instead of failing open:
 * AES-256 of a zero block under the all-zero key is a fixed value. */
static bool vault_kek_present(void) {
  static const uint8_t zero_key_block[16] = {0xdc, 0x95, 0xc0, 0x78, 0xa2, 0x40,
                                             0x89, 0x89, 0xad, 0x48, 0xa2, 0x14,
                                             0x92, 0x84, 0x20, 0x87};
  static bool present = false;
  if (present) return true;
  uint8_t block[16] = {0};
  bool ok = vault_kek_block(true, block, block) &&
            memcmp(block, zero_key_block, sizeof(block)) != 0;
  memzero(block, sizeof(block));
  present = ok;
  return ok;
}

secbool vault_kek_wrap(bool encrypt, uint8_t value[40]) {
  bool ok = secure_aes_init() == sectrue && vault_kek_present() &&
            vault_keywrap(encrypt, value, vault_kek_block);
  /* Reset SAES data/key registers on both success and failure. Leave the
   * peripheral initialized for existing users of the secure_aes interface. */
  if (secure_aes_init() != sectrue) ok = false;
  if (!ok) memzero(value, 40);
  return ok ? sectrue : secfalse;
}

#endif  // SECURE_MODE
