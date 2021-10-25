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

#include "zkp_bip340.h"

/// package: trezorcrypto.bip340

/// def generate_secret() -> bytes:
///     """
///     Generate secret key.
///     """
STATIC mp_obj_t mod_trezorcrypt_bip340_generate_secret() {
  vstr_t sk = {0};
  vstr_init_len(&sk, 32);
  for (;;) {
    random_buffer((uint8_t *)sk.buf, sk.len);
    // check whether secret > 0 && secret < curve_order
    if (0 ==
        memcmp(
            sk.buf,
            "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
            "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00",
            32))
      continue;
    if (0 <=
        memcmp(
            sk.buf,
            "\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFE"
            "\xBA\xAE\xDC\xE6\xAF\x48\xA0\x3B\xBF\xD2\x5E\x8C\xD0\x36\x41\x41",
            32))
      continue;
    break;
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &sk);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorcrypt_bip340_generate_secret_obj,
                                 mod_trezorcrypt_bip340_generate_secret);

/// def publickey(secret_key: bytes) -> bytes:
///     """
///     Computes public key from secret key.
///     """
STATIC mp_obj_t mod_trezorcrypt_bip340_publickey(mp_obj_t secret_key) {
  mp_buffer_info_t sk = {0};
  mp_get_buffer_raise(secret_key, &sk, MP_BUFFER_READ);
  if (sk.len != 32) {
    mp_raise_ValueError("Invalid length of secret key");
  }
  vstr_t pk = {0};
  vstr_init_len(&pk, 32);
  int ret =
      zkp_bip340_get_public_key((const uint8_t *)sk.buf, (uint8_t *)pk.buf);
  if (0 != ret) {
    vstr_clear(&pk);
    mp_raise_ValueError("Invalid secret key");
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &pk);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypt_bip340_publickey_obj,
                                 mod_trezorcrypt_bip340_publickey);

/// def sign(
///     secret_key: bytes,
///     digest: bytes,
/// ) -> bytes:
///     """
///     Uses secret key to produce the signature of the digest.
///     """
STATIC mp_obj_t mod_trezorcrypt_bip340_sign(mp_obj_t secret_key,
                                            mp_obj_t digest) {
  mp_buffer_info_t sk = {0}, dig = {0};
  mp_get_buffer_raise(secret_key, &sk, MP_BUFFER_READ);
  mp_get_buffer_raise(digest, &dig, MP_BUFFER_READ);
  if (sk.len != 32) {
    mp_raise_ValueError("Invalid length of secret key");
  }
  if (dig.len != 32) {
    mp_raise_ValueError("Invalid length of digest");
  }

  vstr_t sig = {0};
  vstr_init_len(&sig, 64);
  int ret =
      zkp_bip340_sign_digest((const uint8_t *)sk.buf, (const uint8_t *)dig.buf,
                             (uint8_t *)sig.buf, NULL);
  if (0 != ret) {
    vstr_clear(&sig);
    mp_raise_ValueError("Signing failed");
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &sig);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypt_bip340_sign_obj,
                                 mod_trezorcrypt_bip340_sign);

/// def verify(public_key: bytes, signature: bytes, digest: bytes) -> bool:
///     """
///     Uses public key to verify the signature of the digest.
///     Returns True on success.
///     """
STATIC mp_obj_t mod_trezorcrypt_bip340_verify(mp_obj_t public_key,
                                              mp_obj_t signature,
                                              mp_obj_t digest) {
  mp_buffer_info_t pk = {0}, sig = {0}, dig = {0};
  mp_get_buffer_raise(public_key, &pk, MP_BUFFER_READ);
  mp_get_buffer_raise(signature, &sig, MP_BUFFER_READ);
  mp_get_buffer_raise(digest, &dig, MP_BUFFER_READ);
  if (pk.len != 32) {
    return mp_const_false;
  }
  if (sig.len != 64) {
    return mp_const_false;
  }
  if (dig.len != 32) {
    return mp_const_false;
  }
  int ret = zkp_bip340_verify_digest((const uint8_t *)pk.buf,
                                     (const uint8_t *)sig.buf,
                                     (const uint8_t *)dig.buf);
  return mp_obj_new_bool(ret == 0);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorcrypt_bip340_verify_obj,
                                 mod_trezorcrypt_bip340_verify);

