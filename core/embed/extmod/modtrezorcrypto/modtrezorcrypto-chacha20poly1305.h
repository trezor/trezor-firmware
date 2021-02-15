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

#include "chacha20poly1305/rfc7539.h"
#include "memzero.h"

/// package: trezorcrypto.__init__

/// class chacha20poly1305:
///     """
///     ChaCha20Poly1305 context.
///     """
typedef struct _mp_obj_ChaCha20Poly1305_t {
  mp_obj_base_t base;
  chacha20poly1305_ctx ctx;
  int64_t alen, plen;
} mp_obj_ChaCha20Poly1305_t;

/// def __init__(self, key: bytes, nonce: bytes) -> None:
///     """
///     Initialize the ChaCha20 + Poly1305 context for encryption or decryption
///     using a 32 byte key and 12 byte nonce as in the RFC 7539 style.
///     """
STATIC mp_obj_t mod_trezorcrypto_ChaCha20Poly1305_make_new(
    const mp_obj_type_t *type, size_t n_args, size_t n_kw,
    const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 2, 2, false);
  mp_obj_ChaCha20Poly1305_t *o =
      m_new_obj_with_finaliser(mp_obj_ChaCha20Poly1305_t);
  o->base.type = type;
  mp_buffer_info_t key = {0}, nonce = {0};
  mp_get_buffer_raise(args[0], &key, MP_BUFFER_READ);
  mp_get_buffer_raise(args[1], &nonce, MP_BUFFER_READ);
  if (key.len != 32) {
    mp_raise_ValueError("Invalid length of key");
  }
  if (nonce.len != 12) {
    mp_raise_ValueError("Invalid length of nonce");
  }
  rfc7539_init(&(o->ctx), key.buf, nonce.buf);
  o->alen = 0;
  o->plen = 0;
  return MP_OBJ_FROM_PTR(o);
}

/// def encrypt(self, data: bytes) -> bytes:
///     """
///     Encrypt data (length of data must be divisible by 64 except for the
///     final value).
///     """
STATIC mp_obj_t mod_trezorcrypto_ChaCha20Poly1305_encrypt(mp_obj_t self,
                                                          mp_obj_t data) {
  mp_obj_ChaCha20Poly1305_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t in = {0};
  mp_get_buffer_raise(data, &in, MP_BUFFER_READ);
  vstr_t vstr = {0};
  vstr_init_len(&vstr, in.len);
  chacha20poly1305_encrypt(&(o->ctx), in.buf, (uint8_t *)vstr.buf, in.len);
  o->plen += in.len;
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_ChaCha20Poly1305_encrypt_obj,
                                 mod_trezorcrypto_ChaCha20Poly1305_encrypt);

/// def decrypt(self, data: bytes) -> bytes:
///     """
///     Decrypt data (length of data must be divisible by 64 except for the
///     final value).
///     """
STATIC mp_obj_t mod_trezorcrypto_ChaCha20Poly1305_decrypt(mp_obj_t self,
                                                          mp_obj_t data) {
  mp_obj_ChaCha20Poly1305_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t in = {0};
  mp_get_buffer_raise(data, &in, MP_BUFFER_READ);
  vstr_t vstr = {0};
  vstr_init_len(&vstr, in.len);
  chacha20poly1305_decrypt(&(o->ctx), in.buf, (uint8_t *)vstr.buf, in.len);
  o->plen += in.len;
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_ChaCha20Poly1305_decrypt_obj,
                                 mod_trezorcrypto_ChaCha20Poly1305_decrypt);

/// def auth(self, data: bytes) -> None:
///     """
///     Include authenticated data in the Poly1305 MAC using the RFC 7539
///     style with 16 byte padding. This must only be called once and prior
///     to encryption or decryption.
///     """
STATIC mp_obj_t mod_trezorcrypto_ChaCha20Poly1305_auth(mp_obj_t self,
                                                       mp_obj_t data) {
  mp_obj_ChaCha20Poly1305_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t in = {0};
  mp_get_buffer_raise(data, &in, MP_BUFFER_READ);
  rfc7539_auth(&(o->ctx), in.buf, in.len);
  o->alen += in.len;
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_ChaCha20Poly1305_auth_obj,
                                 mod_trezorcrypto_ChaCha20Poly1305_auth);

/// def finish(self) -> bytes:
///     """
///     Compute RFC 7539-style Poly1305 MAC.
///     """
STATIC mp_obj_t mod_trezorcrypto_ChaCha20Poly1305_finish(mp_obj_t self) {
  mp_obj_ChaCha20Poly1305_t *o = MP_OBJ_TO_PTR(self);
  vstr_t mac = {0};
  vstr_init_len(&mac, 16);
  rfc7539_finish(&(o->ctx), o->alen, o->plen, (uint8_t *)mac.buf);
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &mac);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_ChaCha20Poly1305_finish_obj,
                                 mod_trezorcrypto_ChaCha20Poly1305_finish);

STATIC mp_obj_t mod_trezorcrypto_ChaCha20Poly1305___del__(mp_obj_t self) {
  mp_obj_ChaCha20Poly1305_t *o = MP_OBJ_TO_PTR(self);
  memzero(&(o->ctx), sizeof(chacha20poly1305_ctx));
  o->alen = 0;
  o->plen = 0;
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_ChaCha20Poly1305___del___obj,
                                 mod_trezorcrypto_ChaCha20Poly1305___del__);

STATIC const mp_rom_map_elem_t
    mod_trezorcrypto_ChaCha20Poly1305_locals_dict_table[] = {
        {MP_ROM_QSTR(MP_QSTR_encrypt),
         MP_ROM_PTR(&mod_trezorcrypto_ChaCha20Poly1305_encrypt_obj)},
        {MP_ROM_QSTR(MP_QSTR_decrypt),
         MP_ROM_PTR(&mod_trezorcrypto_ChaCha20Poly1305_decrypt_obj)},
        {MP_ROM_QSTR(MP_QSTR_auth),
         MP_ROM_PTR(&mod_trezorcrypto_ChaCha20Poly1305_auth_obj)},
        {MP_ROM_QSTR(MP_QSTR_finish),
         MP_ROM_PTR(&mod_trezorcrypto_ChaCha20Poly1305_finish_obj)},
        {MP_ROM_QSTR(MP_QSTR___del__),
         MP_ROM_PTR(&mod_trezorcrypto_ChaCha20Poly1305___del___obj)},
};
STATIC MP_DEFINE_CONST_DICT(
    mod_trezorcrypto_ChaCha20Poly1305_locals_dict,
    mod_trezorcrypto_ChaCha20Poly1305_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorcrypto_ChaCha20Poly1305_type = {
    {&mp_type_type},
    .name = MP_QSTR_ChaCha20Poly1305,
    .make_new = mod_trezorcrypto_ChaCha20Poly1305_make_new,
    .locals_dict = (void *)&mod_trezorcrypto_ChaCha20Poly1305_locals_dict,
};
