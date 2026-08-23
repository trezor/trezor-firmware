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

#include <io/nfc.h>

/// package: trezorio.nfc
///
/// def start() -> None:
///     """Start NFC stack."""
///
/// def stop() -> None:
///     """Stop NFC stack."""

static void raise_on_error(ts_t status) {
  if (ts_error(status)) {
    mp_raise_OSError(ts_code(status));
  }
}

static mp_obj_t mod_trezorio_nfc_start() {
  raise_on_error(nfc_init());
  // TODO: deinit on start error?
  raise_on_error(nfc_start_discovery());
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_nfc_start_obj,
                                 mod_trezorio_nfc_start);

static mp_obj_t mod_trezorio_nfc_stop() {
  ts_t status = nfc_stop_discovery();
  nfc_deinit();
  raise_on_error(status);
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_0(mod_trezorio_nfc_stop_obj,
                                 mod_trezorio_nfc_stop);

static const mp_rom_map_elem_t mod_trezorio_nfc_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_nfc)},
    {MP_ROM_QSTR(MP_QSTR_start), MP_ROM_PTR(&mod_trezorio_nfc_start_obj)},
    {MP_ROM_QSTR(MP_QSTR_stop), MP_ROM_PTR(&mod_trezorio_nfc_stop_obj)},
};
static MP_DEFINE_CONST_DICT(mod_trezorio_nfc_globals,
                            mod_trezorio_nfc_globals_table);

static const mp_obj_module_t mod_trezorio_nfc_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorio_nfc_globals,
};
