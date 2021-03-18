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

#include "hmac.h"
#include "memzero.h"

#define SHA256 256
#define SHA512 512

/// package: trezorcrypto.__init__

/// class hmac:
///     """
///     HMAC context.
///     """
///     SHA256: int
///     SHA512: int
typedef struct _mp_obj_Hmac_t {
  mp_obj_base_t base;
  union {
    HMAC_SHA256_CTX ctx256;
    HMAC_SHA512_CTX ctx512;
  };
  uint32_t hashtype;
} mp_obj_Hmac_t;

STATIC mp_obj_t mod_trezorcrypto_Hmac_update(mp_obj_t self, mp_obj_t data);

/// def __init__(
///     self,
///     hashtype: int,
///     key: bytes,
///     message: bytes | None = None,
/// ) -> None:
///     """
///     Create a HMAC context.
///     """
STATIC mp_obj_t mod_trezorcrypto_Hmac_make_new(const mp_obj_type_t *type,
                                               size_t n_args, size_t n_kw,
                                               const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 2, 3, false);
  mp_obj_Hmac_t *o = m_new_obj_with_finaliser(mp_obj_Hmac_t);
  o->base.type = type;

  mp_buffer_info_t key = {0};
  mp_get_buffer_raise(args[1], &key, MP_BUFFER_READ);

  if (key.len == 0) {
    key.buf = "";
  }

  o->hashtype = trezor_obj_get_uint(args[0]);
  if (o->hashtype == SHA256) {
    hmac_sha256_Init(&(o->ctx256), key.buf, key.len);
  } else if (o->hashtype == SHA512) {
    hmac_sha512_Init(&(o->ctx512), key.buf, key.len);
  } else {
    mp_raise_ValueError("Invalid hashtype");
  }
  // constructor called with message as third parameter
  if (n_args > 2) {
    mod_trezorcrypto_Hmac_update(MP_OBJ_FROM_PTR(o), args[2]);
  }
  return MP_OBJ_FROM_PTR(o);
}

/// def update(self, message: bytes) -> None:
///     """
///     Update a HMAC context.
///     """
STATIC mp_obj_t mod_trezorcrypto_Hmac_update(mp_obj_t self, mp_obj_t message) {
  mp_obj_Hmac_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t msg = {0};
  mp_get_buffer_raise(message, &msg, MP_BUFFER_READ);
  if (o->hashtype == SHA256) {
    hmac_sha256_Update(&(o->ctx256), msg.buf, msg.len);
  } else if (o->hashtype == SHA512) {
    hmac_sha512_Update(&(o->ctx512), msg.buf, msg.len);
  } else {
    mp_raise_ValueError("Invalid hashtype");
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_Hmac_update_obj,
                                 mod_trezorcrypto_Hmac_update);

/// def digest(self) -> bytes:
///     """
///     Return the digest of processed data so far.
///     """
STATIC mp_obj_t mod_trezorcrypto_Hmac_digest(mp_obj_t self) {
  mp_obj_Hmac_t *o = MP_OBJ_TO_PTR(self);
  vstr_t mac = {0};
  if (o->hashtype == SHA256) {
    HMAC_SHA256_CTX ctx = {0};
    memcpy(&ctx, &(o->ctx256), sizeof(HMAC_SHA256_CTX));
    vstr_init_len(&mac, SHA256_DIGEST_LENGTH);
    hmac_sha256_Final(&ctx, (uint8_t *)mac.buf);
    memzero(&ctx, sizeof(HMAC_SHA256_CTX));
  } else if (o->hashtype == SHA512) {
    HMAC_SHA512_CTX ctx = {0};
    memcpy(&ctx, &(o->ctx512), sizeof(HMAC_SHA512_CTX));
    vstr_init_len(&mac, SHA512_DIGEST_LENGTH);
    hmac_sha512_Final(&ctx, (uint8_t *)mac.buf);
    memzero(&ctx, sizeof(HMAC_SHA512_CTX));
  } else {
    mp_raise_ValueError("Invalid hashtype");
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &mac);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_Hmac_digest_obj,
                                 mod_trezorcrypto_Hmac_digest);

STATIC mp_obj_t mod_trezorcrypto_Hmac___del__(mp_obj_t self) {
  mp_obj_Hmac_t *o = MP_OBJ_TO_PTR(self);
  memzero(&(o->ctx256), sizeof(HMAC_SHA256_CTX));
  memzero(&(o->ctx512), sizeof(HMAC_SHA512_CTX));
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_Hmac___del___obj,
                                 mod_trezorcrypto_Hmac___del__);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_Hmac_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_update),
     MP_ROM_PTR(&mod_trezorcrypto_Hmac_update_obj)},
    {MP_ROM_QSTR(MP_QSTR_digest),
     MP_ROM_PTR(&mod_trezorcrypto_Hmac_digest_obj)},
    {MP_ROM_QSTR(MP_QSTR___del__),
     MP_ROM_PTR(&mod_trezorcrypto_Hmac___del___obj)},
    {MP_ROM_QSTR(MP_QSTR_SHA256), MP_ROM_INT(SHA256)},
    {MP_ROM_QSTR(MP_QSTR_SHA512), MP_ROM_INT(SHA512)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_Hmac_locals_dict,
                            mod_trezorcrypto_Hmac_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorcrypto_Hmac_type = {
    {&mp_type_type},
    .name = MP_QSTR_Hmac,
    .make_new = mod_trezorcrypto_Hmac_make_new,
    .locals_dict = (void *)&mod_trezorcrypto_Hmac_locals_dict,
};
