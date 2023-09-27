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

#include "display.h"

/// class Display:
///     """
///     Provide access to device display.
///     """
///
///     WIDTH: int  # display width in pixels
///     HEIGHT: int  # display height in pixels
///     FONT_MONO: int  # id of monospace font
///     FONT_NORMAL: int  # id of normal-width font
///     FONT_BOLD: int  # id of bold-width font
///     FONT_DEMIBOLD: int  # id of demibold font
///
typedef struct _mp_obj_Display_t {
  mp_obj_base_t base;
} mp_obj_Display_t;

/// def __init__(self) -> None:
///     """
///     Initialize the display.
///     """
STATIC mp_obj_t mod_trezorui_Display_make_new(const mp_obj_type_t *type,
                                              size_t n_args, size_t n_kw,
                                              const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 0, 0, false);
  mp_obj_Display_t *o = mp_obj_malloc(mp_obj_Display_t, type);
  return MP_OBJ_FROM_PTR(o);
}

/// def refresh(self) -> None:
///     """
///     Refresh display (update screen).
///     """
STATIC mp_obj_t mod_trezorui_Display_refresh(mp_obj_t self) {
  display_refresh();
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorui_Display_refresh_obj,
                                 mod_trezorui_Display_refresh);

/// def bar(self, x: int, y: int, w: int, h: int, color: int) -> None:
///     """
///     Renders a bar at position (x,y = upper left corner) with width w and
///     height h of color color.
///     """
STATIC mp_obj_t mod_trezorui_Display_bar(size_t n_args, const mp_obj_t *args) {
  mp_int_t x = mp_obj_get_int(args[1]);
  mp_int_t y = mp_obj_get_int(args[2]);
  mp_int_t w = mp_obj_get_int(args[3]);
  mp_int_t h = mp_obj_get_int(args[4]);
  uint16_t c = mp_obj_get_int(args[5]);
  display_bar(x, y, w, h, c);
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_bar_obj, 6, 6,
                                           mod_trezorui_Display_bar);

/// def orientation(self, degrees: int | None = None) -> int:
///     """
///     Sets display orientation to 0, 90, 180 or 270 degrees.
///     Everything needs to be redrawn again when this function is used.
///     Call without the degrees parameter to just perform the read of the
///     value.
///     """
STATIC mp_obj_t mod_trezorui_Display_orientation(size_t n_args,
                                                 const mp_obj_t *args) {
  mp_int_t deg;
  if (n_args > 1) {
    deg = mp_obj_get_int(args[1]);
    if (deg != 0 && deg != 90 && deg != 180 && deg != 270) {
      mp_raise_ValueError("Value must be 0, 90, 180 or 270");
    }
    deg = display_orientation(deg);
  } else {
    deg = display_orientation(-1);
  }
  return MP_OBJ_NEW_SMALL_INT(deg);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_orientation_obj,
                                           1, 2,
                                           mod_trezorui_Display_orientation);

/// def backlight(self, val: int | None = None) -> int:
///     """
///     Sets backlight intensity to the value specified in val.
///     Call without the val parameter to just perform the read of the value.
///     """
STATIC mp_obj_t mod_trezorui_Display_backlight(size_t n_args,
                                               const mp_obj_t *args) {
  mp_int_t val;
  if (n_args > 1) {
    val = mp_obj_get_int(args[1]);
    if (val < 0 || val > 255) {
      mp_raise_ValueError("Value must be between 0 and 255");
    }
    val = display_backlight(val);
  } else {
    val = display_backlight(-1);
  }
  return MP_OBJ_NEW_SMALL_INT(val);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_backlight_obj,
                                           1, 2,
                                           mod_trezorui_Display_backlight);

/// def save(self, prefix: str) -> None:
///     """
///     Saves current display contents to PNG file with given prefix.
///     """
STATIC mp_obj_t mod_trezorui_Display_save(mp_obj_t self, mp_obj_t prefix) {
  mp_buffer_info_t pfx = {0};
  mp_get_buffer_raise(prefix, &pfx, MP_BUFFER_READ);
  if (pfx.len > 0) {
    display_save(pfx.buf);
  }
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorui_Display_save_obj,
                                 mod_trezorui_Display_save);

/// def clear_save(self) -> None:
///     """
///     Clears buffers in display saving.
///     """
STATIC mp_obj_t mod_trezorui_Display_clear_save(mp_obj_t self) {
  display_clear_save();
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorui_Display_clear_save_obj,
                                 mod_trezorui_Display_clear_save);

STATIC const mp_rom_map_elem_t mod_trezorui_Display_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_refresh),
     MP_ROM_PTR(&mod_trezorui_Display_refresh_obj)},
    {MP_ROM_QSTR(MP_QSTR_bar), MP_ROM_PTR(&mod_trezorui_Display_bar_obj)},
    {MP_ROM_QSTR(MP_QSTR_orientation),
     MP_ROM_PTR(&mod_trezorui_Display_orientation_obj)},
    {MP_ROM_QSTR(MP_QSTR_backlight),
     MP_ROM_PTR(&mod_trezorui_Display_backlight_obj)},
    {MP_ROM_QSTR(MP_QSTR_save), MP_ROM_PTR(&mod_trezorui_Display_save_obj)},
    {MP_ROM_QSTR(MP_QSTR_clear_save),
     MP_ROM_PTR(&mod_trezorui_Display_clear_save_obj)},
    {MP_ROM_QSTR(MP_QSTR_WIDTH), MP_ROM_INT(DISPLAY_RESX)},
    {MP_ROM_QSTR(MP_QSTR_HEIGHT), MP_ROM_INT(DISPLAY_RESY)},
    {MP_ROM_QSTR(MP_QSTR_FONT_NORMAL), MP_ROM_INT(FONT_NORMAL)},
    {MP_ROM_QSTR(MP_QSTR_FONT_BOLD), MP_ROM_INT(FONT_BOLD)},
    {MP_ROM_QSTR(MP_QSTR_FONT_DEMIBOLD), MP_ROM_INT(FONT_DEMIBOLD)},
    {MP_ROM_QSTR(MP_QSTR_FONT_MONO), MP_ROM_INT(FONT_MONO)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorui_Display_locals_dict,
                            mod_trezorui_Display_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorui_Display_type = {
    {&mp_type_type},
    .name = MP_QSTR_Display,
    .make_new = mod_trezorui_Display_make_new,
    .locals_dict = (void *)&mod_trezorui_Display_locals_dict,
};
