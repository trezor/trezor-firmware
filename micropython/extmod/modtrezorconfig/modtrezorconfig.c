/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "py/runtime.h"

#include "norcow.h"

#if MICROPY_PY_TREZORCONFIG

/// class Config:
///     '''
///     Persistent key-value storage, with 16-bit keys and bytes values.
///     '''
typedef struct _mp_obj_Config_t {
    mp_obj_base_t base;
} mp_obj_Config_t;

/// def __init__(self):
///     '''
///     Initializes the storage.
///     '''
STATIC mp_obj_t mod_trezorconfig_Config_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Config_t *o = m_new_obj(mp_obj_Config_t);
    o->base.type = type;
    bool r = norcow_init();
    if (!r) {
        mp_raise_msg(&mp_type_RuntimeError, "Could not initialize storage");
    }
    return MP_OBJ_FROM_PTR(o);
}

/// def get(self, app: int, key: int) -> bytes:
///     '''
///     Gets a value of given key for given app (or empty bytes if not set).
///     '''
STATIC mp_obj_t mod_trezorconfig_Config_get(mp_obj_t self, mp_obj_t app, mp_obj_t key) {
    uint8_t a = mp_obj_get_int(app);
    uint8_t k = mp_obj_get_int(key);
    uint16_t appkey = a << 8 | k, len;
    const void *val;
    bool r = norcow_get(appkey, &val, &len);
    if (!r || len == 0) {
        return mp_const_empty_bytes;
    }
    vstr_t vstr;
    vstr_init_len(&vstr, len);
    memcpy(vstr.buf, val, len);
    return mp_obj_new_str_from_vstr(&mp_type_bytes, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorconfig_Config_get_obj, mod_trezorconfig_Config_get);

/// def set(self, app: int, key: int, value: bytes) -> None:
///     '''
///     Sets a value of given key for given app.
///     Returns True on success.
///     '''
STATIC mp_obj_t mod_trezorconfig_Config_set(size_t n_args, const mp_obj_t *args) {
    uint8_t a = mp_obj_get_int(args[1]);
    uint8_t k = mp_obj_get_int(args[2]);
    uint16_t appkey = a << 8 | k;
    mp_buffer_info_t value;
    mp_get_buffer_raise(args[3], &value, MP_BUFFER_READ);
    bool r = norcow_set(appkey, value.buf, value.len);
    if (!r) {
        mp_raise_msg(&mp_type_RuntimeError, "Could not save value");
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorconfig_Config_set_obj, 4, 4, mod_trezorconfig_Config_set);

/// def wipe(self) -> None:
///     '''
///     Erases the whole config. Use with caution!
///     '''
STATIC mp_obj_t mod_trezorconfig_Config_wipe(mp_obj_t self) {
    bool r = norcow_wipe();
    if (!r) {
       mp_raise_msg(&mp_type_RuntimeError, "Could not wipe storage");
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorconfig_Config_wipe_obj, mod_trezorconfig_Config_wipe);

STATIC const mp_rom_map_elem_t mod_trezorconfig_Config_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_get), MP_ROM_PTR(&mod_trezorconfig_Config_get_obj) },
    { MP_ROM_QSTR(MP_QSTR_set), MP_ROM_PTR(&mod_trezorconfig_Config_set_obj) },
    { MP_ROM_QSTR(MP_QSTR_wipe), MP_ROM_PTR(&mod_trezorconfig_Config_wipe_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorconfig_Config_locals_dict, mod_trezorconfig_Config_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorconfig_Config_type = {
    { &mp_type_type },
    .name = MP_QSTR_Config,
    .make_new = mod_trezorconfig_Config_make_new,
    .locals_dict = (void*)&mod_trezorconfig_Config_locals_dict,
};

STATIC const mp_rom_map_elem_t mp_module_trezorconfig_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorconfig) },
    { MP_ROM_QSTR(MP_QSTR_Config), MP_ROM_PTR(&mod_trezorconfig_Config_type) },
};

STATIC MP_DEFINE_CONST_DICT(mp_module_trezorconfig_globals, mp_module_trezorconfig_globals_table);

const mp_obj_module_t mp_module_trezorconfig = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mp_module_trezorconfig_globals,
};

#endif // MICROPY_PY_TREZORCONFIG
