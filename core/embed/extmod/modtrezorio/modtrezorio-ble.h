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

#include "ble/dfu.h"

/// package: trezorio.ble

/// def update_init(data: bytes, binsize: int) -> int:
///     """
///     Initializes the BLE firmware update
///     """
STATIC mp_obj_t mod_trezorio_BLE_update_init(mp_obj_t data, mp_obj_t binsize) {
  mp_buffer_info_t buffer = {0};
  mp_int_t binsize_int = mp_obj_get_int(binsize);

  mp_get_buffer_raise(data, &buffer, MP_BUFFER_READ);

  dfu_result_t result = dfu_update_init(buffer.buf, buffer.len, binsize_int);
  if (result == DFU_NEXT_CHUNK) {
    return mp_obj_new_int(0);
  } else if (result == DFU_SUCCESS) {
    return mp_obj_new_int(1);
  } else {
    mp_raise_msg(&mp_type_RuntimeError, "Upload failed.");
  }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_BLE_update_init_obj,
                                 mod_trezorio_BLE_update_init);

/// def update_chunk(chunk: bytes) -> int:
///     """
///     Writes next chunk of BLE firmware update
///     """
STATIC mp_obj_t mod_trezorio_BLE_update_chunk(mp_obj_t data) {
  mp_buffer_info_t buffer = {0};

  mp_get_buffer_raise(data, &buffer, MP_BUFFER_READ);

  dfu_result_t result = dfu_update_chunk(buffer.buf, buffer.len);

  if (result == DFU_NEXT_CHUNK) {
    return mp_obj_new_int(0);
  } else if (result == DFU_SUCCESS) {
    return mp_obj_new_int(1);
  } else {
    mp_raise_msg(&mp_type_RuntimeError, "Upload failed.");
  }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_BLE_update_chunk_obj,
                                 mod_trezorio_BLE_update_chunk);

/// def write(self, msg: bytes) -> int:
///     """
///     Sends message using BLE.
///     """
STATIC mp_obj_t mod_trezorio_BLE_write(mp_obj_t self, mp_obj_t msg) {
  mp_buffer_info_t buf = {0};
  mp_get_buffer_raise(msg, &buf, MP_BUFFER_READ);
  ble_int_comm_send(buf.buf, buf.len,
                    ble_last_internal ? INTERNAL_MESSAGE : EXTERNAL_MESSAGE);
  return MP_OBJ_NEW_SMALL_INT(buf.len);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_BLE_write_obj,
                                 mod_trezorio_BLE_write);

STATIC const mp_rom_map_elem_t mod_trezorio_BLE_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_ble)},
    {MP_ROM_QSTR(MP_QSTR_update_init),
     MP_ROM_PTR(&mod_trezorio_BLE_update_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_update_chunk),
     MP_ROM_PTR(&mod_trezorio_BLE_update_chunk_obj)},
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&mod_trezorio_BLE_write_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_BLE_globals,
                            mod_trezorio_BLE_globals_table);

STATIC const mp_obj_module_t mod_trezorio_BLE_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorio_BLE_globals};
