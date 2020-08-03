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

#include "py/obj.h"

#include "embed/extmod/trezorobj.h"

#include "shamir.h"

#define SHAMIR_MAX_SHARE_COUNT 16

/// package: trezorcrypto.shamir

/// def interpolate(shares: List[Tuple[int, bytes]], x: int) -> bytes:
///     """
///     Returns f(x) given the Shamir shares (x_1, f(x_1)), ... , (x_k, f(x_k)).
///     :param shares: The Shamir shares.
///     :type shares: A list of pairs (x_i, y_i), where x_i is an integer and
///         y_i is an array of bytes representing the evaluations of the
///         polynomials in x_i.
///     :param int x: The x coordinate of the result.
///     :return: Evaluations of the polynomials in x.
///     :rtype: Array of bytes.
///     """
mp_obj_t mod_trezorcrypto_shamir_interpolate(mp_obj_t shares, mp_obj_t x) {
  size_t share_count = 0;
  mp_obj_t *share_items = NULL;
  mp_obj_get_array(shares, &share_count, &share_items);
  if (share_count < 1 || share_count > SHAMIR_MAX_SHARE_COUNT) {
    mp_raise_ValueError("Invalid number of shares.");
  }
  uint8_t x_uint8 = trezor_obj_get_uint8(x);
  uint8_t share_indices[SHAMIR_MAX_SHARE_COUNT] = {0};
  const uint8_t *share_values[SHAMIR_MAX_SHARE_COUNT] = {0};
  size_t value_len = 0;
  for (int i = 0; i < share_count; ++i) {
    mp_obj_t *share = NULL;
    mp_obj_get_array_fixed_n(share_items[i], 2, &share);
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
  vstr_t vstr = {0};
  vstr_init_len(&vstr, value_len);
  if (shamir_interpolate((uint8_t *)vstr.buf, x_uint8, share_indices,
                         share_values, share_count, value_len) != true) {
    vstr_clear(&vstr);
    mp_raise_ValueError("Share indices must be pairwise distinct.");
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_shamir_interpolate_obj,
                                 mod_trezorcrypto_shamir_interpolate);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_shamir_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_shamir)},
    {MP_ROM_QSTR(MP_QSTR_interpolate),
     MP_ROM_PTR(&mod_trezorcrypto_shamir_interpolate_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_shamir_globals,
                            mod_trezorcrypto_shamir_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_shamir_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_shamir_globals,
};
