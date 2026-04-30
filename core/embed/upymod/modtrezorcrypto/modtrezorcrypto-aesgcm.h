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

#include "aes/aesgcm.h"
#include "consteq.h"
#include "memzero.h"

/// package: trezorcrypto.__init__

/// class aesgcm_encrypt:
///     """
///     AES-GCM context for encryption.
///     """
typedef struct _mp_obj_AesGcm_t {
  mp_obj_base_t base;
  gcm_ctx ctx;
  enum {
    STATE_INIT,
    STATE_PROCESSING,
    STATE_FINISHED,
    STATE_FAILED,
  } state;
} mp_obj_AesGcm_t;

/// def __init__(self, key: AnyBytes, iv: AnyBytes) -> None:
///     """
///     Initialize the AES-GCM context for encryption.
///     """
STATIC mp_obj_t mod_trezorcrypto_AesGcm_make_new(const mp_obj_type_t *type,
                                                 size_t n_args, size_t n_kw,
                                                 const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 2, 2, false);
  mp_buffer_info_t key = {0}, iv = {0};
  mp_get_buffer_raise(args[0], &key, MP_BUFFER_READ);
  mp_get_buffer_raise(args[1], &iv, MP_BUFFER_READ);
  if (key.len != 16 && key.len != 24 && key.len != 32) {
    mp_raise_ValueError(MP_ERROR_TEXT(
        "Invalid length of key (has to be 128, 192 or 256 bits)."));
  }

  mp_obj_AesGcm_t *o = m_new_obj_with_finaliser(mp_obj_AesGcm_t);
  o->base.type = type;
  o->state = STATE_INIT;
  if (gcm_init_and_key(key.buf, key.len, &(o->ctx)) != RETURN_GOOD ||
      gcm_init_message(iv.buf, iv.len, &(o->ctx)) != RETURN_GOOD) {
    m_del_obj(mp_obj_AesGcm_t, o);
    mp_raise_type(&mp_type_RuntimeError);
  }
  return MP_OBJ_FROM_PTR(o);
}

