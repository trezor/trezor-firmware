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

#include <io/haptic.h>

/// package: trezorio.haptic

/// def haptic_set_enabled(enable: bool) -> None:
///     """
///     Enable/Disable the haptic feedback.
///     """
STATIC mp_obj_t mod_trezorio_haptic_set_enabled(mp_obj_t enable) {
  haptic_set_enabled(mp_obj_is_true(enable));
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_haptic_set_enabled_obj,
                                 mod_trezorio_haptic_set_enabled);

STATIC const mp_rom_map_elem_t mod_trezorio_haptic_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_haptic)},
    {MP_ROM_QSTR(MP_QSTR_haptic_set_enabled),
     MP_ROM_PTR(&mod_trezorio_haptic_set_enabled_obj)},

};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_haptic_globals,
                            mod_trezorio_haptic_globals_table);

STATIC const mp_obj_module_t mod_trezorio_haptic_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorio_haptic_globals,
};
