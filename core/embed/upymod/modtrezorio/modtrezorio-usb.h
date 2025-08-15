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

/// package: trezorio.__init__

/// class USB:
///     """
///     USB device configuration.
///     """
typedef struct _mp_obj_USB_t {
  mp_obj_base_t base;
} mp_obj_USB_t;

static const char *get_0str(mp_obj_t o, size_t min_len, size_t max_len) {
  size_t len;
  const char *s = mp_obj_str_get_data(o, &len);
  if ((len >= min_len) && (len <= max_len)) {
    if (len == 0 && s == NULL) {
      return "";
    } else {
      return s;
    }
  } else {
    return NULL;
  }
}

/// def __init__(
///     self,
/// ) -> None:
///     """
///     """
STATIC mp_obj_t mod_trezorio_USB_make_new(const mp_obj_type_t *type,
                                          size_t n_args, size_t n_kw,
                                          const mp_obj_t *args) {
  mp_obj_USB_t *o = m_new_obj_with_finaliser(mp_obj_USB_t);
  o->base.type = type;

  return MP_OBJ_FROM_PTR(o);
}

/// def open(self, serial_number: str) -> None:
///     """
///     Initializes the USB stack.
///     """
STATIC mp_obj_t mod_trezorio_USB_open(mp_obj_t self,
                                      mp_obj_t serial_number_obj) {
  const char *serial_number = get_0str(serial_number_obj, 0, USB_MAX_STR_SIZE);
  if (serial_number == NULL) {
    mp_raise_ValueError(MP_ERROR_TEXT("serial_number is invalid"));
  }

  usb_start_params_t params = {
      .serial_number = "",
      .usb21_landing = secfalse,
  };

  strncpy(params.serial_number, serial_number, USB_MAX_STR_SIZE);

  // Start the USB stack
  if (sectrue != usb_start(&params)) {
    mp_raise_msg(&mp_type_RuntimeError,
                 MP_ERROR_TEXT("failed to start usb driver"));
  }

  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_USB_open_obj,
                                 mod_trezorio_USB_open);

/// def close(self) -> None:
///     """
///     Cleans up the USB stack.
///     """
STATIC mp_obj_t mod_trezorio_USB_close(mp_obj_t self) {
  usb_stop();
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_USB_close_obj,
                                 mod_trezorio_USB_close);

STATIC mp_obj_t mod_trezorio_USB___del__(mp_obj_t self) {
  usb_stop();
  return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_USB___del___obj,
                                 mod_trezorio_USB___del__);

STATIC const mp_rom_map_elem_t mod_trezorio_USB_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_open), MP_ROM_PTR(&mod_trezorio_USB_open_obj)},
    {MP_ROM_QSTR(MP_QSTR_close), MP_ROM_PTR(&mod_trezorio_USB_close_obj)},
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&mod_trezorio_USB___del___obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_USB_locals_dict,
                            mod_trezorio_USB_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorio_USB_type = {
    {&mp_type_type},
    .name = MP_QSTR_USB,
    .make_new = mod_trezorio_USB_make_new,
    .locals_dict = (void *)&mod_trezorio_USB_locals_dict,
};
