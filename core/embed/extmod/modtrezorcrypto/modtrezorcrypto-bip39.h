/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "py/objstr.h"
#include "py/runtime.h"

#include "bip39.h"
#include "sha2.h"

/// package: trezorcrypto.bip39

/// def complete_word(prefix: str) -> str | None:
///     """
///     Return the first word from the wordlist starting with prefix.
///     """
STATIC mp_obj_t mod_trezorcrypto_bip39_complete_word(mp_obj_t prefix) {
  mp_buffer_info_t pfx = {0};
  mp_get_buffer_raise(prefix, &pfx, MP_BUFFER_READ);
  if (pfx.len == 0) {
    return mp_const_none;
  }
  const char *word = mnemonic_complete_word(pfx.buf, pfx.len);
  if (word) {
    return mp_obj_new_str(word, strlen(word));
  } else {
    return mp_const_none;
  }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_bip39_complete_word_obj,
                                 mod_trezorcrypto_bip39_complete_word);

/// def word_completion_mask(prefix: str) -> int:
///     """
///     Return possible 1-letter suffixes for given word prefix.
///     Result is a bitmask, with 'a' on the lowest bit, 'b' on the second
///     lowest, etc.
///     """
STATIC mp_obj_t mod_trezorcrypto_bip39_word_completion_mask(mp_obj_t prefix) {
  mp_buffer_info_t pfx = {0};
  mp_get_buffer_raise(prefix, &pfx, MP_BUFFER_READ);
  return mp_obj_new_int(mnemonic_word_completion_mask(pfx.buf, pfx.len));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(
    mod_trezorcrypto_bip39_word_completion_mask_obj,
    mod_trezorcrypto_bip39_word_completion_mask);

/// def generate(strength: int) -> str:
///     """
///     Generate a mnemonic of given strength (128, 160, 192, 224 and 256 bits).
///     """
STATIC mp_obj_t mod_trezorcrypto_bip39_generate(mp_obj_t strength) {
  int bits = mp_obj_get_int(strength);
  if (bits % 32 || bits < 128 || bits > 256) {
    mp_raise_ValueError(
        "Invalid bit strength (only 128, 160, 192, 224 and 256 values are "
        "allowed)");
  }
  const char *mnemo = mnemonic_generate(bits);
  mp_obj_t res =
      mp_obj_new_str_copy(&mp_type_str, (const uint8_t *)mnemo, strlen(mnemo));
  mnemonic_clear();
  return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_bip39_generate_obj,
                                 mod_trezorcrypto_bip39_generate);

/// def from_data(data: bytes) -> str:
///     """
///     Generate a mnemonic from given data (of 16, 20, 24, 28 and 32 bytes).
///     """
STATIC mp_obj_t mod_trezorcrypto_bip39_from_data(mp_obj_t data) {
  mp_buffer_info_t bin = {0};
  mp_get_buffer_raise(data, &bin, MP_BUFFER_READ);
  if (bin.len % 4 || bin.len < 16 || bin.len > 32) {
    mp_raise_ValueError(
        "Invalid data length (only 16, 20, 24, 28 and 32 bytes are allowed)");
  }
  const char *mnemo = mnemonic_from_data(bin.buf, bin.len);
  mp_obj_t res =
      mp_obj_new_str_copy(&mp_type_str, (const uint8_t *)mnemo, strlen(mnemo));
  mnemonic_clear();
  return res;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_bip39_from_data_obj,
                                 mod_trezorcrypto_bip39_from_data);

/// def check(mnemonic: str) -> bool:
///     """
///     Check whether given mnemonic is valid.
///     """
STATIC mp_obj_t mod_trezorcrypto_bip39_check(mp_obj_t mnemonic) {
  mp_buffer_info_t text = {0};
  mp_get_buffer_raise(mnemonic, &text, MP_BUFFER_READ);
  return (text.len > 0 && mnemonic_check(text.buf)) ? mp_const_true
                                                    : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_bip39_check_obj,
                                 mod_trezorcrypto_bip39_check);

/// def seed(
///     mnemonic: str,
///     passphrase: str,
///     callback: Callable[[int, int], None] | None = None,
/// ) -> bytes:
///     """
///     Generate seed from mnemonic and passphrase.
///     """
STATIC mp_obj_t mod_trezorcrypto_bip39_seed(size_t n_args,
                                            const mp_obj_t *args) {
  mp_buffer_info_t mnemo = {0};
  mp_buffer_info_t phrase = {0};
  mp_get_buffer_raise(args[0], &mnemo, MP_BUFFER_READ);
  mp_get_buffer_raise(args[1], &phrase, MP_BUFFER_READ);
  vstr_t seed = {0};
  vstr_init_len(&seed, SHA512_DIGEST_LENGTH);
  const char *pmnemonic = mnemo.len > 0 ? mnemo.buf : "";
  const char *ppassphrase = phrase.len > 0 ? phrase.buf : "";
  if (n_args > 2) {
    // generate with a progress callback
    ui_wait_callback = args[2];
    mnemonic_to_seed(pmnemonic, ppassphrase, (uint8_t *)seed.buf,
                     wrapped_ui_wait_callback);
    ui_wait_callback = mp_const_none;
  } else {
    // generate without callback
    mnemonic_to_seed(pmnemonic, ppassphrase, (uint8_t *)seed.buf, NULL);
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &seed);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_bip39_seed_obj, 2,
                                           3, mod_trezorcrypto_bip39_seed);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_bip39_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_bip39)},
    {MP_ROM_QSTR(MP_QSTR_complete_word),
     MP_ROM_PTR(&mod_trezorcrypto_bip39_complete_word_obj)},
    {MP_ROM_QSTR(MP_QSTR_word_completion_mask),
     MP_ROM_PTR(&mod_trezorcrypto_bip39_word_completion_mask_obj)},
    {MP_ROM_QSTR(MP_QSTR_generate),
     MP_ROM_PTR(&mod_trezorcrypto_bip39_generate_obj)},
    {MP_ROM_QSTR(MP_QSTR_from_data),
     MP_ROM_PTR(&mod_trezorcrypto_bip39_from_data_obj)},
    {MP_ROM_QSTR(MP_QSTR_check), MP_ROM_PTR(&mod_trezorcrypto_bip39_check_obj)},
    {MP_ROM_QSTR(MP_QSTR_seed), MP_ROM_PTR(&mod_trezorcrypto_bip39_seed_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_bip39_globals,
                            mod_trezorcrypto_bip39_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_bip39_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_bip39_globals,
};
