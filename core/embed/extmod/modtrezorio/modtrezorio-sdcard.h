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

#include "embed/extmod/trezorobj.h"
#include "py/mperrno.h"

#include "sdcard.h"

/// package: trezorio.sdcard

/// BLOCK_SIZE: int  # size of SD card block

/// def is_present() -> bool:
///     """
///     Returns True if SD card is detected, False otherwise.
///     """
STATIC mp_obj_t mod_trezorio_sdcard_is_present() {
  return mp_obj_new_bool(sdcard_is_present());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_sdcard_is_present_obj,
                                 mod_trezorio_sdcard_is_present);

/// def power_on() -> None:
///     """
///     Power on the SD card interface.
///     Raises OSError if the SD card cannot be powered on, e.g., when there
///     is no SD card inserted.
///     """
STATIC mp_obj_t mod_trezorio_sdcard_power_on() {
  if (sectrue != sdcard_power_on()) {
    mp_raise_OSError(MP_EIO);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_sdcard_power_on_obj,
                                 mod_trezorio_sdcard_power_on);

/// def power_off() -> None:
///     """
///     Power off the SD card interface.
///     """
STATIC mp_obj_t mod_trezorio_sdcard_power_off() {
  /* XXX should this call happen inside sdcard_power_off()? */
  _fatfs_unmount_instance();
  sdcard_power_off();
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_sdcard_power_off_obj,
                                 mod_trezorio_sdcard_power_off);

/// def capacity() -> int:
///     """
///     Returns capacity of the SD card in bytes, or zero if not present.
///     """
STATIC mp_obj_t mod_trezorio_sdcard_capacity() {
  return mp_obj_new_int_from_ull(sdcard_get_capacity_in_bytes());
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_sdcard_capacity_obj,
                                 mod_trezorio_sdcard_capacity);

/// def read(block_num: int, buf: bytearray) -> None:
///     """
///     Reads blocks starting with block_num from the SD card into buf.
///     Number of bytes read is length of buf rounded down to multiply of
///     SDCARD_BLOCK_SIZE. Returns True if in case of success, False otherwise.
///     """
STATIC mp_obj_t mod_trezorio_sdcard_read(mp_obj_t block_num, mp_obj_t buf) {
  uint32_t block = trezor_obj_get_uint(block_num);
  mp_buffer_info_t bufinfo = {0};
  mp_get_buffer_raise(buf, &bufinfo, MP_BUFFER_WRITE);
  if (sectrue !=
      sdcard_read_blocks(bufinfo.buf, block, bufinfo.len / SDCARD_BLOCK_SIZE)) {
    mp_raise_OSError(MP_EIO);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_sdcard_read_obj,
                                 mod_trezorio_sdcard_read);

/// def write(block_num: int, buf: bytes) -> None:
///     """
///     Writes blocks starting with block_num from buf to the SD card.
///     Number of bytes written is length of buf rounded down to multiply of
///     SDCARD_BLOCK_SIZE. Returns True if in case of success, False otherwise.
///     """
STATIC mp_obj_t mod_trezorio_sdcard_write(mp_obj_t block_num, mp_obj_t buf) {
  uint32_t block = trezor_obj_get_uint(block_num);
  mp_buffer_info_t bufinfo = {0};
  mp_get_buffer_raise(buf, &bufinfo, MP_BUFFER_READ);
  if (sectrue != sdcard_write_blocks(bufinfo.buf, block,
                                     bufinfo.len / SDCARD_BLOCK_SIZE)) {
    mp_raise_OSError(MP_EIO);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_sdcard_write_obj,
                                 mod_trezorio_sdcard_write);

STATIC const mp_rom_map_elem_t mod_trezorio_sdcard_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_sdcard)},

    {MP_ROM_QSTR(MP_QSTR_is_present),
     MP_ROM_PTR(&mod_trezorio_sdcard_is_present_obj)},
    {MP_ROM_QSTR(MP_QSTR_power_on),
     MP_ROM_PTR(&mod_trezorio_sdcard_power_on_obj)},
    {MP_ROM_QSTR(MP_QSTR_power_off),
     MP_ROM_PTR(&mod_trezorio_sdcard_power_off_obj)},
    {MP_ROM_QSTR(MP_QSTR_capacity),
     MP_ROM_PTR(&mod_trezorio_sdcard_capacity_obj)},
    {MP_ROM_QSTR(MP_QSTR_BLOCK_SIZE), MP_ROM_INT(SDCARD_BLOCK_SIZE)},
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&mod_trezorio_sdcard_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&mod_trezorio_sdcard_write_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_sdcard_globals,
                            mod_trezorio_sdcard_globals_table);

STATIC const mp_obj_module_t mod_trezorio_sdcard_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorio_sdcard_globals,
};
