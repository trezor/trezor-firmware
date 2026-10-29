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

#if USE_SECP256K1_ZKP

#include <sys/rng.h>

#include "py/objstr.h"

#include "zkp_bip340.h"

/// package: trezorcrypto.bip340
/// from trezorcrypto import secbytes

/// def generate_secret() -> secbytes:
///     """Generate a private key in the kernel; return an opaque value."""
static mp_obj_t mod_trezorcrypto_bip340_generate_secret() {
  mp_obj_secbytes_t *value = secbytes_new(32);
  vault_request_t r = {.op = VAULT_SCHNORR_GENERATE};
  vault_response_t out = {0};
  vault_raise(&r, &out);
  secbytes_set_blob(value, &out.blob);
  return MP_OBJ_FROM_PTR(value);
}
static MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorcrypto_bip340_generate_secret_obj,
                                 mod_trezorcrypto_bip340_generate_secret);

static vault_blob_t bip340_key_blob(mp_obj_t key) {
  if (!mp_obj_is_type(key, &mod_trezorcrypto_secbytes_type)) {
    mp_buffer_info_t b = {0};
    mp_get_buffer_raise(key, &b, MP_BUFFER_READ);
    if (b.len != 32)
      mp_raise_ValueError(MP_ERROR_TEXT("Invalid length of secret key"));
    key = secbytes_copy(b.buf, b.len);
  }
  return secbytes_blob(MP_OBJ_TO_PTR(key));
}

/// def publickey(secret_key: AnyBytes | secbytes) -> bytes:
///     """Compute the public key without exporting private material."""
static mp_obj_t mod_trezorcrypto_bip340_publickey(mp_obj_t secret_key) {
  vault_request_t r = {.op = VAULT_SCHNORR_PUBLIC,
                       .blob = bip340_key_blob(secret_key)};
  vault_response_t out = {0};
  vault_raise(&r, &out);
  return mp_obj_new_bytes(out.signature, 32);
}

static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_bip340_publickey_obj,
                                 mod_trezorcrypto_bip340_publickey);

/// def sign(secret_key: AnyBytes | secbytes, digest: AnyBytes) -> bytes:
///     """Sign in the kernel; return only the public signature."""
static mp_obj_t mod_trezorcrypto_bip340_sign(mp_obj_t secret_key,
                                             mp_obj_t digest) {
  mp_buffer_info_t dig = {0};
  mp_get_buffer_raise(digest, &dig, MP_BUFFER_READ);
  if (dig.len != 32)
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid length of digest"));
  vault_request_t r = {.op = VAULT_SCHNORR_SIGN,
                       .blob = bip340_key_blob(secret_key),
                       .length = 32};
  vault_response_t out = {0};
  memcpy(r.data, dig.buf, 32);
  vault_raise(&r, &out);
  return mp_obj_new_bytes(out.signature, 64);
}

static MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_bip340_sign_obj,
                                 mod_trezorcrypto_bip340_sign);

/// def verify_publickey(public_key: AnyBytes) -> bool:
///     """
///     Verifies whether the public key is valid.
///     Returns True on success.
///     """
static mp_obj_t mod_trezorcrypto_bip340_verify_publickey(mp_obj_t public_key) {
  mp_buffer_info_t pk = {0};
  mp_get_buffer_raise(public_key, &pk, MP_BUFFER_READ);
  if (pk.len != 32) {
    return mp_const_false;
  }
  int ret = zkp_bip340_verify_publickey((const uint8_t *)pk.buf);
  return mp_obj_new_bool(ret == 0);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_bip340_verify_publickey_obj,
                                 mod_trezorcrypto_bip340_verify_publickey);

/// def verify(
///     public_key: AnyBytes, signature: AnyBytes, digest: AnyBytes
/// ) -> bool:
///     """
///     Uses public key to verify the signature of the digest.
///     Returns True on success.
///     """
static mp_obj_t mod_trezorcrypto_bip340_verify(mp_obj_t public_key,
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
static MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorcrypto_bip340_verify_obj,
                                 mod_trezorcrypto_bip340_verify);

