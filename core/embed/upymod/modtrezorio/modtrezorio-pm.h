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

/// # Wakeup flags:
/// WAKEUP_FLAG_BUTTON: int
/// WAKEUP_FLAG_POWER: int
/// WAKEUP_FLAG_BLE: int
/// WAKEUP_FLAG_NFC: int
/// WAKEUP_FLAG_RTC: int
/// WAKEUP_FLAG_USB: int
///
/// # Power manager event flags:
/// EVENT_POWER_STATUS_CHANGED: int
/// EVENT_CHARGING_STATUS_CHANGED: int
/// EVENT_USB_CONNECTED_CHANGED: int
/// EVENT_WIRELESS_CONNECTED_CHANGED: int
/// EVENT_NTC_CONNECTED_CHANGED: int
/// EVENT_CHARGING_LIMITED_CHANGED: int
/// EVENT_BATTERY_OCV_JUMP_DETECTED: int
/// EVENT_BATTERY_TEMP_JUMP_DETECTED: int
/// EVENT_SOC_UPDATED: int

/// def soc() -> int:
///    """
///    Returns the state of charge (SoC) in percent (0-100). Raises RuntimeError
///    on failure.
///    """
STATIC mp_obj_t mod_trezorio_pm_soc() {
  pm_state_t state = {0};
  pm_status_t res = pm_get_state(&state);
  if (res != PM_OK) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get power manager state"));
  }
  return mp_obj_new_int(state.soc);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_pm_soc_obj, mod_trezorio_pm_soc);

/// def suspend() -> int:
///     """
///     Suspends the device. Returns wakeup flag. Raises RuntimeError on
///     failure.
///     Wakeup flags: BUTTON=1, POWER=2, BLE=4, NFC=8, RTC=16
///     """
STATIC mp_obj_t mod_trezorio_pm_suspend() {
  wakeup_flags_t wakeup_flags = 0;
  pm_status_t res = pm_suspend(&wakeup_flags);
  if (res != PM_OK) {
    mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Failed to suspend"));
  }
  return mp_obj_new_int_from_uint(wakeup_flags);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_pm_suspend_obj,
                                 mod_trezorio_pm_suspend);

/// def hibernate() -> None:
///     """
///     Hibernates the device. Raises RuntimeError on failure.
///     """
STATIC mp_obj_t mod_trezorio_pm_hibernate() {
  pm_status_t res = pm_hibernate();
  if (res != PM_OK) {
    mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Failed to hibernate"));
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_pm_hibernate_obj,
                                 mod_trezorio_pm_hibernate);

/// def is_usb_connected() -> bool:
///     """
///     Returns True if USB is connected, False otherwise. Raises RuntimeError
///     on failure.
///     """
STATIC mp_obj_t mod_trezorio_pm_is_usb_connected() {
  pm_state_t state;
  pm_status_t res = pm_get_state(&state);
  if (res != PM_OK) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get power manager report"));
  }
  return mp_obj_new_bool(state.usb_connected);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_pm_is_usb_connected_obj,
                                 mod_trezorio_pm_is_usb_connected);

/// def is_wireless_connected() -> bool:
///     """
///     Returns True if Wireless power source is connected, False otherwise.
///     Raises RuntimeError on failure.
///     """
STATIC mp_obj_t mod_trezorio_pm_is_wireless_connected() {
  pm_state_t state;
  pm_status_t res = pm_get_state(&state);
  if (res != PM_OK) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to get power manager report"));
  }
  return mp_obj_new_bool(state.wireless_connected);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_pm_is_wireless_connected_obj,
                                 mod_trezorio_pm_is_wireless_connected);

STATIC const mp_rom_map_elem_t mod_trezorio_pm_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_pm)},
    {MP_ROM_QSTR(MP_QSTR_soc), MP_ROM_PTR(&mod_trezorio_pm_soc_obj)},
    {MP_ROM_QSTR(MP_QSTR_suspend), MP_ROM_PTR(&mod_trezorio_pm_suspend_obj)},
    {MP_ROM_QSTR(MP_QSTR_hibernate),
     MP_ROM_PTR(&mod_trezorio_pm_hibernate_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_usb_connected),
     MP_ROM_PTR(&mod_trezorio_pm_is_usb_connected_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_wireless_connected),
     MP_ROM_PTR(&mod_trezorio_pm_is_wireless_connected_obj)},

    // Wakeup flag constants
    {MP_ROM_QSTR(MP_QSTR_WAKEUP_FLAG_BUTTON), MP_ROM_INT(WAKEUP_FLAG_BUTTON)},
    {MP_ROM_QSTR(MP_QSTR_WAKEUP_FLAG_POWER), MP_ROM_INT(WAKEUP_FLAG_POWER)},
    {MP_ROM_QSTR(MP_QSTR_WAKEUP_FLAG_BLE), MP_ROM_INT(WAKEUP_FLAG_BLE)},
    {MP_ROM_QSTR(MP_QSTR_WAKEUP_FLAG_NFC), MP_ROM_INT(WAKEUP_FLAG_NFC)},
    {MP_ROM_QSTR(MP_QSTR_WAKEUP_FLAG_RTC), MP_ROM_INT(WAKEUP_FLAG_RTC)},
    {MP_ROM_QSTR(MP_QSTR_WAKEUP_FLAG_USB), MP_ROM_INT(WAKEUP_FLAG_USB)},

    // Power manager event flags
    {MP_ROM_QSTR(MP_QSTR_EVENT_POWER_STATUS_CHANGED), MP_ROM_INT(1 << 0)},
    {MP_ROM_QSTR(MP_QSTR_EVENT_CHARGING_STATUS_CHANGED), MP_ROM_INT(1 << 1)},
    {MP_ROM_QSTR(MP_QSTR_EVENT_USB_CONNECTED_CHANGED), MP_ROM_INT(1 << 2)},
    {MP_ROM_QSTR(MP_QSTR_EVENT_WIRELESS_CONNECTED_CHANGED), MP_ROM_INT(1 << 3)},
    {MP_ROM_QSTR(MP_QSTR_EVENT_NTC_CONNECTED_CHANGED), MP_ROM_INT(1 << 4)},
    {MP_ROM_QSTR(MP_QSTR_EVENT_CHARGING_LIMITED_CHANGED), MP_ROM_INT(1 << 5)},
    {MP_ROM_QSTR(MP_QSTR_EVENT_BATTERY_OCV_JUMP_DETECTED), MP_ROM_INT(1 << 6)},
    {MP_ROM_QSTR(MP_QSTR_EVENT_BATTERY_TEMP_JUMP_UPDATED), MP_ROM_INT(1 << 7)},
    {MP_ROM_QSTR(MP_QSTR_EVENT_SOC_UPDATED), MP_ROM_INT(1 << 8)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_pm_globals,
                            mod_trezorio_pm_globals_table);

STATIC const mp_obj_module_t mod_trezorio_pm_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorio_pm_globals,
};
