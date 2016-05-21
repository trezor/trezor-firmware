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
#include "py/objstr.h"

#if MICROPY_PY_TREZORSTORAGE

typedef struct _mp_obj_Storage_t {
    mp_obj_base_t base;
} mp_obj_Storage_t;

STATIC mp_obj_t mod_TrezorStorage_Storage_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Storage_t *o = m_new_obj(mp_obj_Storage_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

STATIC mp_obj_t mod_TrezorStorage_Storage_get(mp_obj_t self, mp_obj_t name) {
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorStorage_Storage_get_obj, mod_TrezorStorage_Storage_get);

STATIC mp_obj_t mod_TrezorStorage_Storage_set(mp_obj_t self, mp_obj_t name, mp_obj_t value) {
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorStorage_Storage_set_obj, mod_TrezorStorage_Storage_set);

STATIC const mp_rom_map_elem_t mod_TrezorStorage_Storage_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_get), MP_ROM_PTR(&mod_TrezorStorage_Storage_get_obj) },
    { MP_ROM_QSTR(MP_QSTR_set), MP_ROM_PTR(&mod_TrezorStorage_Storage_set_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorStorage_Storage_locals_dict, mod_TrezorStorage_Storage_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorStorage_Storage_type = {
    { &mp_type_type },
    .name = MP_QSTR_Storage,
    .make_new = mod_TrezorStorage_Storage_make_new,
    .locals_dict = (void*)&mod_TrezorStorage_Storage_locals_dict,
};

STATIC const mp_rom_map_elem_t mp_module_TrezorStorage_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_TrezorStorage) },
    { MP_ROM_QSTR(MP_QSTR_Storage), MP_ROM_PTR(&mod_TrezorStorage_Storage_type) },
};

STATIC MP_DEFINE_CONST_DICT(mp_module_TrezorStorage_globals, mp_module_TrezorStorage_globals_table);

const mp_obj_module_t mp_module_TrezorStorage = {
    .base = { &mp_type_module },
    .name = MP_QSTR_TrezorStorage,
    .globals = (mp_obj_dict_t*)&mp_module_TrezorStorage_globals,
};

#endif // MICROPY_PY_TREZORSTORAGE
