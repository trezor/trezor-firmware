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

// #include "ble/dfu.h"
// #include "ble/messages.h"

/// package: trezorio.ble

// /// def update_init(data: bytes, binsize: int) -> int:
// ///     """
// ///     Initializes the BLE firmware update
// ///     """
// STATIC mp_obj_t mod_trezorio_BLE_update_init(mp_obj_t data, mp_obj_t binsize)
// {
//   mp_buffer_info_t buffer = {0};
//   mp_int_t binsize_int = mp_obj_get_int(binsize);
//
//   mp_get_buffer_raise(data, &buffer, MP_BUFFER_READ);
//
//   ble_set_dfu_mode(true);
//
//   dfu_result_t result = dfu_update_init(buffer.buf, buffer.len, binsize_int);
//   if (result == DFU_NEXT_CHUNK) {
//     return mp_obj_new_int(0);
//   } else if (result == DFU_SUCCESS) {
//     ble_set_dfu_mode(false);
//     return mp_obj_new_int(1);
//   } else {
//     ble_set_dfu_mode(false);
//     mp_raise_msg(&mp_type_RuntimeError, "Upload failed.");
//   }
// }
// STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_BLE_update_init_obj,
//                                  mod_trezorio_BLE_update_init);
//
// /// def update_chunk(chunk: bytes) -> int:
// ///     """
// ///     Writes next chunk of BLE firmware update
// ///     """
// STATIC mp_obj_t mod_trezorio_BLE_update_chunk(mp_obj_t data) {
//   mp_buffer_info_t buffer = {0};
//
//   mp_get_buffer_raise(data, &buffer, MP_BUFFER_READ);
//
//   dfu_result_t result = dfu_update_chunk(buffer.buf, buffer.len);
//
//   if (result == DFU_NEXT_CHUNK) {
//     return mp_obj_new_int(0);
//   } else if (result == DFU_SUCCESS) {
//     ble_set_dfu_mode(false);
//     return mp_obj_new_int(1);
//   } else {
//     ble_set_dfu_mode(false);
//     mp_raise_msg(&mp_type_RuntimeError, "Upload failed.");
//   }
// }
// STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_BLE_update_chunk_obj,
//                                  mod_trezorio_BLE_update_chunk);

/// def write(self, msg: bytes) -> int:
///     """
///     Sends message over BLE
///     """
STATIC mp_obj_t mod_trezorio_BLE_write(mp_obj_t self, mp_obj_t msg) {
  mp_buffer_info_t buf = {0};
  mp_get_buffer_raise(msg, &buf, MP_BUFFER_READ);
  bool success = ble_write(buf.buf, buf.len);
  if (success) {
    return MP_OBJ_NEW_SMALL_INT(buf.len);
  } else {
    return MP_OBJ_NEW_SMALL_INT(-1);
  }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_BLE_write_obj,
                                 mod_trezorio_BLE_write);

/// def erase_bonds() -> None:
///     """
///     Erases all BLE bonds
///     """
STATIC mp_obj_t mod_trezorio_BLE_erase_bonds(void) {
  ble_issue_command(BLE_ERASE_BONDS);
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_BLE_erase_bonds_obj,
                                 mod_trezorio_BLE_erase_bonds);

/// def start_comm() -> None:
///     """
///     Start communication with BLE chip
///     """
STATIC mp_obj_t mod_trezorio_BLE_start_comm(void) {
  ble_start();
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_BLE_start_comm_obj,
                                 mod_trezorio_BLE_start_comm);

/// def start_advertising(whitelist: bool) -> None:
///     """
///     Start advertising
///     """
STATIC mp_obj_t mod_trezorio_BLE_start_advertising(mp_obj_t whitelist) {
  bool whitelist_bool = mp_obj_is_true(whitelist);

  ble_issue_command(whitelist_bool ? BLE_SWITCH_ON : BLE_PAIRING_MODE);
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_BLE_start_advertising_obj,
                                 mod_trezorio_BLE_start_advertising);

/// def stop_advertising(whitelist: bool) -> None:
///     """
///     Stop advertising
///     """
STATIC mp_obj_t mod_trezorio_BLE_stop_advertising(void) {
  ble_issue_command(BLE_SWITCH_OFF);
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_BLE_stop_advertising_obj,
                                 mod_trezorio_BLE_stop_advertising);

/// def disconnect() -> None:
///     """
///     Disconnect BLE
///     """
STATIC mp_obj_t mod_trezorio_BLE_disconnect(void) {
  ble_issue_command(BLE_DISCONNECT);
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_BLE_disconnect_obj,
                                 mod_trezorio_BLE_disconnect);

STATIC const mp_rom_map_elem_t mod_trezorio_BLE_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_ble)},
    // {MP_ROM_QSTR(MP_QSTR_update_init),
    //  MP_ROM_PTR(&mod_trezorio_BLE_update_init_obj)},
    // {MP_ROM_QSTR(MP_QSTR_update_chunk),
    //  MP_ROM_PTR(&mod_trezorio_BLE_update_chunk_obj)},
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&mod_trezorio_BLE_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_erase_bonds),
     MP_ROM_PTR(&mod_trezorio_BLE_erase_bonds_obj)},
    {MP_ROM_QSTR(MP_QSTR_start_comm),
     MP_ROM_PTR(&mod_trezorio_BLE_start_comm_obj)},
    {MP_ROM_QSTR(MP_QSTR_start_advertising),
     MP_ROM_PTR(&mod_trezorio_BLE_start_advertising_obj)},
    {MP_ROM_QSTR(MP_QSTR_stop_advertising),
     MP_ROM_PTR(&mod_trezorio_BLE_stop_advertising_obj)},
    {MP_ROM_QSTR(MP_QSTR_disconnect),
     MP_ROM_PTR(&mod_trezorio_BLE_disconnect_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_BLE_globals,
                            mod_trezorio_BLE_globals_table);

STATIC const mp_obj_module_t mod_trezorio_BLE_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorio_BLE_globals};
