/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "py/runtime.h"

#if MICROPY_PY_TREZORIO

#include "modtrezorio-sdcard.h"

STATIC const mp_rom_map_elem_t mp_module_TrezorIO_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_TrezorIO) },
    { MP_ROM_QSTR(MP_QSTR_SDCard), MP_ROM_PTR(&mod_TrezorIO_SDCard_type) },
};

STATIC MP_DEFINE_CONST_DICT(mp_module_TrezorIO_globals, mp_module_TrezorIO_globals_table);

const mp_obj_module_t mp_module_TrezorIO = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mp_module_TrezorIO_globals,
};

#endif // MICROPY_PY_TREZORIO
