/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include "base58.h"

// class Base58(object):
typedef struct _mp_obj_Base58_t {
    mp_obj_base_t base;
} mp_obj_Base58_t;

// def Base58.__init__(self)
STATIC mp_obj_t mod_TrezorCrypto_Base58_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Base58_t *o = m_new_obj(mp_obj_Base58_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

// def Base58.encode(self, data: bytes) -> str
STATIC mp_obj_t mod_TrezorCrypto_Base58_encode(mp_obj_t self, mp_obj_t data) {
    mp_buffer_info_t databuf;
    mp_get_buffer_raise(data, &databuf, MP_BUFFER_READ);
    vstr_t vstr;
    vstr_init_len(&vstr, databuf.len * 8000 / 5857 + 1); // 256 = 2^8 ; 58 > 2^5.857
    bool r = b58enc(vstr.buf, &vstr.len, databuf.buf, databuf.len);
    if (!r) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid input"));
    }
    vstr.len--; // b58enc returns length including the trailing zero
    return mp_obj_new_str_from_vstr(&mp_type_str, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Base58_encode_obj, mod_TrezorCrypto_Base58_encode);

// def Base58.decode(self, string: str) -> bytes
STATIC mp_obj_t mod_TrezorCrypto_Base58_decode(mp_obj_t self, mp_obj_t string) {
    mp_buffer_info_t stringbuf;
    mp_get_buffer_raise(string, &stringbuf, MP_BUFFER_READ);
    vstr_t vstr;
    vstr_init_len(&vstr, stringbuf.len * 5858 / 8000 + 1); // 256 = 2^8 ; 58 < 2^5.858
    bool r = b58tobin(vstr.buf, &vstr.len, stringbuf.buf);
    if (!r) {
        nlr_raise(mp_obj_new_exception_msg(&mp_type_ValueError, "Invalid input"));
    }
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Base58_decode_obj, mod_TrezorCrypto_Base58_decode);

// Base58 stuff

STATIC const mp_rom_map_elem_t mod_TrezorCrypto_Base58_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_encode), MP_ROM_PTR(&mod_TrezorCrypto_Base58_encode_obj) },
    { MP_ROM_QSTR(MP_QSTR_decode), MP_ROM_PTR(&mod_TrezorCrypto_Base58_decode_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorCrypto_Base58_locals_dict, mod_TrezorCrypto_Base58_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorCrypto_Base58_type = {
    { &mp_type_type },
    .name = MP_QSTR_Base58,
    .make_new = mod_TrezorCrypto_Base58_make_new,
    .locals_dict = (void*)&mod_TrezorCrypto_Base58_locals_dict,
};
