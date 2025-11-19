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

#include <py/obj.h>
#include <py/runtime.h>

#include <trezor_rtl.h>

#include <util/app_loader.h>

/// package: trezorapp

/// class AppImage:
///     """
///     Application image image.
///     """
typedef struct _mp_obj_AppImage_t {
  mp_obj_base_t base;
  app_cache_image_t* image;
} mp_obj_AppImage_t;

/// def write(self, offset: int, data: AnyBytes) -> None:
///     """
///     Writes data to the application image at the specified offset.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_write(mp_obj_t self, mp_obj_t offset_obj,
                                             mp_obj_t data_obj) {
  mp_obj_AppImage_t* o = MP_OBJ_TO_PTR(self);
  app_cache_image_t* image = o->image;

  mp_buffer_info_t bufinfo = {0};
  mp_get_buffer_raise(data_obj, &bufinfo, MP_BUFFER_READ);

  uintptr_t offset = mp_obj_get_int(offset_obj);

  if (!app_cache_write_image(image, offset, bufinfo.buf, bufinfo.len)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("Failed to write to app image."));
  }

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorapp_AppImage_write_obj,
                                 mod_trezorapp_AppImage_write);

/// def finalize(self, accept: bool) -> None:
///     """
///     Finalizes loading of the application image. If `accept` is true,
///     the image is marked as loaded and will be available for execution.
///     If `accept` is false, the image is discarded.
///     """
STATIC mp_obj_t mod_trezorapp_AppImage_finalize(mp_obj_t self,
                                                mp_obj_t accept_obj) {
  mp_obj_AppImage_t* o = MP_OBJ_TO_PTR(self);

  bool accept = mp_obj_is_true(accept_obj);

  app_cache_finalize_image(o->image, accept);
  o->image = NULL;

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorapp_AppImage_finalize_obj,
                                 mod_trezorapp_AppImage_finalize);

STATIC const mp_rom_map_elem_t mod_trezorapp_AppImage_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&mod_trezorapp_AppImage_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_finalize),
     MP_ROM_PTR(&mod_trezorapp_AppImage_finalize_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorapp_AppImage_locals_dict,
                            mod_trezorapp_AppImage_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorapp_AppImage_type = {
    {&mp_type_type},
    .name = MP_QSTR_AppImage,
    .locals_dict = (void*)&mod_trezorapp_AppImage_locals_dict,
};
