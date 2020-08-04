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
#include "sha3.h"

/// package: trezorcrypto.__init__

/// class sha3_256:
///     """
///     SHA3_256 context.
///     """
///     block_size: int
///     digest_size: int
typedef struct _mp_obj_Sha3_256_t {
  mp_obj_base_t base;
  SHA3_CTX ctx;
  bool keccak;
} mp_obj_Sha3_256_t;

STATIC mp_obj_t mod_trezorcrypto_Sha3_256_update(mp_obj_t self, mp_obj_t data);

/// def __init__(self, data: bytes = None, keccak: bool = False) -> None:
///     """
///     Creates a hash context object.
///     """
STATIC mp_obj_t mod_trezorcrypto_Sha3_256_make_new(const mp_obj_type_t *type,
                                                   size_t n_args, size_t n_kw,
                                                   const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 0, 1, true);
  mp_obj_Sha3_256_t *o = m_new_obj_with_finaliser(mp_obj_Sha3_256_t);
  o->base.type = type;
  o->keccak = 0;
  sha3_256_Init(&(o->ctx));

  STATIC const mp_arg_t allowed_args[] = {
      {MP_QSTR_data, MP_ARG_OBJ, {.u_obj = mp_const_none}},
      {MP_QSTR_keccak, MP_ARG_OBJ | MP_ARG_KW_ONLY, {.u_obj = MP_OBJ_NULL}},
  };
  mp_arg_val_t vals[MP_ARRAY_SIZE(allowed_args)] = {0};
  mp_arg_parse_all_kw_array(n_args, n_kw, args, MP_ARRAY_SIZE(allowed_args),
                            allowed_args, vals);
  if (vals[1].u_obj != MP_OBJ_NULL) {
    o->keccak = mp_obj_is_true(vals[1].u_obj);
  }

  if (vals[0].u_obj != mp_const_none) {
    mod_trezorcrypto_Sha3_256_update(MP_OBJ_FROM_PTR(o), vals[0].u_obj);
  }
  return MP_OBJ_FROM_PTR(o);
}

/// def update(self, data: bytes) -> None:
///     """
///     Update the hash context with hashed data.
///     """
STATIC mp_obj_t mod_trezorcrypto_Sha3_256_update(mp_obj_t self, mp_obj_t data) {
  mp_obj_Sha3_256_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t msg = {0};
  mp_get_buffer_raise(data, &msg, MP_BUFFER_READ);
  if (msg.len > 0) {
    sha3_Update(&(o->ctx), msg.buf, msg.len);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_Sha3_256_update_obj,
                                 mod_trezorcrypto_Sha3_256_update);

/// def digest(self) -> bytes:
///     """
///     Returns the digest of hashed data.
///     """
STATIC mp_obj_t mod_trezorcrypto_Sha3_256_digest(mp_obj_t self) {
  mp_obj_Sha3_256_t *o = MP_OBJ_TO_PTR(self);
  uint8_t out[SHA3_256_DIGEST_LENGTH] = {0};
  SHA3_CTX ctx = {0};
  memcpy(&ctx, &(o->ctx), sizeof(SHA3_CTX));
  if (o->keccak) {
    keccak_Final(&ctx, out);
  } else {
    sha3_Final(&ctx, out);
  }
  memzero(&ctx, sizeof(SHA3_CTX));
  return mp_obj_new_bytes(out, sizeof(out));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_Sha3_256_digest_obj,
                                 mod_trezorcrypto_Sha3_256_digest);

/// def copy(self) -> sha3_256:
///     """
///     Returns the copy of the digest object with the current state
///     """
STATIC mp_obj_t mod_trezorcrypto_Sha3_256_copy(size_t n_args,
                                               const mp_obj_t *args) {
  mp_obj_Sha3_256_t *o = MP_OBJ_TO_PTR(args[0]);
  mp_obj_Sha3_256_t *out = m_new_obj_with_finaliser(mp_obj_Sha3_256_t);
  out->base.type = o->base.type;
  out->keccak = o->keccak;
  memcpy(&(out->ctx), &(o->ctx), sizeof(SHA3_CTX));
  return MP_OBJ_FROM_PTR(out);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_Sha3_256_copy_obj,
                                           1, 1,
                                           mod_trezorcrypto_Sha3_256_copy);

STATIC mp_obj_t mod_trezorcrypto_Sha3_256___del__(mp_obj_t self) {
  mp_obj_Sha3_256_t *o = MP_OBJ_TO_PTR(self);
  memzero(&(o->ctx), sizeof(SHA3_CTX));
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_Sha3_256___del___obj,
                                 mod_trezorcrypto_Sha3_256___del__);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_Sha3_256_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_update),
     MP_ROM_PTR(&mod_trezorcrypto_Sha3_256_update_obj)},
    {MP_ROM_QSTR(MP_QSTR_digest),
     MP_ROM_PTR(&mod_trezorcrypto_Sha3_256_digest_obj)},
    {MP_ROM_QSTR(MP_QSTR_copy),
     MP_ROM_PTR(&mod_trezorcrypto_Sha3_256_copy_obj)},
    {MP_ROM_QSTR(MP_QSTR___del__),
     MP_ROM_PTR(&mod_trezorcrypto_Sha3_256___del___obj)},
    {MP_ROM_QSTR(MP_QSTR_block_size), MP_ROM_INT(SHA3_256_BLOCK_LENGTH)},
    {MP_ROM_QSTR(MP_QSTR_digest_size), MP_ROM_INT(SHA3_256_DIGEST_LENGTH)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_Sha3_256_locals_dict,
                            mod_trezorcrypto_Sha3_256_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorcrypto_Sha3_256_type = {
    {&mp_type_type},
    .name = MP_QSTR_Sha3_256,
    .make_new = mod_trezorcrypto_Sha3_256_make_new,
    .locals_dict = (void *)&mod_trezorcrypto_Sha3_256_locals_dict,
};
