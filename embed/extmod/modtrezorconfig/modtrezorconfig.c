/*
 * Copyright (c) Pavol Rusnak, Jan Pochyla, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "py/runtime.h"
#include "py/mphal.h"
#include "py/objstr.h"

#if MICROPY_PY_TREZORCONFIG

#include "norcow.h"
#include "storage.h"

/// def init() -> None:
///     '''
///     Initializes the storage.  Must be called before any other method is
///     called from this module!
///     '''
STATIC mp_obj_t mod_trezorconfig_init(void) {
    bool r = storage_init();
    if (!r) {
        mp_raise_msg(&mp_type_RuntimeError, "Could not initialize config module");
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_init_obj, mod_trezorconfig_init);

/// def unlock(pin: str) -> bool:
///     '''
///     Attempts to unlock the storage with given PIN.  Returns True on
///     success, False on failure.
///     '''
STATIC mp_obj_t mod_trezorconfig_unlock(mp_obj_t pin) {
    mp_buffer_info_t buf;
    mp_get_buffer_raise(pin, &buf, MP_BUFFER_READ);
    bool r = storage_unlock(buf.buf, buf.len);
    if (!r) {
        return mp_const_false;
    }
    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorconfig_unlock_obj, mod_trezorconfig_unlock);

/// def get(app: int, key: int) -> bytes:
///     '''
///     Gets a value of given key for given app (or empty bytes if not set).
///     '''
STATIC mp_obj_t mod_trezorconfig_get(mp_obj_t app, mp_obj_t key) {
    uint8_t a = mp_obj_get_int(app);
    uint8_t k = mp_obj_get_int(key);
    uint16_t appkey = a << 8 | k;
    uint16_t len = 0;
    const void *val;
    bool r = storage_get(appkey, &val, &len);
    if (!r || len == 0) {
        return mp_const_empty_bytes;
    }
    return mp_obj_new_str_of_type(&mp_type_bytes, val, len);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorconfig_get_obj, mod_trezorconfig_get);

/// def set(app: int, key: int, value: bytes) -> None:
///     '''
///     Sets a value of given key for given app.
///     '''
STATIC mp_obj_t mod_trezorconfig_set(mp_obj_t app, mp_obj_t key, mp_obj_t value) {
    uint8_t a = mp_obj_get_int(app);
    uint8_t k = mp_obj_get_int(key);
    uint16_t appkey = a << 8 | k;
    mp_buffer_info_t v;
    mp_get_buffer_raise(value, &v, MP_BUFFER_READ);
    bool r = storage_set(appkey, v.buf, v.len);
    if (!r) {
        mp_raise_msg(&mp_type_RuntimeError, "Could not save value");
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorconfig_set_obj, mod_trezorconfig_set);

/// def wipe() -> None:
///     '''
///     Erases the whole config. Use with caution!
///     '''
STATIC mp_obj_t mod_trezorconfig_wipe(void) {
    bool r = storage_wipe();
    if (!r) {
       mp_raise_msg(&mp_type_RuntimeError, "Could not wipe storage");
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorconfig_wipe_obj, mod_trezorconfig_wipe);

STATIC const mp_rom_map_elem_t mp_module_trezorconfig_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorconfig) },
    { MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&mod_trezorconfig_init_obj) },
    { MP_ROM_QSTR(MP_QSTR_unlock), MP_ROM_PTR(&mod_trezorconfig_unlock_obj) },
    { MP_ROM_QSTR(MP_QSTR_get), MP_ROM_PTR(&mod_trezorconfig_get_obj) },
    { MP_ROM_QSTR(MP_QSTR_set), MP_ROM_PTR(&mod_trezorconfig_set_obj) },
    { MP_ROM_QSTR(MP_QSTR_wipe), MP_ROM_PTR(&mod_trezorconfig_wipe_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mp_module_trezorconfig_globals, mp_module_trezorconfig_globals_table);

const mp_obj_module_t mp_module_trezorconfig = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mp_module_trezorconfig_globals,
};

#endif // MICROPY_PY_TREZORCONFIG