/// def tweak_public_key(
///     public_key: bytes,
///     root_hash: bytes | None = None,
/// ) -> bytes:
///     """
///     Tweaks the public key with the specified root_hash.
///     """
STATIC mp_obj_t mod_trezorcrypt_bip340_tweak_public_key(size_t n_args,
                                                        const mp_obj_t *args) {
  mp_buffer_info_t pk = {0};
  mp_get_buffer_raise(args[0], &pk, MP_BUFFER_READ);
  if (pk.len != 32) {
    mp_raise_ValueError("Invalid length of public key");
  }

  mp_buffer_info_t rh = {0};
  const uint8_t *rh_ptr = NULL;
  if (n_args > 1 && args[1] != mp_const_none) {
    mp_get_buffer_raise(args[1], &rh, MP_BUFFER_READ);
    if (rh.len != 32) {
      mp_raise_ValueError("Invalid length of root hash");
    }
    rh_ptr = (const uint8_t *)rh.buf;
  }

  vstr_t tpk = {0};
  vstr_init_len(&tpk, 32);
  int ret = zkp_bip340_tweak_public_key((const uint8_t *)pk.buf, rh_ptr,
                                        (uint8_t *)tpk.buf);
  if (ret != 0) {
    vstr_clear(&tpk);
    mp_raise_ValueError("Failed to tweak public key");
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &tpk);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypt_bip340_tweak_public_key_obj, 1, 2,
    mod_trezorcrypt_bip340_tweak_public_key);

/// def tweak_secret_key(
///     secret_key: bytes,
///     root_hash: bytes | None = None,
/// ) -> bytes:
///     """
///     Tweaks the secret key with the specified root_hash.
///     """
STATIC mp_obj_t mod_trezorcrypt_bip340_tweak_secret_key(size_t n_args,
                                                        const mp_obj_t *args) {
  mp_buffer_info_t sk = {0};
  mp_get_buffer_raise(args[0], &sk, MP_BUFFER_READ);
  if (sk.len != 32) {
    mp_raise_ValueError("Invalid length of secret key");
  }

  mp_buffer_info_t rh = {0};
  const uint8_t *rh_ptr = NULL;
  if (n_args > 1 && args[1] != mp_const_none) {
    mp_get_buffer_raise(args[1], &rh, MP_BUFFER_READ);
    if (rh.len != 32) {
      mp_raise_ValueError("Invalid length of root hash");
    }
    rh_ptr = (const uint8_t *)rh.buf;
  }

  vstr_t tsk = {0};
  vstr_init_len(&tsk, 32);
  int ret = zkp_bip340_tweak_private_key((const uint8_t *)sk.buf, rh_ptr,
                                         (uint8_t *)tsk.buf);
  if (ret != 0) {
    vstr_clear(&tsk);
    mp_raise_ValueError("Failed to tweak secret key");
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &tsk);
}

STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypt_bip340_tweak_secret_key_obj, 1, 2,
    mod_trezorcrypt_bip340_tweak_secret_key);

STATIC const mp_rom_map_elem_t mod_trezorcrypt_bip340_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_bip340)},
    {MP_ROM_QSTR(MP_QSTR_generate_secret),
     MP_ROM_PTR(&mod_trezorcrypt_bip340_generate_secret_obj)},
    {MP_ROM_QSTR(MP_QSTR_publickey),
     MP_ROM_PTR(&mod_trezorcrypt_bip340_publickey_obj)},
    {MP_ROM_QSTR(MP_QSTR_sign), MP_ROM_PTR(&mod_trezorcrypt_bip340_sign_obj)},
    {MP_ROM_QSTR(MP_QSTR_verify),
     MP_ROM_PTR(&mod_trezorcrypt_bip340_verify_obj)},
    {MP_ROM_QSTR(MP_QSTR_tweak_public_key),
     MP_ROM_PTR(&mod_trezorcrypt_bip340_tweak_public_key_obj)},
    {MP_ROM_QSTR(MP_QSTR_tweak_secret_key),
     MP_ROM_PTR(&mod_trezorcrypt_bip340_tweak_secret_key_obj)}};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypt_bip340_globals,
                            mod_trezorcrypt_bip340_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypt_bip340_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypt_bip340_globals,
};
