/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include "py/obj.h"
#include "py/runtime.h"

#include "slip39.h"

/// package: trezorcrypto.slip39

/// def word_index(word: str) -> int:
///     """
///     Finds index of given word.
///     Raises ValueError if not found.
///     """
STATIC mp_obj_t mod_trezorcrypto_slip39_word_index(mp_obj_t _word) {
  mp_buffer_info_t word = {0};

  mp_get_buffer_raise(_word, &word, MP_BUFFER_READ);

  uint16_t result = 0;
  if (word_index(&result, word.buf, word.len) == false) {
    mp_raise_ValueError("Invalid mnemonic word");
  }
  return mp_obj_new_int_from_uint(result);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_slip39_word_index_obj,
                                 mod_trezorcrypto_slip39_word_index);

/// def get_word(index: int) -> str:
///     """
///     Returns word on position 'index'.
///     """
STATIC mp_obj_t mod_trezorcrypto_slip39_get_word(mp_obj_t _index) {
  uint16_t index = mp_obj_get_int(_index);

  const char *word = get_word(index);
  if (word == NULL) {
    mp_raise_ValueError(
        "Invalid wordlist index (range between 0 and 1023 is allowed)");
  }

  return mp_obj_new_str_copy(&mp_type_str, (const uint8_t *)word, strlen(word));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_slip39_get_word_obj,
                                 mod_trezorcrypto_slip39_get_word);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_slip39_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_slip39)},
    {MP_ROM_QSTR(MP_QSTR_word_index),
     MP_ROM_PTR(&mod_trezorcrypto_slip39_word_index_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_word),
     MP_ROM_PTR(&mod_trezorcrypto_slip39_get_word_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_slip39_globals,
                            mod_trezorcrypto_slip39_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_slip39_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_slip39_globals,
};
