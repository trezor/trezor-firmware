/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include "py/runtime.h"
#include "py/mphal.h"
#include "py/objstr.h"

#if MICROPY_PY_TREZORIO

#include "modtrezorio-flash.h"
#include "modtrezorio-sbu.h"
#include "modtrezorio-sdcard.h"
#include "modtrezorio-msg.h"

STATIC const mp_rom_map_elem_t mp_module_trezorio_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorio) },

    { MP_ROM_QSTR(MP_QSTR_FlashOTP), MP_ROM_PTR(&mod_trezorio_FlashOTP_type) },

    { MP_ROM_QSTR(MP_QSTR_SBU), MP_ROM_PTR(&mod_trezorio_SBU_type) },

    { MP_ROM_QSTR(MP_QSTR_SDCard), MP_ROM_PTR(&mod_trezorio_SDCard_type) },

    { MP_ROM_QSTR(MP_QSTR_USB), MP_ROM_PTR(&mod_trezorio_USB_type) },
    { MP_ROM_QSTR(MP_QSTR_HID), MP_ROM_PTR(&mod_trezorio_HID_type) },
    { MP_ROM_QSTR(MP_QSTR_VCP), MP_ROM_PTR(&mod_trezorio_VCP_type) },
    { MP_ROM_QSTR(MP_QSTR_poll), MP_ROM_PTR(&mod_trezorio_poll_obj) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH), MP_OBJ_NEW_SMALL_INT(TOUCH_IFACE) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH_START), MP_OBJ_NEW_SMALL_INT((TOUCH_START & 0xFF0000) >> 16) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH_MOVE), MP_OBJ_NEW_SMALL_INT((TOUCH_MOVE & 0xFF0000) >> 16) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH_END), MP_OBJ_NEW_SMALL_INT((TOUCH_END & 0xFF0000) >> 16) },
    { MP_ROM_QSTR(MP_QSTR_POLL_READ), MP_OBJ_NEW_SMALL_INT(POLL_READ) },
    { MP_ROM_QSTR(MP_QSTR_POLL_WRITE), MP_OBJ_NEW_SMALL_INT(POLL_WRITE) },
};

STATIC MP_DEFINE_CONST_DICT(mp_module_trezorio_globals, mp_module_trezorio_globals_table);

const mp_obj_module_t mp_module_trezorio = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mp_module_trezorio_globals,
};

#endif // MICROPY_PY_TREZORIO
