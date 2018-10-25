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

#include "rfc6979.h"

/// package: trezorcrypto.__init__

/// class Rfc6979:
///     '''
///     RFC6979 context.
///     '''
typedef struct _mp_obj_Rfc6979_t {
    mp_obj_base_t base;
    rfc6979_state rng;
} mp_obj_Rfc6979_t;

/// def __init__(self, secret_key: bytes, hash: bytes) -> None:
///     '''
///     Initialize RFC6979 context from secret key and a hash.
///     '''
STATIC mp_obj_t mod_trezorcrypto_Rfc6979_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 2, 2, false);
    mp_obj_Rfc6979_t *o = m_new_obj(mp_obj_Rfc6979_t);
    o->base.type = type;
    mp_buffer_info_t pkey, hash;
    mp_get_buffer_raise(args[0], &pkey, MP_BUFFER_READ);
    mp_get_buffer_raise(args[1], &hash, MP_BUFFER_READ);
    if (pkey.len != 32) {
        mp_raise_ValueError("Secret key has to be 32 bytes long");
    }
    if (hash.len != 32) {
        mp_raise_ValueError("Hash has to be 32 bytes long");
    }
    init_rfc6979((const uint8_t *)pkey.buf, (const uint8_t *)hash.buf, &(o->rng));
    return MP_OBJ_FROM_PTR(o);
}

/// def next(self) -> bytes:
///     '''
///     Compute next 32-bytes of pseudorandom data.
///     '''
STATIC mp_obj_t mod_trezorcrypto_Rfc6979_next(mp_obj_t self) {
    mp_obj_Rfc6979_t *o = MP_OBJ_TO_PTR(self);
    uint8_t out[32];
    generate_rfc6979(out, &(o->rng));
    return mp_obj_new_bytes(out, sizeof(out));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorcrypto_Rfc6979_next_obj, mod_trezorcrypto_Rfc6979_next);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_Rfc6979_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_next), MP_ROM_PTR(&mod_trezorcrypto_Rfc6979_next_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_Rfc6979_locals_dict, mod_trezorcrypto_Rfc6979_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorcrypto_Rfc6979_type = {
    { &mp_type_type },
    .name = MP_QSTR_Rfc6979,
    .make_new = mod_trezorcrypto_Rfc6979_make_new,
    .locals_dict = (void*)&mod_trezorcrypto_Rfc6979_locals_dict,
};
