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

#include "ed25519-donna/curve25519_sign.h"

/// package: trezorcrypto.curve25519_axolotl

/// def curve25519_axolotl_sign(secret_key: bytes, message: bytes, random: bytes) -> bytes:
///     """
///     Uses private key to sign the signature.
///     """
STATIC mp_obj_t mod_trezorcrypto_curve25519_axolotl_curve25519_axolotl_sign(size_t n_args,
                                                                            const mp_obj_t *args) {
  mp_buffer_info_t sk, msg, random;
  mp_get_buffer_raise(args[0], &sk, MP_BUFFER_READ);
  mp_get_buffer_raise(args[1], &msg, MP_BUFFER_READ);
  mp_get_buffer_raise(args[2], &random, MP_BUFFER_READ);
  if (sk.len != 32) {
    mp_raise_ValueError("Invalid length of secret key");
  }
  if (msg.len == 0) {
    mp_raise_ValueError("Empty data to sign");
  }
  if (random.len != 64) {
    mp_raise_ValueError("Invalid length of random (must be 64)");
  }

  uint8_t signature[64];
  curve25519_sign(signature, (const uint8_t *)sk.buf,
                  (const uint8_t *)msg.buf, msg.len, (const uint8_t *)random.buf);
  return mp_obj_new_bytes(signature, sizeof(signature));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_curve25519_axolotl_curve25519_axolotl_sign_obj, 3, 3,
    mod_trezorcrypto_curve25519_axolotl_curve25519_axolotl_sign);

/// def curve25519_axolotl_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
///     """
///     Uses public key to verify the signature
///     """
STATIC mp_obj_t mod_trezorcrypto_curve25519_axolotl_curve25519_axolotl_verify(size_t n_args,
                                                                              const mp_obj_t *args) {
  mp_buffer_info_t publickey, msg, signature;
  mp_get_buffer_raise(args[0], &publickey, MP_BUFFER_READ);
  mp_get_buffer_raise(args[1], &msg, MP_BUFFER_READ);
  mp_get_buffer_raise(args[2], &signature, MP_BUFFER_READ);
  if (publickey.len != 32) {
    return mp_const_false;
  }
  if (msg.len == 0) {
    return mp_const_false;
  }
  if (signature.len != 64) {
    return mp_const_false;
  }

  return (0 == curve25519_verify((const uint8_t *)signature.buf, (const uint8_t *)publickey.buf,
                                 (const uint8_t *)msg.buf, msg.len))
             ? mp_const_true
             : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_curve25519_axolotl_curve25519_axolotl_verify_obj, 3, 3,
    mod_trezorcrypto_curve25519_axolotl_curve25519_axolotl_verify);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_curve25519_axolotl_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_curve25519_axolotl)},
    {MP_ROM_QSTR(MP_QSTR_curve25519_axolotl_sign),
     MP_ROM_PTR(&mod_trezorcrypto_curve25519_axolotl_curve25519_axolotl_sign_obj)},
    {MP_ROM_QSTR(MP_QSTR_curve25519_axolotl_verify),
     MP_ROM_PTR(&mod_trezorcrypto_curve25519_axolotl_curve25519_axolotl_verify_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_curve25519_axolotl_globals,
                            mod_trezorcrypto_curve25519_axolotl_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_curve25519_axolotl_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_curve25519_axolotl_globals,
};
