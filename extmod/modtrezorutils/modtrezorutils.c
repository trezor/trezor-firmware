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

#if MICROPY_PY_TREZORUTILS

// class Utils(object):
typedef struct _mp_obj_Utils_t {
    mp_obj_base_t base;
} mp_obj_Utils_t;

// def Utils.__init__(self)
STATIC mp_obj_t mod_TrezorUtils_Utils_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Utils_t *o = m_new_obj(mp_obj_Utils_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

// def Utils.memaccess(self, address: int, length: int) -> bytes
STATIC mp_obj_t mod_TrezorUtils_Utils_memaccess(mp_obj_t self, mp_obj_t address, mp_obj_t length) {
    uint32_t addr = mp_obj_get_int(address);
    uint32_t len = mp_obj_get_int(length);
    mp_obj_str_t *o = m_new_obj(mp_obj_str_t);
    o->base.type = &mp_type_bytes;
    o->len = len;
    o->hash = 0;
    o->data = (byte *)(uintptr_t)addr;
    return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorUtils_Utils_memaccess_obj, mod_TrezorUtils_Utils_memaccess);

// from modtrezorui
uint32_t trezorui_poll_sdl_event(uint32_t timeout_us);

// def Utils.select(self, timeout_us: int) -> None/tuple
STATIC mp_obj_t mod_TrezorUtils_Utils_select(mp_obj_t self, mp_obj_t timeout_us) {
    uint32_t to = mp_obj_get_int(timeout_us);
    uint32_t e = trezorui_poll_sdl_event(to);
    if (e) {
        mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(3, NULL));
        tuple->items[0] = MP_OBJ_NEW_SMALL_INT((e & 0xFF0000) >> 16);
        tuple->items[1] = MP_OBJ_NEW_SMALL_INT((e & 0xFF00) >> 8);
        tuple->items[2] = MP_OBJ_NEW_SMALL_INT((e & 0xFF));
        return MP_OBJ_FROM_PTR(tuple);
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorUtils_Utils_select_obj, mod_TrezorUtils_Utils_select);

// Utils stuff

STATIC const mp_rom_map_elem_t mod_TrezorUtils_Utils_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_memaccess), MP_ROM_PTR(&mod_TrezorUtils_Utils_memaccess_obj) },
    { MP_ROM_QSTR(MP_QSTR_select), MP_ROM_PTR(&mod_TrezorUtils_Utils_select_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorUtils_Utils_locals_dict, mod_TrezorUtils_Utils_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorUtils_Utils_type = {
    { &mp_type_type },
    .name = MP_QSTR_Utils,
    .make_new = mod_TrezorUtils_Utils_make_new,
    .locals_dict = (void*)&mod_TrezorUtils_Utils_locals_dict,
};

// module stuff

STATIC const mp_rom_map_elem_t mp_module_TrezorUtils_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_TrezorUtils) },
    { MP_ROM_QSTR(MP_QSTR_Utils), MP_ROM_PTR(&mod_TrezorUtils_Utils_type) },
};

STATIC MP_DEFINE_CONST_DICT(mp_module_TrezorUtils_globals, mp_module_TrezorUtils_globals_table);

const mp_obj_module_t mp_module_TrezorUtils = {
    .base = { &mp_type_module },
    .name = MP_QSTR_TrezorUtils,
    .globals = (mp_obj_dict_t*)&mp_module_TrezorUtils_globals,
};

#endif // MICROPY_PY_TREZORUTILS
