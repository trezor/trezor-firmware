/*
 * This file is part of the TREZOR project, https://trezor.io/
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

#include "blake2s.h"
#include "memzero.h"

/// class Blake2s:
///     '''
///     Blake2s context.
///     '''
typedef struct _mp_obj_Blake2s_t {
    mp_obj_base_t base;
    BLAKE2S_CTX ctx;
} mp_obj_Blake2s_t;

STATIC mp_obj_t mod_trezorcrypto_Blake2s_update(mp_obj_t self, mp_obj_t data);

/// def __init__(self, data: bytes = None, outlen: int = Blake2s.digest_size, key: bytes = None, personal: bytes = None) -> None:
///     '''
///     Creates a hash context object.
///     '''
STATIC mp_obj_t mod_trezorcrypto_Blake2s_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {

    STATIC const mp_arg_t allowed_args[] = {
        { MP_QSTR_data,                      MP_ARG_OBJ, {.u_obj = mp_const_empty_bytes} },
        { MP_QSTR_outlen,   MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = BLAKE2S_DIGEST_LENGTH} },
        { MP_QSTR_key,      MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_empty_bytes} },
        { MP_QSTR_personal, MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_empty_bytes} },
    };
    mp_arg_val_t vals[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, MP_ARRAY_SIZE(allowed_args), allowed_args, vals);

    size_t data_len;
    const uint8_t *data = (const uint8_t *)mp_obj_str_get_data(vals[0].u_obj, &data_len);
    const mp_int_t outlen = vals[1].u_int;
    size_t key_len;
    const uint8_t *key = (const uint8_t *)mp_obj_str_get_data(vals[2].u_obj, &key_len);
    size_t personal_len;
    const uint8_t *personal = (const uint8_t *)mp_obj_str_get_data(vals[3].u_obj, &personal_len);

    if (key_len > 0 && personal_len > 0) {
        mp_raise_ValueError("Invalid Blake2s parameters: cannot use key and personal at the same time");
    }

    mp_obj_Blake2s_t *o = m_new_obj(mp_obj_Blake2s_t);
    o->base.type = type;
    int res = 0;

    if (key_len > 0) {
        res = blake2s_InitKey(&(o->ctx), outlen, key, key_len);
    } else if (personal_len > 0) {
        res = blake2s_InitPersonal(&(o->ctx), outlen, personal, personal_len);
    } else {
        res = blake2s_Init(&(o->ctx), outlen);
    }

    if (res < 0) {
        mp_raise_ValueError("Invalid Blake2s parameters");
    }

    // constructor called with data argument set
    if (data_len > 0) {
        blake2s_Update(&(o->ctx), data, data_len);
    }

    return MP_OBJ_FROM_PTR(o);
}

/// def update(self, data: bytes) -> None:
///     '''
///     Update the hash context with hashed data.
///     '''
STATIC mp_obj_t mod_trezorcrypto_Blake2s_update(mp_obj_t self, mp_obj_t data) {
    mp_obj_Blake2s_t *o = MP_OBJ_TO_PTR(self);
    mp_buffer_info_t msg;
    mp_get_buffer_raise(data, &msg, MP_BUFFER_READ);
    if (msg.len > 0) {
        blake2s_Update(&(o->ctx), msg.buf, msg.len);
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorcrypto_Blake2s_update_obj, mod_trezorcrypto_Blake2s_update);

/// def digest(self) -> bytes:
///     '''
///     Returns the digest of hashed data.
///     '''
STATIC mp_obj_t mod_trezorcrypto_Blake2s_digest(mp_obj_t self) {
    mp_obj_Blake2s_t *o = MP_OBJ_TO_PTR(self);
    uint8_t out[BLAKE2S_DIGEST_LENGTH];
    BLAKE2S_CTX ctx;
    memcpy(&ctx, &(o->ctx), sizeof(BLAKE2S_CTX));
    blake2s_Final(&ctx, out, ctx.outlen);
    memset(&ctx, 0, sizeof(BLAKE2S_CTX));
    return mp_obj_new_bytes(out, o->ctx.outlen);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_Blake2s_digest_obj, mod_trezorcrypto_Blake2s_digest);

STATIC mp_obj_t mod_trezorcrypto_Blake2s___del__(mp_obj_t self) {
    mp_obj_Blake2s_t *o = MP_OBJ_TO_PTR(self);
    memzero(&(o->ctx), sizeof(BLAKE2S_CTX));
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_Blake2s___del___obj, mod_trezorcrypto_Blake2s___del__);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_Blake2s_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_update), MP_ROM_PTR(&mod_trezorcrypto_Blake2s_update_obj) },
    { MP_ROM_QSTR(MP_QSTR_digest), MP_ROM_PTR(&mod_trezorcrypto_Blake2s_digest_obj) },
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&mod_trezorcrypto_Blake2s___del___obj) },
    { MP_ROM_QSTR(MP_QSTR_block_size), MP_OBJ_NEW_SMALL_INT(BLAKE2S_BLOCK_LENGTH) },
    { MP_ROM_QSTR(MP_QSTR_digest_size), MP_OBJ_NEW_SMALL_INT(BLAKE2S_DIGEST_LENGTH) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_Blake2s_locals_dict, mod_trezorcrypto_Blake2s_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorcrypto_Blake2s_type = {
    { &mp_type_type },
    .name = MP_QSTR_Blake2s,
    .make_new = mod_trezorcrypto_Blake2s_make_new,
    .locals_dict = (void*)&mod_trezorcrypto_Blake2s_locals_dict,
};