/// def auth(self, data: AnyBytes) -> None:
///     """
///     Include authenticated data chunk in the GCM authentication tag. This can
///     be called repeatedly to add authenticated data at any point before
///     finish().
///     """
STATIC mp_obj_t mod_trezorcrypto_AesGcm_auth(mp_obj_t self, mp_obj_t data) {
  mp_obj_AesGcm_t *o = MP_OBJ_TO_PTR(self);
  if (o->state != STATE_INIT && o->state != STATE_PROCESSING) {
    mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Invalid state."));
  }
  mp_buffer_info_t in = {0};
  mp_get_buffer_raise(data, &in, MP_BUFFER_READ);
  if (gcm_auth_header(in.buf, in.len, &(o->ctx)) != RETURN_GOOD) {
    o->state = STATE_FAILED;
    mp_raise_type(&mp_type_RuntimeError);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_AesGcm_auth_obj,
                                 mod_trezorcrypto_AesGcm_auth);

/// def reset(self, iv: AnyBytes) -> None:
///     """
///     Reset the IV for encryption.
///     """
STATIC mp_obj_t mod_trezorcrypto_AesGcm_reset(mp_obj_t self, mp_obj_t iv) {
  mp_obj_AesGcm_t *o = MP_OBJ_TO_PTR(self);
  mp_buffer_info_t in = {0};
  mp_get_buffer_raise(iv, &in, MP_BUFFER_READ);
  if (gcm_init_message(in.buf, in.len, &(o->ctx)) != RETURN_GOOD) {
    o->state = STATE_FAILED;
    mp_raise_type(&mp_type_RuntimeError);
  }
  o->state = STATE_INIT;
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_AesGcm_reset_obj,
                                 mod_trezorcrypto_AesGcm_reset);

/// def encrypt(self, data: AnyBytes) -> bytes:
///     """
///     Encrypt data chunk.
///     """
STATIC mp_obj_t mod_trezorcrypto_AesGcm_encrypt(mp_obj_t self, mp_obj_t data) {
  mp_obj_AesGcm_t *o = MP_OBJ_TO_PTR(self);
  if (o->state != STATE_INIT && o->state != STATE_PROCESSING) {
    mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Invalid state."));
  }
  o->state = STATE_PROCESSING;
  mp_buffer_info_t in = {0};
  mp_get_buffer_raise(data, &in, MP_BUFFER_READ);
  vstr_t vstr = {0};
  vstr_init_len(&vstr, in.len);
  memcpy(vstr.buf, in.buf, in.len);
  if (gcm_encrypt((unsigned char *)vstr.buf, in.len, &(o->ctx)) !=
      RETURN_GOOD) {
    o->state = STATE_FAILED;
    mp_raise_type(&mp_type_RuntimeError);
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_AesGcm_encrypt_obj,
                                 mod_trezorcrypto_AesGcm_encrypt);

/// def encrypt_in_place(self, data: AnyBuffer) -> int:
///     """
///     Encrypt data chunk in place. Returns the length of the encrypted data.
///     """
STATIC mp_obj_t mod_trezorcrypto_AesGcm_encrypt_in_place(mp_obj_t self,
                                                         mp_obj_t data) {
  mp_obj_AesGcm_t *o = MP_OBJ_TO_PTR(self);
  if (o->state != STATE_INIT && o->state != STATE_PROCESSING) {
    mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Invalid state."));
  }
  o->state = STATE_PROCESSING;
  mp_buffer_info_t in = {0};
  mp_get_buffer_raise(data, &in, MP_BUFFER_READ | MP_BUFFER_WRITE);
  if (gcm_encrypt((unsigned char *)in.buf, in.len, &(o->ctx)) != RETURN_GOOD) {
    o->state = STATE_FAILED;
    mp_raise_type(&mp_type_RuntimeError);
  }
  return mp_obj_new_int(in.len);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_AesGcm_encrypt_in_place_obj,
                                 mod_trezorcrypto_AesGcm_encrypt_in_place);

/// def finish(self) -> bytes:
///     """
///     Compute the GCM authentication tag.
///     """
STATIC mp_obj_t mod_trezorcrypto_AesGcm_encrypt_finish(mp_obj_t self) {
  mp_obj_AesGcm_t *o = MP_OBJ_TO_PTR(self);
  if (o->state != STATE_INIT && o->state != STATE_PROCESSING) {
    mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Invalid state."));
  }

  o->state = STATE_FINISHED;
  vstr_t tag = {0};
  vstr_init_len(&tag, 16);
  if (gcm_compute_tag((unsigned char *)tag.buf, tag.len, &(o->ctx)) !=
      RETURN_GOOD) {
    o->state = STATE_FAILED;
    mp_raise_type(&mp_type_RuntimeError);
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &tag);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_AesGcm_encrypt_finish_obj,
                                 mod_trezorcrypto_AesGcm_encrypt_finish);

/// class aesgcm_decrypt:
///     """
///     AES-GCM context for decryption.
///     """

/// def __init__(self, key: AnyBytes, iv: AnyBytes) -> None:
///     """
///     Initialize the AES-GCM context for decryption.
///     """

/// def auth(self, data: AnyBytes) -> None:
///     """
///     Include authenticated data chunk in the GCM authentication tag. This can
///     be called repeatedly to add authenticated data at any point before
///     finish().
///     """

/// def reset(self, iv: AnyBytes) -> None:
///     """
///     Reset the IV for decryption.
///     """

/// def decrypt(self, data: AnyBytes) -> bytes:
///     """
///     Decrypt data chunk.
///     """
STATIC mp_obj_t mod_trezorcrypto_AesGcm_decrypt(mp_obj_t self, mp_obj_t data) {
  mp_obj_AesGcm_t *o = MP_OBJ_TO_PTR(self);
  if (o->state != STATE_INIT && o->state != STATE_PROCESSING) {
    mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Invalid state."));
  }
  o->state = STATE_PROCESSING;
  mp_buffer_info_t in = {0};
  mp_get_buffer_raise(data, &in, MP_BUFFER_READ);
  vstr_t vstr = {0};
  vstr_init_len(&vstr, in.len);
  memcpy(vstr.buf, in.buf, in.len);
  if (gcm_decrypt((unsigned char *)vstr.buf, in.len, &(o->ctx)) !=
      RETURN_GOOD) {
    o->state = STATE_FAILED;
    mp_raise_type(&mp_type_RuntimeError);
  }
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_AesGcm_decrypt_obj,
                                 mod_trezorcrypto_AesGcm_decrypt);

/// def decrypt_in_place(self, data: AnyBuffer) -> int:
///     """
///     Decrypt data chunk in place. Returns the length of the decrypted data.
///     """
STATIC mp_obj_t mod_trezorcrypto_AesGcm_decrypt_in_place(mp_obj_t self,
                                                         mp_obj_t data) {
  mp_obj_AesGcm_t *o = MP_OBJ_TO_PTR(self);
  if (o->state != STATE_INIT && o->state != STATE_PROCESSING) {
    mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Invalid state."));
  }
  o->state = STATE_PROCESSING;
  mp_buffer_info_t in = {0};
  mp_get_buffer_raise(data, &in, MP_BUFFER_READ | MP_BUFFER_WRITE);
  if (gcm_decrypt((unsigned char *)in.buf, in.len, &(o->ctx)) != RETURN_GOOD) {
    o->state = STATE_FAILED;
    mp_raise_type(&mp_type_RuntimeError);
  }
  return mp_obj_new_int(in.len);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_AesGcm_decrypt_in_place_obj,
                                 mod_trezorcrypto_AesGcm_decrypt_in_place);

/// def finish(self, expected_tag: AnyBytes) -> None:
///     """
///     Verify the GCM authentication tag.
///     """
STATIC mp_obj_t mod_trezorcrypto_AesGcm_decrypt_finish(mp_obj_t self,
                                                       mp_obj_t expected_tag) {
  mp_obj_AesGcm_t *o = MP_OBJ_TO_PTR(self);
  if (o->state != STATE_INIT && o->state != STATE_PROCESSING) {
    mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Invalid state."));
  }

  o->state = STATE_FINISHED;
  mp_buffer_info_t exp_tag = {0};
  mp_get_buffer_raise(expected_tag, &exp_tag, MP_BUFFER_READ);
  if (exp_tag.len != 16) {
    mp_raise_ValueError(
        MP_ERROR_TEXT("Invalid length of the tag. It has to be 16 bytes."));
  }
  vstr_t tag = {0};
  vstr_init_len(&tag, 16);
  if (gcm_compute_tag((unsigned char *)tag.buf, tag.len, &(o->ctx)) !=
      RETURN_GOOD) {
    o->state = STATE_FAILED;
    mp_raise_type(&mp_type_RuntimeError);
  }

  if (!consteq(tag.buf, exp_tag.buf, exp_tag.len)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Authentication failed."));
  }

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_AesGcm_decrypt_finish_obj,
                                 mod_trezorcrypto_AesGcm_decrypt_finish);

STATIC mp_obj_t mod_trezorcrypto_AesGcm___del__(mp_obj_t self) {
  mp_obj_AesGcm_t *o = MP_OBJ_TO_PTR(self);
  memzero(&(o->ctx), sizeof(gcm_ctx));
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_AesGcm___del___obj,
                                 mod_trezorcrypto_AesGcm___del__);

STATIC const mp_rom_map_elem_t
    mod_trezorcrypto_AesGcmEncrypt_locals_dict_table[] = {
        {MP_ROM_QSTR(MP_QSTR_auth),
         MP_ROM_PTR(&mod_trezorcrypto_AesGcm_auth_obj)},
        {MP_ROM_QSTR(MP_QSTR_reset),
         MP_ROM_PTR(&mod_trezorcrypto_AesGcm_reset_obj)},
        {MP_ROM_QSTR(MP_QSTR_encrypt),
         MP_ROM_PTR(&mod_trezorcrypto_AesGcm_encrypt_obj)},
        {MP_ROM_QSTR(MP_QSTR_encrypt_in_place),
         MP_ROM_PTR(&mod_trezorcrypto_AesGcm_encrypt_in_place_obj)},

        {MP_ROM_QSTR(MP_QSTR_finish),
         MP_ROM_PTR(&mod_trezorcrypto_AesGcm_encrypt_finish_obj)},
        {MP_ROM_QSTR(MP_QSTR___del__),
         MP_ROM_PTR(&mod_trezorcrypto_AesGcm___del___obj)},
};

STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_AesGcmEncrypt_locals_dict,
                            mod_trezorcrypto_AesGcmEncrypt_locals_dict_table);

STATIC const mp_rom_map_elem_t
    mod_trezorcrypto_AesGcmDecrypt_locals_dict_table[] = {
        {MP_ROM_QSTR(MP_QSTR_auth),
         MP_ROM_PTR(&mod_trezorcrypto_AesGcm_auth_obj)},
        {MP_ROM_QSTR(MP_QSTR_reset),
         MP_ROM_PTR(&mod_trezorcrypto_AesGcm_reset_obj)},
        {MP_ROM_QSTR(MP_QSTR_decrypt),
         MP_ROM_PTR(&mod_trezorcrypto_AesGcm_decrypt_obj)},
        {MP_ROM_QSTR(MP_QSTR_decrypt_in_place),
         MP_ROM_PTR(&mod_trezorcrypto_AesGcm_decrypt_in_place_obj)},
        {MP_ROM_QSTR(MP_QSTR_finish),
         MP_ROM_PTR(&mod_trezorcrypto_AesGcm_decrypt_finish_obj)},
        {MP_ROM_QSTR(MP_QSTR___del__),
         MP_ROM_PTR(&mod_trezorcrypto_AesGcm___del___obj)},
};

STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_AesGcmDecrypt_locals_dict,
                            mod_trezorcrypto_AesGcmDecrypt_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorcrypto_AesGcmEncrypt_type = {
    {&mp_type_type},
    .name = MP_QSTR_aesgcm_encrypt,
    .make_new = mod_trezorcrypto_AesGcm_make_new,
    .locals_dict = (void *)&mod_trezorcrypto_AesGcmEncrypt_locals_dict,
};

STATIC const mp_obj_type_t mod_trezorcrypto_AesGcmDecrypt_type = {
    {&mp_type_type},
    .name = MP_QSTR_aesgcm_decrypt,
    .make_new = mod_trezorcrypto_AesGcm_make_new,
    .locals_dict = (void *)&mod_trezorcrypto_AesGcmDecrypt_locals_dict,
};
