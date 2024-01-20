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

#include <stdio.h>
#include <sys/mman.h>
#include "common.h"
#include "embed/extmod/trezorobj.h"
#include "py/mpconfig.h"
#include "sdcard.h"
#include "sdcard_emu_mock.h"

/// package: trezorio.sdcard_switcher

/// def insert(
///     card_sn: int,
///     capacity_bytes: int | None = 122_945_536,
///     manuf_id: int | None = 39,
/// ) -> None:
///     """
///     Inserts SD card to the emulator.
///     """
STATIC mp_obj_t mod_trezorio_sdcard_switcher_insert(size_t n_args,
                                                    const mp_obj_t *args,
                                                    mp_map_t *kw_args) {
  STATIC const mp_arg_t allowed_args[] = {
      {MP_QSTR_card_sn, MP_ARG_REQUIRED | MP_ARG_INT},
      {MP_QSTR_capacity_bytes,
       MP_ARG_OBJ,
       {.u_rom_obj = MP_ROM_INT(122945536)}},
      {MP_QSTR_manuf_id, MP_ARG_OBJ, {.u_rom_obj = MP_ROM_INT(39)}},
  };

  mp_arg_val_t vals[MP_ARRAY_SIZE(allowed_args)] = {0};
  mp_arg_parse_all(n_args, args, kw_args, MP_ARRAY_SIZE(allowed_args),
                   allowed_args, vals);

  const mp_int_t card_sn = vals[0].u_int;

  // FIXME: default arguments should be somehow accessible by .u_rom_obj, no?
  mp_int_t capacity_bytes;
  if (vals[1].u_obj == mp_const_none) {
    /* capacity_bytes = mp_obj_get_int(vals[1].u_rom_obj); */
    capacity_bytes = 122945536;
  } else {
    capacity_bytes = mp_obj_get_int(vals[1].u_obj);
  }
  mp_int_t manuf_id;
  if (vals[2].u_obj == mp_const_none) {
    /* manuf_id = mp_obj_get_int(vals[2].u_rom_obj); */
    manuf_id = 39;
  } else {
    manuf_id = mp_obj_get_int(vals[2].u_obj);
  }

  CHECK_PARAM_RANGE(card_sn, 1, 16)
  CHECK_PARAM_RANGE(capacity_bytes, ONE_MEBIBYTE,
                    1024 * ONE_MEBIBYTE)  // capacity between 1 MiB and 1 GiB

  sdcard_mock.inserted = sectrue;
  set_sdcard_mock_filename((int)card_sn);
  sdcard_mock.buffer = NULL;
  sdcard_mock.serial_number = card_sn;
  sdcard_mock.capacity_bytes = capacity_bytes;
  sdcard_mock.blocks = capacity_bytes / SDCARD_BLOCK_SIZE;
  sdcard_mock.manuf_ID = manuf_id;
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_trezorio_sdcard_switcher_insert_obj, 1,
                                  mod_trezorio_sdcard_switcher_insert);

/// def eject() -> None:
///     """
///     Ejects SD card from the emulator.
///     """
STATIC mp_obj_t mod_trezorio_sdcard_switcher_eject() {
  sdcard_mock.inserted = secfalse;

  if (sdcard_mock.buffer != NULL) {
    // TODO repetion with unix/sdcard.c code
    int r = munmap(sdcard_mock.buffer, sdcard_mock.capacity_bytes);
    ensure(sectrue * (r == 0), "munmap failed");
    sdcard_mock.buffer = NULL;
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_sdcard_switcher_eject_obj,
                                 mod_trezorio_sdcard_switcher_eject);

STATIC const mp_rom_map_elem_t mod_trezorio_sdcard_switcher_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_sdcard_switcher)},
    {MP_ROM_QSTR(MP_QSTR_insert),
     MP_ROM_PTR(&mod_trezorio_sdcard_switcher_insert_obj)},
    {MP_ROM_QSTR(MP_QSTR_eject),
     MP_ROM_PTR(&mod_trezorio_sdcard_switcher_eject_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_sdcard_switcher_globals,
                            mod_trezorio_sdcard_switcher_globals_table);

STATIC const mp_obj_module_t mod_trezorio_sdcard_switcher_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorio_sdcard_switcher_globals,
};
