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

#include "embed/upymod/trezorobj.h"
#include "py/objstr.h"

#include "segwit_addr.h"

/// package: trezorcrypto.bech32

/// def decode(
///     bech: str,
///     max_bech_len: int = 90,
/// ) -> tuple[str, list[int], Encoding]:
///     """
///     Decode a Bech32 or Bech32m string
///     """
STATIC mp_obj_t mod_trezorcrypto_bech32_decode(size_t n_args,
                                               const mp_obj_t *args) {
  mp_buffer_info_t bech = {0};
  mp_get_buffer_raise(args[0], &bech, MP_BUFFER_READ);

  uint32_t max_bech_len = 90;
  if (n_args > 1) {
    max_bech_len = trezor_obj_get_uint(args[1]);
  }

  if (bech.len > max_bech_len) {
    mp_raise_ValueError(NULL);
  }

  if (bech.len < 8) {
    mp_raise_ValueError(NULL);
  }

  uint8_t data[bech.len - 8];
  char hrp[BECH32_MAX_HRP_LEN + 1] = {0};
  size_t data_len = 0;
  bech32_encoding enc = bech32_decode(hrp, data, &data_len, bech.buf);
  if (enc == BECH32_ENCODING_NONE) {
    mp_raise_ValueError(NULL);
  }

  mp_obj_list_t *data_list = MP_OBJ_TO_PTR(mp_obj_new_list(data_len, NULL));
  for (size_t i = 0; i < data_len; ++i) {
    data_list->items[i] = mp_obj_new_int_from_uint(data[i]);
  }

  mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(3, NULL));
  tuple->items[0] = mp_obj_new_str(hrp, strlen(hrp));
  tuple->items[1] = data_list;
  tuple->items[2] = MP_OBJ_NEW_SMALL_INT(enc);
  return MP_OBJ_FROM_PTR(tuple);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_bech32_decode_obj,
                                           1, 2,
                                           mod_trezorcrypto_bech32_decode);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_bech32_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_bech32)},
    {MP_ROM_QSTR(MP_QSTR_decode),
     MP_ROM_PTR(&mod_trezorcrypto_bech32_decode_obj)},
    {MP_ROM_QSTR(MP_QSTR_BECH32), MP_ROM_INT(BECH32_ENCODING_BECH32)},
    {MP_ROM_QSTR(MP_QSTR_BECH32M), MP_ROM_INT(BECH32_ENCODING_BECH32M)}};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_bech32_globals,
                            mod_trezorcrypto_bech32_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_bech32_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_bech32_globals,
};
