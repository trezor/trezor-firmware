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

#include "button.h"
#include "common.h"
#include "display.h"
#include "embed/extmod/trezorobj.h"

#define USB_DATA_IFACE (253)
#define BUTTON_IFACE (254)
#define TOUCH_IFACE (255)
#define POLL_READ (0x0000)
#define POLL_WRITE (0x0100)

extern bool usb_connected_previously;
extern uint32_t last_touch_sample_time;

/// package: trezorio.__init__

/// def poll(ifaces: Iterable[int], list_ref: list, timeout_ms: int) -> bool:
///     """
///     Wait until one of `ifaces` is ready to read or write (using masks
///     `io.POLL_READ` and `io.POLL_WRITE`) and assign the result into
///     `list_ref`:
///
///     - `list_ref[0]` - the interface number, including the mask
///     - `list_ref[1]` - for touch event, tuple of:
///                     (event_type, x_position, y_position)
///                   - for button event (T1), tuple of:
///                     (event type, button number)
///                   - for USB read event, received bytes
///
///     If timeout occurs, False is returned, True otherwise.
///     """
STATIC mp_obj_t mod_trezorio_poll(mp_obj_t ifaces, mp_obj_t list_ref,
                                  mp_obj_t timeout_ms) {
  mp_obj_list_t *ret = MP_OBJ_TO_PTR(list_ref);
  if (!MP_OBJ_IS_TYPE(list_ref, &mp_type_list) || ret->len < 2) {
    mp_raise_TypeError("invalid list_ref");
  }

  // The value `timeout_ms` can be negative in a minority of cases, indicating a
  // deadline overrun. This is not a problem because we use the `timeout` only
  // to calculate a `deadline`, and having deadline in the past works fine
  // (except when it overflows, but the code misbehaves near the overflow
  // anyway). Instead of bothering to correct the negative value in Python, we
  // just coerce it to an uint. Deliberately assigning *get_int* to *uint_t*
  // will give us C's wrapping unsigned overflow behavior, and the `deadline`
  // result will come out correct.
  const mp_uint_t timeout = trezor_obj_get_int(timeout_ms);
  const mp_uint_t deadline = mp_hal_ticks_ms() + timeout;
  mp_obj_iter_buf_t iterbuf = {0};

  for (;;) {
    mp_obj_t iter = mp_getiter(ifaces, &iterbuf);
    mp_obj_t item = 0;
    while ((item = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION) {
      const mp_uint_t i = trezor_obj_get_uint(item);
      const mp_uint_t iface = i & 0x00FF;
      const mp_uint_t mode = i & 0xFF00;

#if defined TREZOR_EMULATOR
      emulator_poll_events();
#endif

      if (false) {
      }
#if defined USE_TOUCH
      else if (iface == TOUCH_IFACE) {
        const uint32_t evt = touch_get_event();
        if (evt) {
          // ignore TOUCH_MOVE events if they are too frequent
          if ((evt & TOUCH_MOVE) == 0 ||
              (hal_ticks_ms() - last_touch_sample_time > 10)) {
            last_touch_sample_time = hal_ticks_ms();

            mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(3, NULL));
            const uint32_t etype = (evt >> 24) & 0xFFU;  // event type
            const uint32_t ex = (evt >> 12) & 0xFFFU;    // x position
            const uint32_t ey = evt & 0xFFFU;            // y position
            uint32_t exr;                                // rotated x position
            uint32_t eyr;                                // rotated y position
            switch (display_orientation(-1)) {
              case 90:
                exr = ey;
                eyr = DISPLAY_RESX - ex;
                break;
              case 180:
                exr = DISPLAY_RESX - ex;
                eyr = DISPLAY_RESY - ey;
                break;
              case 270:
                exr = DISPLAY_RESY - ey;
                eyr = ex;
                break;
              default:
                exr = ex;
                eyr = ey;
                break;
            }
            tuple->items[0] = MP_OBJ_NEW_SMALL_INT(etype);
            tuple->items[1] = MP_OBJ_NEW_SMALL_INT(exr);
            tuple->items[2] = MP_OBJ_NEW_SMALL_INT(eyr);
            ret->items[0] = MP_OBJ_NEW_SMALL_INT(i);
            ret->items[1] = MP_OBJ_FROM_PTR(tuple);
            return mp_const_true;
          }
        }
      } else if (iface == USB_DATA_IFACE) {
        bool usb_connected = usb_configured() == sectrue ? true : false;
        if (usb_connected != usb_connected_previously) {
          usb_connected_previously = usb_connected;
          ret->items[0] = MP_OBJ_NEW_SMALL_INT(i);
          ret->items[1] = usb_connected ? mp_const_true : mp_const_false;
          return mp_const_true;
        }
      }
#endif
#if USE_BUTTON
      else if (iface == BUTTON_IFACE) {
        const uint32_t evt = button_read();
        if (evt & (BTN_EVT_DOWN | BTN_EVT_UP)) {
          mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(2, NULL));
          uint32_t etype = (evt >> 24) & 0x3U;  // button down/up
          uint32_t en = evt & 0xFFFF;           // button number
          if (display_orientation(-1) == 180) {
            en = (en == BTN_LEFT) ? BTN_RIGHT : BTN_LEFT;
          }
          tuple->items[0] = MP_OBJ_NEW_SMALL_INT(etype);
          tuple->items[1] = MP_OBJ_NEW_SMALL_INT(en);
          ret->items[0] = MP_OBJ_NEW_SMALL_INT(i);
          ret->items[1] = MP_OBJ_FROM_PTR(tuple);
          return mp_const_true;
        }
      }
#endif
      else if (mode == POLL_READ) {
        if (sectrue == usb_hid_can_read(iface)) {
          uint8_t buf[64] = {0};
          int len = usb_hid_read(iface, buf, sizeof(buf));
          if (len > 0) {
            ret->items[0] = MP_OBJ_NEW_SMALL_INT(i);
            ret->items[1] = mp_obj_new_bytes(buf, len);
            return mp_const_true;
          }
        } else if (sectrue == usb_webusb_can_read(iface)) {
          uint8_t buf[64] = {0};
          int len = usb_webusb_read(iface, buf, sizeof(buf));
          if (len > 0) {
            ret->items[0] = MP_OBJ_NEW_SMALL_INT(i);
            ret->items[1] = mp_obj_new_bytes(buf, len);
            return mp_const_true;
          }
        }
      } else if (mode == POLL_WRITE) {
        if (sectrue == usb_hid_can_write(iface)) {
          ret->items[0] = MP_OBJ_NEW_SMALL_INT(i);
          ret->items[1] = mp_const_none;
          return mp_const_true;
        } else if (sectrue == usb_webusb_can_write(iface)) {
          ret->items[0] = MP_OBJ_NEW_SMALL_INT(i);
          ret->items[1] = mp_const_none;
          return mp_const_true;
        }
      }
    }

    if (mp_hal_ticks_ms() >= deadline) {
      break;
    } else {
      MICROPY_EVENT_POLL_HOOK
    }
  }

  return mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorio_poll_obj, mod_trezorio_poll);
