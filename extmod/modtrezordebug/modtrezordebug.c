/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "py/nlr.h"
#include "py/runtime.h"
#include "py/binary.h"
#include "py/objstr.h"

#if MICROPY_PY_TREZORDEBUG

typedef struct _mp_obj_Debug_t {
    mp_obj_base_t base;
} mp_obj_Debug_t;

STATIC mp_obj_t mod_TrezorDebug_Debug_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Debug_t *o = m_new_obj(mp_obj_Debug_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

/// def trezor.debug.memaccess(address: int, length: int) -> bytes
///     '''
///     Creates a bytes object that can be used to access certain memory location.
///     '''
STATIC mp_obj_t mod_TrezorDebug_Debug_memaccess(mp_obj_t self, mp_obj_t address, mp_obj_t length) {
    uint32_t addr = mp_obj_get_int(address);
    uint32_t len = mp_obj_get_int(length);
    mp_obj_str_t *o = m_new_obj(mp_obj_str_t);
    o->base.type = &mp_type_bytes;
    o->len = len;
    o->hash = 0;
    o->data = (byte *)(uintptr_t)addr;
    return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorDebug_Debug_memaccess_obj, mod_TrezorDebug_Debug_memaccess);

STATIC const mp_rom_map_elem_t mod_TrezorDebug_Debug_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_memaccess), MP_ROM_PTR(&mod_TrezorDebug_Debug_memaccess_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorDebug_Debug_locals_dict, mod_TrezorDebug_Debug_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorDebug_Debug_type = {
    { &mp_type_type },
    .name = MP_QSTR_Debug,
    .make_new = mod_TrezorDebug_Debug_make_new,
    .locals_dict = (void*)&mod_TrezorDebug_Debug_locals_dict,
};

STATIC const mp_rom_map_elem_t mp_module_TrezorDebug_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_TrezorDebug) },
    { MP_ROM_QSTR(MP_QSTR_Debug), MP_ROM_PTR(&mod_TrezorDebug_Debug_type) },
};

STATIC MP_DEFINE_CONST_DICT(mp_module_TrezorDebug_globals, mp_module_TrezorDebug_globals_table);

const mp_obj_module_t mp_module_TrezorDebug = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mp_module_TrezorDebug_globals,
};

#endif // MICROPY_PY_TREZORDEBUG
