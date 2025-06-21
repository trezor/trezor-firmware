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

#include <sys/power_manager.h>

/// package: trezorio.pm

/// def suspend() -> bool:
///     """
///     Suspends the device. Returns True on success.
///     """
STATIC mp_obj_t mod_trezorio_pm_suspend() {
  pm_status_t res = pm_suspend();
  return mp_obj_new_bool(res == PM_OK);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_pm_suspend_obj,
                                 mod_trezorio_pm_suspend);

STATIC const mp_rom_map_elem_t mod_trezorio_pm_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_pm)},
    {MP_ROM_QSTR(MP_QSTR_suspend), MP_ROM_PTR(&mod_trezorio_pm_suspend_obj)},

};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_pm_globals,
                            mod_trezorio_pm_globals_table);

STATIC const mp_obj_module_t mod_trezorio_pm_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorio_pm_globals,
};
