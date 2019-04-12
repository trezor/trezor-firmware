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
#include "py/objstr.h"

#include "embed/extmod/trezorobj.h"

#include "shamir.h"

#define MAX_SHARE_COUNT 32

/// def interpolate(shares, x) -> bytes:
///     '''
///     Returns f(x) given the Shamir shares (x_1, f(x_1)), ... , (x_k, f(x_k)).
///     :param shares: The Shamir shares.
///     :type shares: A list of pairs (x_i, y_i), where x_i is an integer and y_i is an array of
///         bytes representing the evaluations of the polynomials in x_i.
///     :param int x: The x coordinate of the result.
///     :return: Evaluations of the polynomials in x.
///     :rtype: Array of bytes.
///     '''
mp_obj_t mod_trezorcrypto_shamir_interpolate(mp_obj_t shares, mp_obj_t x) {
  size_t share_count;
  mp_obj_t *share_items;
  if (!MP_OBJ_IS_TYPE(shares, &mp_type_list)) {
    mp_raise_TypeError("Expected a list.");
  }
  mp_obj_list_get(shares, &share_count, &share_items);
  if (share_count < 1 || share_count > MAX_SHARE_COUNT) {
    mp_raise_ValueError("Invalid number of shares.");
  }
  uint8_t x_uint8 = trezor_obj_get_uint8(x);
  uint8_t share_indices[MAX_SHARE_COUNT];
  const uint8_t *share_values[MAX_SHARE_COUNT];
  size_t value_len = 0;
  for (int i = 0; i < share_count; ++i) {
    if (!MP_OBJ_IS_TYPE(share_items[i], &mp_type_tuple)) {
      mp_raise_TypeError("Expected a tuple.");
    }
    size_t tuple_len;
    mp_obj_t *share;
    mp_obj_tuple_get(share_items[i], &tuple_len, &share);
    if (tuple_len != 2) {
      mp_raise_ValueError("Expected a tuple of length 2.");
    }
    share_indices[i] = trezor_obj_get_uint8(share[0]);
    mp_buffer_info_t value;
    mp_get_buffer_raise(share[1], &value, MP_BUFFER_READ);
    if (value_len == 0) {
      value_len = value.len;
      if (value_len > SHAMIR_MAX_LEN) {
        mp_raise_ValueError("Share value exceeds maximum supported length.");
      }
    }
    if (value.len != value_len) {
      mp_raise_ValueError("All shares must have the same length.");
    }
    share_values[i] = value.buf;
  }
  vstr_t vstr;
  vstr_init_len(&vstr, value_len);
  shamir_interpolate((uint8_t*) vstr.buf, x_uint8, share_indices, share_values, share_count, value_len);
  vstr_cut_tail_bytes(&vstr, vstr_len(&vstr) - value_len);
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_shamir_interpolate_obj,
                                 mod_trezorcrypto_shamir_interpolate);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_shamir_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_shamir)},
    {MP_ROM_QSTR(MP_QSTR_interpolate), MP_ROM_PTR(&mod_trezorcrypto_shamir_interpolate_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_shamir_globals,
                            mod_trezorcrypto_shamir_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_shamir_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_shamir_globals,
};
