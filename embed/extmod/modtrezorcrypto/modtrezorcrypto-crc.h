/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "py/objstr.h"
#include "crc.h"

mp_obj_t mod_trezorcrypto_crc_crc32(size_t n_args, const mp_obj_t *args) {
    mp_buffer_info_t bufinfo;
    mp_get_buffer_raise(args[0], &bufinfo, MP_BUFFER_READ);
    uint32_t crc = (n_args > 1) ? mp_obj_get_int_truncated(args[1]) : 0;
    crc = crc32(bufinfo.buf, bufinfo.len, crc ^ 0xffffffff);
    return mp_obj_new_int_from_uint(crc ^ 0xffffffff);
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_crc_crc32_obj, 1, 2, mod_trezorcrypto_crc_crc32);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_crc_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_crc) },
    { MP_ROM_QSTR(MP_QSTR_crc32), MP_ROM_PTR(&mod_trezorcrypto_crc_crc32_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_crc_globals, mod_trezorcrypto_crc_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_crc_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mod_trezorcrypto_crc_globals,
};
