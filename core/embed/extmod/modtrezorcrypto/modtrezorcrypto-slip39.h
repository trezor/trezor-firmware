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

/// def compute_mask(prefix: int) -> int:
///     """
///     Calculates which buttons still can be pressed after some already were.
///     Returns a 9-bit bitmask, where each bit specifies which buttons
///     can be further pressed (there are still words in this combination).
///     LSB denotes first button.
///
///     Example: 110000110 - second, third, eighth and ninth button still can be
///     pressed.
///     """
STATIC mp_obj_t mod_trezorcrypto_slip39_compute_mask(mp_obj_t _prefix) {
  uint16_t prefix = mp_obj_get_int(_prefix);

  if (prefix < 1 || prefix > 9999) {
    mp_raise_ValueError(
        "Invalid button prefix (range between 1 and 9999 is allowed)");
  }
  return mp_obj_new_int_from_uint(compute_mask(prefix));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_slip39_compute_mask_obj,
                                 mod_trezorcrypto_slip39_compute_mask);

/// def button_sequence_to_word(prefix: int) -> str:
///     """
///     Finds the first word that fits the given button prefix.
///     """
STATIC mp_obj_t
mod_trezorcrypto_slip39_button_sequence_to_word(mp_obj_t _prefix) {
  uint16_t prefix = mp_obj_get_int(_prefix);

  if (prefix < 1 || prefix > 9999) {
    mp_raise_ValueError(
        "Invalid button prefix (range between 1 and 9999 is allowed)");
  }
  const char *word = button_sequence_to_word(prefix);
  return mp_obj_new_str_copy(&mp_type_str, (const uint8_t *)word, strlen(word));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(
    mod_trezorcrypto_slip39_button_sequence_to_word_obj,
    mod_trezorcrypto_slip39_button_sequence_to_word);

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

  if (index > 1023) {
    mp_raise_ValueError(
        "Invalid wordlist index (range between 0 and 1024 is allowed)");
  }

  const char *word = get_word(index);
  return mp_obj_new_str_copy(&mp_type_str, (const uint8_t *)word, strlen(word));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_slip39_get_word_obj,
                                 mod_trezorcrypto_slip39_get_word);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_slip39_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_slip39)},
    {MP_ROM_QSTR(MP_QSTR_compute_mask),
     MP_ROM_PTR(&mod_trezorcrypto_slip39_compute_mask_obj)},
    {MP_ROM_QSTR(MP_QSTR_button_sequence_to_word),
     MP_ROM_PTR(&mod_trezorcrypto_slip39_button_sequence_to_word_obj)},
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
