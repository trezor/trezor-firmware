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

#include "embed/extmod/trezorobj.h"

#include "rand.h"

#if USE_OPTIGA
#include "optiga.h"
#endif

/// package: trezorcrypto.random

/// def uniform(n: int) -> int:
///     """
///     Compute uniform random number from interval 0 ... n - 1.
///     """
STATIC mp_obj_t mod_trezorcrypto_random_uniform(mp_obj_t n) {
  uint32_t nn = trezor_obj_get_uint(n);
  if (nn == 0) {
    mp_raise_ValueError("Maximum can't be zero");
  }
  return mp_obj_new_int_from_uint(random_uniform(nn));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_random_uniform_obj,
                                 mod_trezorcrypto_random_uniform);

/// import builtins
/// def bytes(len: int, strong: bool = False) -> builtins.bytes:
///     """
///     Generate random bytes sequence of length len. If `strong` is set then
///     maximum sources of entropy are used.
///     """
STATIC mp_obj_t mod_trezorcrypto_random_bytes(size_t n_args,
                                              const mp_obj_t *args) {
  uint32_t len = trezor_obj_get_uint(args[0]);
  if (len > 1024) {
    mp_raise_ValueError("Maximum requested size is 1024");
  }
  vstr_t vstr = {0};
  vstr_init_len(&vstr, len);
#if USE_OPTIGA
  if (n_args > 1 && mp_obj_is_true(args[1])) {
    if (!optiga_random_buffer((uint8_t *)vstr.buf, len)) {
      vstr_clear(&vstr);
      mp_raise_msg(&mp_type_RuntimeError,
                   "Failed to get randomness from Optiga.");
    }

    random_xor((uint8_t *)vstr.buf, len);
  } else
#endif
  {
    random_buffer((uint8_t *)vstr.buf, len);
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_random_bytes_obj, 1,
                                           2, mod_trezorcrypto_random_bytes);

/// def shuffle(data: list) -> None:
///     """
///     Shuffles items of given list (in-place).
///     """
STATIC mp_obj_t mod_trezorcrypto_random_shuffle(mp_obj_t data) {
  size_t count = 0;
  mp_obj_t *items = NULL;
  mp_obj_get_array(data, &count, &items);
  if (count > 256) {
    mp_raise_ValueError("Maximum list size is 256 items");
  }
  if (count <= 1) {
    return mp_const_none;
  }
  // Fisher-Yates shuffle
  mp_obj_t t = 0;
  for (size_t i = count - 1; i >= 1; i--) {
    size_t j = random_uniform(i + 1);
    t = items[i];
    items[i] = items[j];
    items[j] = t;
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_random_shuffle_obj,
                                 mod_trezorcrypto_random_shuffle);

#ifdef TREZOR_EMULATOR
/// def reseed(value: int) -> None:
///     """
///     Re-seed the RNG with given value.
///     """
STATIC mp_obj_t mod_trezorcrypto_random_reseed(mp_obj_t data) {
  random_reseed(trezor_obj_get_uint(data));
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_random_reseed_obj,
                                 mod_trezorcrypto_random_reseed);
#endif

STATIC const mp_rom_map_elem_t mod_trezorcrypto_random_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_random)},
    {MP_ROM_QSTR(MP_QSTR_uniform),
     MP_ROM_PTR(&mod_trezorcrypto_random_uniform_obj)},
    {MP_ROM_QSTR(MP_QSTR_bytes),
     MP_ROM_PTR(&mod_trezorcrypto_random_bytes_obj)},
    {MP_ROM_QSTR(MP_QSTR_shuffle),
     MP_ROM_PTR(&mod_trezorcrypto_random_shuffle_obj)},
#ifdef TREZOR_EMULATOR
    {MP_ROM_QSTR(MP_QSTR_reseed),
     MP_ROM_PTR(&mod_trezorcrypto_random_reseed_obj)},
#endif
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_random_globals,
                            mod_trezorcrypto_random_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_random_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_random_globals,
};
