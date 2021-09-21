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

#include <string.h>

#include "py/mphal.h"
#include "py/objstr.h"
#include "py/runtime.h"

#if MICROPY_PY_TREZORIO

#include <unistd.h>

#include "button.h"
#include "touch.h"
#include "usb.h"

#define CHECK_PARAM_RANGE(value, minimum, maximum)  \
  if (value < minimum || value > maximum) {         \
    mp_raise_ValueError(#value " is out of range"); \
  }

// clang-format off
#include "modtrezorio-flash.h"
#include "modtrezorio-hid.h"
#include "modtrezorio-poll.h"
#include "modtrezorio-vcp.h"
#include "modtrezorio-webusb.h"
#include "modtrezorio-usb.h"
// clang-format on
#if TREZOR_MODEL == T
#include "modtrezorio-fatfs.h"
#include "modtrezorio-sbu.h"
#include "modtrezorio-sdcard.h"
#endif

/// package: trezorio.__init__

/// POLL_READ: int  # wait until interface is readable and return read data
/// POLL_WRITE: int  # wait until interface is writable
///
/// TOUCH: int  # interface id of the touch events
/// TOUCH_START: int  # event id of touch start event
/// TOUCH_MOVE: int  # event id of touch move event
/// TOUCH_END: int  # event id of touch end event

/// BUTTON: int  # interface id of button events
/// BUTTON_PRESSED: int  # button down event
/// BUTTON_RELEASED: int  # button up event
/// BUTTON_LEFT: int  # button number of left button
/// BUTTON_RIGHT: int  # button number of right button

/// WireInterface = Union[HID, WebUSB]

/// if False:
///     from . import fatfs, sdcard

STATIC const mp_rom_map_elem_t mp_module_trezorio_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezorio)},

#if TREZOR_MODEL == T
    {MP_ROM_QSTR(MP_QSTR_fatfs), MP_ROM_PTR(&mod_trezorio_fatfs_module)},
    {MP_ROM_QSTR(MP_QSTR_SBU), MP_ROM_PTR(&mod_trezorio_SBU_type)},
    {MP_ROM_QSTR(MP_QSTR_sdcard), MP_ROM_PTR(&mod_trezorio_sdcard_module)},

    {MP_ROM_QSTR(MP_QSTR_TOUCH), MP_ROM_INT(TOUCH_IFACE)},
    {MP_ROM_QSTR(MP_QSTR_TOUCH_START), MP_ROM_INT((TOUCH_START >> 24) & 0xFFU)},
    {MP_ROM_QSTR(MP_QSTR_TOUCH_MOVE), MP_ROM_INT((TOUCH_MOVE >> 24) & 0xFFU)},
    {MP_ROM_QSTR(MP_QSTR_TOUCH_END), MP_ROM_INT((TOUCH_END >> 24) & 0xFFU)},
#elif TREZOR_MODEL == 1
    {MP_ROM_QSTR(MP_QSTR_BUTTON), MP_ROM_INT(BUTTON_IFACE)},
    {MP_ROM_QSTR(MP_QSTR_BUTTON_PRESSED),
     MP_ROM_INT((BTN_EVT_DOWN >> 24) & 0x3U)},
    {MP_ROM_QSTR(MP_QSTR_BUTTON_RELEASED),
     MP_ROM_INT((BTN_EVT_UP >> 24) & 0x3U)},
    {MP_ROM_QSTR(MP_QSTR_BUTTON_LEFT), MP_ROM_INT(BTN_LEFT)},
    {MP_ROM_QSTR(MP_QSTR_BUTTON_RIGHT), MP_ROM_INT(BTN_RIGHT)},
#endif

    {MP_ROM_QSTR(MP_QSTR_FlashOTP), MP_ROM_PTR(&mod_trezorio_FlashOTP_type)},

    {MP_ROM_QSTR(MP_QSTR_USB), MP_ROM_PTR(&mod_trezorio_USB_type)},
    {MP_ROM_QSTR(MP_QSTR_HID), MP_ROM_PTR(&mod_trezorio_HID_type)},
    {MP_ROM_QSTR(MP_QSTR_VCP), MP_ROM_PTR(&mod_trezorio_VCP_type)},
    {MP_ROM_QSTR(MP_QSTR_WebUSB), MP_ROM_PTR(&mod_trezorio_WebUSB_type)},

    {MP_ROM_QSTR(MP_QSTR_poll), MP_ROM_PTR(&mod_trezorio_poll_obj)},
    {MP_ROM_QSTR(MP_QSTR_POLL_READ), MP_ROM_INT(POLL_READ)},
    {MP_ROM_QSTR(MP_QSTR_POLL_WRITE), MP_ROM_INT(POLL_WRITE)},
};

STATIC MP_DEFINE_CONST_DICT(mp_module_trezorio_globals,
                            mp_module_trezorio_globals_table);

const mp_obj_module_t mp_module_trezorio = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&mp_module_trezorio_globals,
};

MP_REGISTER_MODULE(MP_QSTR_trezorio, mp_module_trezorio, MICROPY_PY_TREZORIO);

#endif  // MICROPY_PY_TREZORIO
