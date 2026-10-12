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

#include <trezor_model.h>

#include <io/display.h>
#include <io/display_utils.h>

/// class Display:
///     """
///     Provide access to device display.
///     """
///     WIDTH: int  # display width in pixels
///     HEIGHT: int  # display height in pixels

typedef struct _mp_obj_Display_t {
  mp_obj_base_t base;
} mp_obj_Display_t;

/// def __init__(self) -> None:
///     """
///     Initialize the display.
///     """
static mp_obj_t mod_trezorui_Display_make_new(const mp_obj_type_t *type,
                                              size_t n_args, size_t n_kw,
                                              const mp_obj_t *args) {
  mp_arg_check_num(n_args, n_kw, 0, 0, false);
  mp_obj_Display_t *o = mp_obj_malloc(mp_obj_Display_t, type);
  return MP_OBJ_FROM_PTR(o);
}

/// def orientation(self, degrees: int | None = None) -> int:
///     """
///     Sets display orientation to 0, 90, 180 or 270 degrees.
///     Everything needs to be redrawn again when this function is used.
///     Call without the degrees parameter to just perform the read of the
///     value.
///     """
static mp_obj_t mod_trezorui_Display_orientation(size_t n_args,
                                                 const mp_obj_t *args) {
  mp_int_t deg;
  if (n_args > 1) {
    deg = mp_obj_get_int(args[1]);
    if (deg != 0 && deg != 90 && deg != 180 && deg != 270) {
      mp_raise_ValueError(MP_ERROR_TEXT("Value must be 0, 90, 180 or 270"));
    }
    deg = display_set_orientation(deg);
  } else {
    deg = display_get_orientation();
  }
  return MP_OBJ_NEW_SMALL_INT(deg);
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorui_Display_orientation_obj,
                                           1, 2,
                                           mod_trezorui_Display_orientation);
/// def record_start(
///     self, target_directory: AnyBytes, refresh_index: int
/// ) -> None:
///     """
///     Starts screen recording with specified target directory and refresh
///     index.
///     """
static mp_obj_t mod_trezorui_Display_record_start(mp_obj_t self,
                                                  mp_obj_t target_directory,
                                                  mp_obj_t refresh_index) {
  mp_buffer_info_t target_dir;
  mp_int_t refresh_idx = mp_obj_get_int(refresh_index);
  mp_get_buffer_raise(target_directory, &target_dir, MP_BUFFER_READ);
  display_record_start(target_dir.buf, target_dir.len, refresh_idx);
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorui_Display_record_start_obj,
                                 mod_trezorui_Display_record_start);

/// def record_stop(self) -> None:
///     """
///     Stops screen recording.
///     """
static mp_obj_t mod_trezorui_Display_record_stop(mp_obj_t self) {
  display_record_stop();
  return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorui_Display_record_stop_obj,
                                 mod_trezorui_Display_record_stop);

/// def record_read(self) -> tuple[list[bytes], bytes]:
///     """
///     Returns the hashes of distinct screens painted since the previous call
///     and the running hash over all screens since the recording started.
///     """
static mp_obj_t mod_trezorui_Display_record_read(mp_obj_t self) {
  display_record_info_t info;
  display_record_read(&info);

  mp_obj_t hashes = mp_obj_new_list(0, NULL);
  for (uint32_t i = 0; i < info.count && i < DISPLAY_RECORD_MAX_HASHES; i++) {
    mp_obj_list_append(
        hashes, mp_obj_new_bytes(info.hashes[i], DISPLAY_RECORD_HASH_SIZE));
  }

  mp_obj_t items[2] = {
      hashes,
      mp_obj_new_bytes(info.digest, DISPLAY_RECORD_HASH_SIZE),
  };
  return mp_obj_new_tuple(2, items);
}
static MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorui_Display_record_read_obj,
                                 mod_trezorui_Display_record_read);

/// def record_read_screen(
///     self, offset: int, length: int
/// ) -> tuple[int, int, str, bytes, int, bytes]:
///     """
///     Reads a chunk of the displayed screen, converted the way the recorded
///     hashes are computed. Returns (width, height, mode, hash of the last
///     recorded screen, total size, data).
///     """
static mp_obj_t mod_trezorui_Display_record_read_screen(mp_obj_t self,
                                                        mp_obj_t offset,
                                                        mp_obj_t length) {
  mp_int_t off = mp_obj_get_int(offset);
  mp_int_t len = mp_obj_get_int(length);
  if (off < 0 || len < 0 || len > DISPLAY_RECORD_CHUNK_SIZE) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid chunk"));
  }

  display_record_screen_t info;
  vstr_t data;
  vstr_init_len(&data, len);
  size_t copied =
      display_record_read_screen(&info, off, (uint8_t *)data.buf, len);
  data.len = copied;

  mp_obj_t items[6] = {
      MP_OBJ_NEW_SMALL_INT(info.width),
      MP_OBJ_NEW_SMALL_INT(info.height),
      mp_obj_new_str(info.mode, strlen(info.mode)),
      mp_obj_new_bytes(info.hash, DISPLAY_RECORD_HASH_SIZE),
      mp_obj_new_int_from_uint(info.total),
      mp_obj_new_bytes_from_vstr(&data),
  };
  return mp_obj_new_tuple(6, items);
}
static MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorui_Display_record_read_screen_obj,
                                 mod_trezorui_Display_record_read_screen);

static const mp_rom_map_elem_t mod_trezorui_Display_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_orientation),
     MP_ROM_PTR(&mod_trezorui_Display_orientation_obj)},
    {MP_ROM_QSTR(MP_QSTR_record_start),
     MP_ROM_PTR(&mod_trezorui_Display_record_start_obj)},
    {MP_ROM_QSTR(MP_QSTR_record_stop),
     MP_ROM_PTR(&mod_trezorui_Display_record_stop_obj)},
    {MP_ROM_QSTR(MP_QSTR_record_read),
     MP_ROM_PTR(&mod_trezorui_Display_record_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_record_read_screen),
     MP_ROM_PTR(&mod_trezorui_Display_record_read_screen_obj)},
    {MP_ROM_QSTR(MP_QSTR_WIDTH), MP_ROM_INT(DISPLAY_RESX)},
    {MP_ROM_QSTR(MP_QSTR_HEIGHT), MP_ROM_INT(DISPLAY_RESY)},
};
static MP_DEFINE_CONST_DICT(mod_trezorui_Display_locals_dict,
                            mod_trezorui_Display_locals_dict_table);

// clang-format off
MP_DEFINE_CONST_OBJ_TYPE(mod_trezorui_Display_type,
  MP_QSTR_Display, MP_TYPE_FLAG_NONE,
  make_new, mod_trezorui_Display_make_new,
  locals_dict, &mod_trezorui_Display_locals_dict);
// clang-format on
