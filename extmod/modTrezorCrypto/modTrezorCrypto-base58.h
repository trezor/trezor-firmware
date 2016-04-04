/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

// class Base58(object):
typedef struct _mp_obj_Base58_t {
    mp_obj_base_t base;
} mp_obj_Base58_t;

// def Base58.__init__(self):
STATIC mp_obj_t mod_TrezorCrypto_Base58_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_obj_Base58_t *o = m_new_obj(mp_obj_Base58_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

// def Base58.encode(self, data: bytes) -> str
STATIC mp_obj_t mod_TrezorCrypto_Base58_encode(mp_obj_t self, mp_obj_t callback) {
    // TODO
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Base58_encode_obj, mod_TrezorCrypto_Base58_encode);

// def Base58.decode(self, string: str) -> bytes
STATIC mp_obj_t mod_TrezorCrypto_Base58_decode(mp_obj_t self, mp_obj_t data) {
    // TODO
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorCrypto_Base58_decode_obj, mod_TrezorCrypto_Base58_decode);

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
