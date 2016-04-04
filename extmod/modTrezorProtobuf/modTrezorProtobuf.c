/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under Microsoft Reference Source License (Ms-RSL)
 * see LICENSE.md file for details
 */

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "py/nlr.h"
#include "py/runtime.h"
#include "py/binary.h"

#if MICROPY_PY_TREZORPROTOBUF

// class Protobuf(object):
typedef struct _mp_obj_Protobuf_t {
    mp_obj_base_t base;
} mp_obj_Protobuf_t;

// def Protobuf.__init__(self):
STATIC mp_obj_t mod_TrezorProtobuf_Protobuf_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_obj_Protobuf_t *o = m_new_obj(mp_obj_Protobuf_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

// def Protobuf.encode(self, message) -> bytes
STATIC mp_obj_t mod_TrezorProtobuf_Protobuf_encode(mp_obj_t self, mp_obj_t callback) {
    // TODO
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorProtobuf_Protobuf_encode_obj, mod_TrezorProtobuf_Protobuf_encode);

// def Protobuf.decode(self, data: bytes) -> object
STATIC mp_obj_t mod_TrezorProtobuf_Protobuf_decode(mp_obj_t self, mp_obj_t data) {
    // TODO
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorProtobuf_Protobuf_decode_obj, mod_TrezorProtobuf_Protobuf_decode);

// Protobuf stuff

STATIC const mp_rom_map_elem_t mod_TrezorProtobuf_Protobuf_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_encode), MP_ROM_PTR(&mod_TrezorProtobuf_Protobuf_encode_obj) },
    { MP_ROM_QSTR(MP_QSTR_decode), MP_ROM_PTR(&mod_TrezorProtobuf_Protobuf_decode_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorProtobuf_Protobuf_locals_dict, mod_TrezorProtobuf_Protobuf_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorProtobuf_Protobuf_type = {
    { &mp_type_type },
    .name = MP_QSTR_Protobuf,
    .make_new = mod_TrezorProtobuf_Protobuf_make_new,
    .locals_dict = (void*)&mod_TrezorProtobuf_Protobuf_locals_dict,
};

// module stuff

STATIC const mp_rom_map_elem_t mp_module_TrezorProtobuf_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_TrezorProtobuf) },
    { MP_ROM_QSTR(MP_QSTR_Protobuf), MP_ROM_PTR(&mod_TrezorProtobuf_Protobuf_type) },
};

STATIC MP_DEFINE_CONST_DICT(mp_module_TrezorProtobuf_globals, mp_module_TrezorProtobuf_globals_table);

const mp_obj_module_t mp_module_TrezorProtobuf = {
    .base = { &mp_type_module },
    .name = MP_QSTR_TrezorProtobuf,
    .globals = (mp_obj_dict_t*)&mp_module_TrezorProtobuf_globals,
};

#endif // MICROPY_PY_TREZORPROTOBUF
