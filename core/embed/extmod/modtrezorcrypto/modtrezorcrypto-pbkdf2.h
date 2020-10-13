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

#include "memzero.h"
#include "pbkdf2.h"

#define PRF_HMAC_SHA256 256
#define PRF_HMAC_SHA512 512

/// package: trezorcrypto.__init__

/// class pbkdf2:
///     """
///     PBKDF2 context.
///     """
///     HMAC_SHA256: int
///     HMAC_SHA512: int
typedef struct _mp_obj_Pbkdf2_t {
  mp_obj_base_t base;
  union {
    PBKDF2_HMAC_SHA256_CTX ctx256;
    PBKDF2_HMAC_SHA512_CTX ctx512;
  };
  uint32_t prf;
} mp_obj_Pbkdf2_t;

STATIC mp_obj_t mod_trezorcrypto_Pbkdf2_update(mp_obj_t self, mp_obj_t data);

/// def __init__(
///     self,
///     prf: int,
///     password: bytes,
///     salt: bytes,
///     iterations: int = None,
///     blocknr: int = 1,
/// ) -> None:
///     """
///     Create a PBKDF2 context.
///     """
STATIC mp_obj_t mod_trezorcrypto_Pbkdf2_make_new(const mp_obj_type_t *type,
                                                 size_t n_args, size_t n_kw,
                                                 const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 3, 4, false);
  mp_obj_Pbkdf2_t *o = m_new_obj_with_finaliser(mp_obj_Pbkdf2_t);
  o->base.type = type;

  mp_buffer_info_t password = {0};
  mp_get_buffer_raise(args[1], &password, MP_BUFFER_READ);
  mp_buffer_info_t salt = {0};
  mp_get_buffer_raise(args[2], &salt, MP_BUFFER_READ);

  if (password.len == 0) {
    password.buf = "";
  }
  if (salt.len == 0) {
    salt.buf = "";
  }

  uint32_t blocknr = 1;
  if (n_args > 4) {  // blocknr is set
    blocknr = trezor_obj_get_uint(args[4]);
  }

  o->prf = trezor_obj_get_uint(args[0]);
  if (o->prf == PRF_HMAC_SHA256) {
    pbkdf2_hmac_sha256_Init(&(o->ctx256), password.buf, password.len, salt.buf,
                            salt.len, blocknr);
  } else if (o->prf == PRF_HMAC_SHA512) {
    pbkdf2_hmac_sha512_Init(&(o->ctx512), password.buf, password.len, salt.buf,
                            salt.len, blocknr);
  } else {
    mp_raise_ValueError("Invalid PRF");
  }
  // constructor called with iterations as fourth parameter
  if (n_args > 3) {
    mod_trezorcrypto_Pbkdf2_update(MP_OBJ_FROM_PTR(o), args[3]);
  }
  return MP_OBJ_FROM_PTR(o);
}

/// def update(self, iterations: int) -> None:
///     """
///     Update a PBKDF2 context.
///     """
STATIC mp_obj_t mod_trezorcrypto_Pbkdf2_update(mp_obj_t self,
                                               mp_obj_t iterations) {
  mp_obj_Pbkdf2_t *o = MP_OBJ_TO_PTR(self);
  uint32_t iter = trezor_obj_get_uint(iterations);
  if (o->prf == PRF_HMAC_SHA256) {
    pbkdf2_hmac_sha256_Update(&(o->ctx256), iter);
  } else if (o->prf == PRF_HMAC_SHA512) {
    pbkdf2_hmac_sha512_Update(&(o->ctx512), iter);
  } else {
    mp_raise_ValueError("Invalid PRF");
  }

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_Pbkdf2_update_obj,
                                 mod_trezorcrypto_Pbkdf2_update);

/// def key(self) -> bytes:
///     """
///     Retrieve derived key.
///     """
STATIC mp_obj_t mod_trezorcrypto_Pbkdf2_key(mp_obj_t self) {
  mp_obj_Pbkdf2_t *o = MP_OBJ_TO_PTR(self);
  vstr_t out = {0};
  if (o->prf == PRF_HMAC_SHA256) {
    PBKDF2_HMAC_SHA256_CTX ctx = {0};
    memcpy(&ctx, &(o->ctx256), sizeof(PBKDF2_HMAC_SHA256_CTX));
    vstr_init_len(&out, SHA256_DIGEST_LENGTH);
    pbkdf2_hmac_sha256_Final(&ctx, (uint8_t *)out.buf);
    memzero(&ctx, sizeof(PBKDF2_HMAC_SHA256_CTX));
  } else if (o->prf == PRF_HMAC_SHA512) {
    PBKDF2_HMAC_SHA512_CTX ctx = {0};
    memcpy(&ctx, &(o->ctx512), sizeof(PBKDF2_HMAC_SHA512_CTX));
    vstr_init_len(&out, SHA512_DIGEST_LENGTH);
    pbkdf2_hmac_sha512_Final(&ctx, (uint8_t *)out.buf);
    memzero(&ctx, sizeof(PBKDF2_HMAC_SHA512_CTX));
  } else {
    mp_raise_ValueError("Invalid PRF");
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &out);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_Pbkdf2_key_obj,
                                 mod_trezorcrypto_Pbkdf2_key);

STATIC mp_obj_t mod_trezorcrypto_Pbkdf2___del__(mp_obj_t self) {
  mp_obj_Pbkdf2_t *o = MP_OBJ_TO_PTR(self);
  memzero(&(o->ctx256), sizeof(PBKDF2_HMAC_SHA256_CTX));
  memzero(&(o->ctx512), sizeof(PBKDF2_HMAC_SHA512_CTX));
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_Pbkdf2___del___obj,
                                 mod_trezorcrypto_Pbkdf2___del__);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_Pbkdf2_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_update),
     MP_ROM_PTR(&mod_trezorcrypto_Pbkdf2_update_obj)},
    {MP_ROM_QSTR(MP_QSTR_key), MP_ROM_PTR(&mod_trezorcrypto_Pbkdf2_key_obj)},
    {MP_ROM_QSTR(MP_QSTR___del__),
     MP_ROM_PTR(&mod_trezorcrypto_Pbkdf2___del___obj)},
    {MP_ROM_QSTR(MP_QSTR_HMAC_SHA256), MP_ROM_INT(PRF_HMAC_SHA256)},
    {MP_ROM_QSTR(MP_QSTR_HMAC_SHA512), MP_ROM_INT(PRF_HMAC_SHA512)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_Pbkdf2_locals_dict,
                            mod_trezorcrypto_Pbkdf2_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorcrypto_Pbkdf2_type = {
    {&mp_type_type},
    .name = MP_QSTR_Pbkdf2,
    .make_new = mod_trezorcrypto_Pbkdf2_make_new,
    .locals_dict = (void *)&mod_trezorcrypto_Pbkdf2_locals_dict,
};
