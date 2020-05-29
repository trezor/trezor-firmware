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
#include "py/objstr.h"
#include "py/runtime.h"

#include "i18n-block.h"

#if MICROPY_PY_TREZORI18N

/// def init() -> None:
///     """
///     Gets
///     """
STATIC mp_obj_t mod_trezori18n_init(void) {
  i18n_init();
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_trezori18n_init_obj, mod_trezori18n_init);

/// def get(id: int) -> str:
///     """
///     Gets
///     """
STATIC mp_obj_t mod_trezori18n_get(mp_obj_t _id) {
  uint16_t id = trezor_obj_get_uint(_id);
  uint16_t len;
  const char *str = i18n_get(id, &len);
  if (!str) {
    return mp_const_none;
  }
  return mp_obj_new_str_copy(&mp_type_str, (const uint8_t *)str, len);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezori18n_get_obj, mod_trezori18n_get);

STATIC const mp_rom_map_elem_t mp_module_trezori18n_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezori18n)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&mod_trezori18n_init_obj)},
    {MP_ROM_QSTR(MP_QSTR_get), MP_ROM_PTR(&mod_trezori18n_get_obj)},
};

STATIC MP_DEFINE_CONST_DICT(mp_module_trezori18n_globals,
                            mp_module_trezori18n_globals_table);

const mp_obj_module_t mp_module_trezori18n = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mp_module_trezori18n_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezori18n, mp_module_trezori18n,
                   MICROPY_PY_TREZORI18N);

#endif  // MICROPY_PY_TREZORI18N
