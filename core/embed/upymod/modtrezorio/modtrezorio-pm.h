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

/// # Status codes:
/// PM_OK: int
/// PM_NOT_INITIALIZED: int
/// PM_REQUEST_REJECTED: int
/// PM_ERROR: int

/// # Wakeup flags:
/// WAKEUP_FLAG_BUTTON: int
/// WAKEUP_FLAG_POWER: int
/// WAKEUP_FLAG_BLE: int
/// WAKEUP_FLAG_NFC: int
/// WAKEUP_FLAG_RTC: int

/// def suspend() -> tuple[int, int]:
///     """
///     Suspends the device. Returns tuple (status, wakeup_flags).
///     Status codes: PM_OK=0, PM_NOT_INITIALIZED=1, PM_REQUEST_REJECTED=2,
///     PM_ERROR=3
///     Wakeup flags: BUTTON=1, POWER=2, BLE=4, NFC=8, RTC=16
///     """
STATIC mp_obj_t mod_trezorio_pm_suspend() {
  wakeup_flags_t wakeup_flags = 0;
  pm_status_t res = pm_suspend(&wakeup_flags);

  mp_obj_t tuple_items[2];
  tuple_items[0] = mp_obj_new_int((mp_int_t)res);
  tuple_items[1] = mp_obj_new_int((mp_int_t)wakeup_flags);
  return mp_obj_new_tuple(2, tuple_items);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_pm_suspend_obj,
                                 mod_trezorio_pm_suspend);

STATIC const mp_rom_map_elem_t mod_trezorio_pm_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_pm)},
    {MP_ROM_QSTR(MP_QSTR_suspend), MP_ROM_PTR(&mod_trezorio_pm_suspend_obj)},

    // PM status constants
    {MP_ROM_QSTR(MP_QSTR_PM_OK), MP_ROM_INT(PM_OK)},
    {MP_ROM_QSTR(MP_QSTR_PM_NOT_INITIALIZED), MP_ROM_INT(PM_NOT_INITIALIZED)},
    {MP_ROM_QSTR(MP_QSTR_PM_REQUEST_REJECTED), MP_ROM_INT(PM_REQUEST_REJECTED)},
    {MP_ROM_QSTR(MP_QSTR_PM_ERROR), MP_ROM_INT(PM_ERROR)},

    // Wakeup flag constants
    {MP_ROM_QSTR(MP_QSTR_WAKEUP_FLAG_BUTTON), MP_ROM_INT(WAKEUP_FLAG_BUTTON)},
    {MP_ROM_QSTR(MP_QSTR_WAKEUP_FLAG_POWER), MP_ROM_INT(WAKEUP_FLAG_POWER)},
    {MP_ROM_QSTR(MP_QSTR_WAKEUP_FLAG_BLE), MP_ROM_INT(WAKEUP_FLAG_BLE)},
    {MP_ROM_QSTR(MP_QSTR_WAKEUP_FLAG_NFC), MP_ROM_INT(WAKEUP_FLAG_NFC)},
    {MP_ROM_QSTR(MP_QSTR_WAKEUP_FLAG_RTC), MP_ROM_INT(WAKEUP_FLAG_RTC)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_pm_globals,
                            mod_trezorio_pm_globals_table);

STATIC const mp_obj_module_t mod_trezorio_pm_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorio_pm_globals,
};
