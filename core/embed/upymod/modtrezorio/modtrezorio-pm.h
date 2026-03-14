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

#include <io/power_manager.h>

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
///     """
///     Returns the state of charge (SoC) in percent (0-100). Raises
///     RuntimeError on failure.
///     """
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

#ifdef TREZOR_EMULATOR
/// def set_emu_battery_state(
///     soc: int | None = None,
///     usb_connected: bool | None = None,
///     wireless_connected: bool | None = None,
///     ntc_connected: bool | None = None,
///     charging_limited: bool | None = None,
///     temp_control_active: bool | None = None,
///     battery_connected: bool | None = None,
///     charging_status: int | None = None,
///     power_status: int | None = None,
/// ) -> None:
///     """
///     Set emulated battery/power state with fine-grained control.
///     Only available on emulator. Pass None to leave a field unchanged.
///     charging_status: 0=idle, 1=discharging, 2=charging (auto-derived from
///       connections if not set)
///     power_status: 0=hibernate, 1=charging, 2=suspend, 3=shutting_down,
///       4=power_save, 5=active
///     """
STATIC mp_obj_t mod_trezorio_pm_set_emu_battery_state(size_t n_args,
                                                      const mp_obj_t* pos_args,
                                                      mp_map_t* kw_args) {
  static const mp_arg_t allowed_args[] = {
      {MP_QSTR_soc, MP_ARG_OBJ, {.u_rom_obj = MP_ROM_NONE}},
      {MP_QSTR_usb_connected, MP_ARG_OBJ, {.u_rom_obj = MP_ROM_NONE}},
      {MP_QSTR_wireless_connected, MP_ARG_OBJ, {.u_rom_obj = MP_ROM_NONE}},
      {MP_QSTR_ntc_connected, MP_ARG_OBJ, {.u_rom_obj = MP_ROM_NONE}},
      {MP_QSTR_charging_limited, MP_ARG_OBJ, {.u_rom_obj = MP_ROM_NONE}},
      {MP_QSTR_temp_control_active, MP_ARG_OBJ, {.u_rom_obj = MP_ROM_NONE}},
      {MP_QSTR_battery_connected, MP_ARG_OBJ, {.u_rom_obj = MP_ROM_NONE}},
      {MP_QSTR_charging_status, MP_ARG_OBJ, {.u_rom_obj = MP_ROM_NONE}},
      {MP_QSTR_power_status, MP_ARG_OBJ, {.u_rom_obj = MP_ROM_NONE}},
  };

  mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
  mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args),
                   allowed_args, args);

  // Convert: None -> -1, otherwise get int/bool value
  int soc =
      (args[0].u_obj == mp_const_none) ? -1 : mp_obj_get_int(args[0].u_obj);
  int usb_connected =
      (args[1].u_obj == mp_const_none) ? -1 : mp_obj_is_true(args[1].u_obj);
  int wireless_connected =
      (args[2].u_obj == mp_const_none) ? -1 : mp_obj_is_true(args[2].u_obj);
  int ntc_connected =
      (args[3].u_obj == mp_const_none) ? -1 : mp_obj_is_true(args[3].u_obj);
  int charging_limited =
      (args[4].u_obj == mp_const_none) ? -1 : mp_obj_is_true(args[4].u_obj);
  int temp_control_active =
      (args[5].u_obj == mp_const_none) ? -1 : mp_obj_is_true(args[5].u_obj);
  int battery_connected =
      (args[6].u_obj == mp_const_none) ? -1 : mp_obj_is_true(args[6].u_obj);
  int charging_status =
      (args[7].u_obj == mp_const_none) ? -1 : mp_obj_get_int(args[7].u_obj);
  int power_status =
      (args[8].u_obj == mp_const_none) ? -1 : mp_obj_get_int(args[8].u_obj);

  pm_set_emu_battery_state(soc, usb_connected, wireless_connected,
                           ntc_connected, charging_limited, temp_control_active,
                           battery_connected, charging_status, power_status);

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_trezorio_pm_set_emu_battery_state_obj, 0,
                                  mod_trezorio_pm_set_emu_battery_state);
#endif

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
#ifdef TREZOR_EMULATOR
    {MP_ROM_QSTR(MP_QSTR_set_emu_battery_state),
     MP_ROM_PTR(&mod_trezorio_pm_set_emu_battery_state_obj)},
#endif

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
    {MP_ROM_QSTR(MP_QSTR_EVENT_TEMP_CONTROL_ACTIVE_CHANGED),
     MP_ROM_INT(1 << 6)},
    {MP_ROM_QSTR(MP_QSTR_EVENT_BATTERY_CONNECTED_CHANGED), MP_ROM_INT(1 << 7)},
    {MP_ROM_QSTR(MP_QSTR_EVENT_BATTERY_OCV_JUMP_DETECTED), MP_ROM_INT(1 << 8)},
    {MP_ROM_QSTR(MP_QSTR_EVENT_BATTERY_TEMP_JUMP_UPDATED), MP_ROM_INT(1 << 9)},
    {MP_ROM_QSTR(MP_QSTR_EVENT_SOC_UPDATED), MP_ROM_INT(1 << 10)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_pm_globals,
                            mod_trezorio_pm_globals_table);

STATIC const mp_obj_module_t mod_trezorio_pm_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&mod_trezorio_pm_globals,
};