/// def tweak_public_key(
///     public_key: AnyBytes,
///     root_hash: AnyBytes | None = None,
/// ) -> bytes:
///     """
///     Tweaks the public key with the specified root_hash.
///     """
static mp_obj_t mod_trezorcrypto_bip340_tweak_public_key(size_t n_args,
                                                         const mp_obj_t *args) {
  mp_buffer_info_t pk = {0};
  mp_get_buffer_raise(args[0], &pk, MP_BUFFER_READ);
  if (pk.len != 32) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid length of public key"));
  }

  mp_buffer_info_t rh = {0};
  const uint8_t *rh_ptr = NULL;
  if (n_args > 1 && args[1] != mp_const_none) {
    mp_get_buffer_raise(args[1], &rh, MP_BUFFER_READ);
    if (rh.len != 32) {
      mp_raise_ValueError(MP_ERROR_TEXT("Invalid length of root hash"));
    }
    rh_ptr = (const uint8_t *)rh.buf;
  }

  vstr_t tpk = {0};
  vstr_init_len(&tpk, 32);
  int ret = zkp_bip340_tweak_public_key((const uint8_t *)pk.buf, rh_ptr,
                                        (uint8_t *)tpk.buf);
  if (ret != 0) {
    vstr_clear(&tpk);
    mp_raise_ValueError(MP_ERROR_TEXT("Failed to tweak public key"));
  }
  return mp_obj_new_bytes_from_vstr(&tpk);
}

static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_bip340_tweak_public_key_obj, 1, 2,
    mod_trezorcrypto_bip340_tweak_public_key);

/// def tweak_secret_key(
///     secret_key: AnyBytes | secbytes,
///     root_hash: AnyBytes | None = None,
/// ) -> secbytes:
///     """Return an independent opaque snapshot of the tweaked key."""
static mp_obj_t mod_trezorcrypto_bip340_tweak_secret_key(size_t n_args,
                                                         const mp_obj_t *args) {
  mp_buffer_info_t root = {0};
  if (n_args > 1 && args[1] != mp_const_none) {
    mp_get_buffer_raise(args[1], &root, MP_BUFFER_READ);
    if (root.len != 32)
      mp_raise_ValueError(MP_ERROR_TEXT("Invalid length of root hash"));
  }
  mp_obj_secbytes_t *value = secbytes_new(32);
  vault_request_t r = {.op = VAULT_SCHNORR_TWEAK,
                       .blob = bip340_key_blob(args[0]),
                       .length = root.len};
  vault_response_t out = {0};
  if (root.len) memcpy(r.data, root.buf, root.len);
  vault_raise(&r, &out);
  secbytes_set_blob(value, &out.blob);
  return MP_OBJ_FROM_PTR(value);
}

static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_bip340_tweak_secret_key_obj, 1, 2,
    mod_trezorcrypto_bip340_tweak_secret_key);

static const mp_rom_map_elem_t mod_trezorcrypto_bip340_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_bip340)},
    {MP_ROM_QSTR(MP_QSTR_generate_secret),
     MP_ROM_PTR(&mod_trezorcrypto_bip340_generate_secret_obj)},
    {MP_ROM_QSTR(MP_QSTR_publickey),
     MP_ROM_PTR(&mod_trezorcrypto_bip340_publickey_obj)},
    {MP_ROM_QSTR(MP_QSTR_sign), MP_ROM_PTR(&mod_trezorcrypto_bip340_sign_obj)},
    {MP_ROM_QSTR(MP_QSTR_verify_publickey),
     MP_ROM_PTR(&mod_trezorcrypto_bip340_verify_publickey_obj)},
    {MP_ROM_QSTR(MP_QSTR_verify),
     MP_ROM_PTR(&mod_trezorcrypto_bip340_verify_obj)},
    {MP_ROM_QSTR(MP_QSTR_tweak_public_key),
     MP_ROM_PTR(&mod_trezorcrypto_bip340_tweak_public_key_obj)},
    {MP_ROM_QSTR(MP_QSTR_tweak_secret_key),
     MP_ROM_PTR(&mod_trezorcrypto_bip340_tweak_secret_key_obj)}};
static MP_DEFINE_CONST_DICT(mod_trezorcrypto_bip340_globals,
                            mod_trezorcrypto_bip340_globals_table);

static const mp_obj_module_t mod_trezorcrypto_bip340_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_bip340_globals,
};

#endif
