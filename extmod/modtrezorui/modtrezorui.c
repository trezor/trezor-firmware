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

#if MICROPY_PY_TREZORUI

#include "modtrezorui-display.h"

STATIC const mp_rom_map_elem_t mp_module_TrezorUi_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_TrezorUi) },
    { MP_ROM_QSTR(MP_QSTR_Display), MP_ROM_PTR(&mod_TrezorUi_Display_type) },
};

STATIC MP_DEFINE_CONST_DICT(mp_module_TrezorUi_globals, mp_module_TrezorUi_globals_table);

const mp_obj_module_t mp_module_TrezorUi = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mp_module_TrezorUi_globals,
};

#endif // MICROPY_PY_TREZORUI
