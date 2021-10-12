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

#if MICROPY_PY_TREZORCRYPTO

#include "librust.h"


STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_zcash_diag, zcash_diag);

STATIC const mp_rom_map_elem_t mp_module_trezorzcash_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorzcash)},
    {MP_ROM_QSTR(MP_QSTR_diag),     MP_ROM_PTR(&mod_zcash_diag)},
};

STATIC MP_DEFINE_CONST_DICT(mp_module_trezorzcash_globals,
                            mp_module_trezorzcash_globals_table);

const mp_obj_module_t mp_module_trezorzcash = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezorzcash_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorzcash, mp_module_trezorzcash,
                   MICROPY_PY_TREZORCRYPTO);

#endif  // MICROPY_PY_TREZOCRYPTO
