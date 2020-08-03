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

#include "py/objstr.h"

#include "embed/extmod/trezorobj.h"

#include "crc.h"

/// package: trezorcrypto.crc

/// def crc32(data: bytes, crc: int = 0) -> int:
///     """
///     Computes a CRC32 checksum of `data`.
///     """
mp_obj_t mod_trezorcrypto_crc_crc32(size_t n_args, const mp_obj_t *args) {
  mp_buffer_info_t bufinfo = {0};
  mp_get_buffer_raise(args[0], &bufinfo, MP_BUFFER_READ);
  uint32_t crc = (n_args > 1) ? trezor_obj_get_uint(args[1]) : 0;
  crc = checksum_crc32(bufinfo.buf, bufinfo.len, crc ^ 0xffffffff);
  return mp_obj_new_int_from_uint(crc ^ 0xffffffff);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_crc_crc32_obj, 1, 2,
                                           mod_trezorcrypto_crc_crc32);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_crc_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_crc)},
    {MP_ROM_QSTR(MP_QSTR_crc32), MP_ROM_PTR(&mod_trezorcrypto_crc_crc32_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_crc_globals,
                            mod_trezorcrypto_crc_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_crc_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_crc_globals,
};
