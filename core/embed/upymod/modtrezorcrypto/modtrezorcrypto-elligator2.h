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

#include "embed/upymod/trezorobj.h"

#include "elligator2.h"

/// package: trezorcrypto.elligator2

/// def map_to_curve25519(input: bytes) -> bytes:
///     """
///     Maps a 32-byte input to a curve25519 point.
///     """
mp_obj_t mod_trezorcrypto_elligator2_map_to_curve25519(mp_obj_t input) {
  mp_buffer_info_t input_buffer_info = {0};
  mp_get_buffer_raise(input, &input_buffer_info, MP_BUFFER_READ);
  if (input_buffer_info.len != 32) {
    mp_raise_ValueError("Invalid input length");
  }

  vstr_t output_vstr = {0};
  vstr_init_len(&output_vstr, 32);
  int res = map_to_curve_elligator2_curve25519(input_buffer_info.buf,
                                               (uint8_t *)output_vstr.buf);
  if (res != true) {
    mp_raise_ValueError(NULL);
  }

  return mp_obj_new_str_from_vstr(&mp_type_bytes, &output_vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(
    mod_trezorcrypto_elligator2_map_to_curve25519_obj,
    mod_trezorcrypto_elligator2_map_to_curve25519);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_elligator2_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_elligator2)},
    {MP_ROM_QSTR(MP_QSTR_map_to_curve25519),
     MP_ROM_PTR(&mod_trezorcrypto_elligator2_map_to_curve25519_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_elligator2_globals,
                            mod_trezorcrypto_elligator2_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_elligator2_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_elligator2_globals,
};
