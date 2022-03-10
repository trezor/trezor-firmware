/*
 * This file is part of the Trezor project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "py/runtime.h"

#if MICROPY_PY_TREZORSTORAGEDEVICE

#include "librust.h"


/// def is_version_stored() -> bool:
///     """Whether version is in storage."""
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorutils_storagedevice_is_version_stored_obj,
                                 storagedevice_is_version_stored);

// /// def get_version() -> bool:
// ///     """Get from storage."""
// STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorutils_storagedevice_get_version_obj,
//                                  storagedevice_get_version);

/// def set_version(version: bytes) -> bool:
///     """Save to storage."""
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorutils_storagedevice_set_version_obj,
                                 storagedevice_set_version);


STATIC const mp_rom_map_elem_t mp_module_trezorstoragedevice_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorstoragedevice)},

    {MP_ROM_QSTR(MP_QSTR_is_version_stored),
     MP_ROM_PTR(&mod_trezorutils_storagedevice_is_version_stored_obj)},
    // {MP_ROM_QSTR(MP_QSTR_get_version),
    //  MP_ROM_PTR(&mod_trezorutils_storagedevice_get_version_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_version),
     MP_ROM_PTR(&mod_trezorutils_storagedevice_set_version_obj)},
};

STATIC MP_DEFINE_CONST_DICT(mp_module_trezorstoragedevice_globals,
                            mp_module_trezorstoragedevice_globals_table);

const mp_obj_module_t mp_module_trezorstoragedevice = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezorstoragedevice_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorstoragedevice, mp_module_trezorstoragedevice,
                   MICROPY_PY_TREZORSTORAGEDEVICE);

#endif  // MICROPY_PY_TREZORSTORAGEDEVICE
