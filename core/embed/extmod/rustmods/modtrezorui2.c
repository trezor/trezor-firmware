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

#if MICROPY_PY_TREZORUI2

#include "librust.h"

#if TREZOR_MODEL == T
/// def layout_new_example(text: str) -> None:
///     """Example layout."""
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorui2_layout_new_example_obj,
                                 ui_layout_new_example);
#elif TREZOR_MODEL == 1
/// def layout_new_confirm_action(
///     title: str,
///     action: str | None,
///     description: str | None,
///     verb: str | None,
///     verb_cancel: str | None,
///     hold: bool | None,
///     reverse: bool,
/// ) -> int:
///     """Example layout. All arguments must be passed as kwargs."""
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_trezorui2_layout_new_confirm_action_obj,
                                  0, ui_layout_new_confirm_action);
#endif

STATIC const mp_rom_map_elem_t mp_module_trezorui2_globals_table[] = {
#if TREZOR_MODEL == T
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorui2)},

    {MP_ROM_QSTR(MP_QSTR_layout_new_example),
     MP_ROM_PTR(&mod_trezorui2_layout_new_example_obj)},
#elif TREZOR_MODEL == 1
    {MP_ROM_QSTR(MP_QSTR_layout_new_confirm_action),
     MP_ROM_PTR(&mod_trezorui2_layout_new_confirm_action_obj)},
#endif

};

STATIC MP_DEFINE_CONST_DICT(mp_module_trezorui2_globals,
                            mp_module_trezorui2_globals_table);

const mp_obj_module_t mp_module_trezorui2 = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezorui2_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorui2, mp_module_trezorui2,
                   MICROPY_PY_TREZORUI2);

#endif  // MICROPY_PY_TREZORUI2
