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
#include <trezor_types.h>

#include <io/display.h>
#include <sys/sysevent.h>
#include <sys/systick.h>

#ifdef USE_BLE
#include <io/ble.h>
#endif

#ifdef USE_BUTTON
#include <io/button.h>
#endif

#include "embed/upymod/trezorobj.h"

#define POLL_READ (0x0000)
#define POLL_WRITE (0x0100)

extern uint32_t last_touch_sample_time;

#ifdef USE_BLE

static mp_obj_t parse_ble_event_data(const ble_event_t *event) {
  if (event->data_len == 0) {
    return mp_const_none;
  }
  if (event->type != BLE_PAIRING_REQUEST) {
    return mp_const_none;
  }
  // Parse pairing code
  _Static_assert(sizeof(event->data) <= 6);
  uint32_t code = 0;
  for (int i = 0; i < event->data_len; ++i) {
    uint8_t byte = event->data[i];
    if (byte >= '0' && byte <= '9') {
      code = 10 * code + (byte - '0');
    } else {
      mp_raise_ValueError("Invalid pairing code");
    }
  }
  return mp_obj_new_int_from_uint(code);
}

#endif

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

  sysevents_t awaited = {0};

  mp_obj_iter_buf_t iterbuf = {0};

  mp_obj_t iter = mp_getiter(ifaces, &iterbuf);
  mp_obj_t item = 0;
  while ((item = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION) {
    const mp_uint_t i = trezor_obj_get_uint(item);
    const mp_uint_t iface = i & 0x00FF;
    const mp_uint_t mode = i & 0xFF00;

    if (mode & POLL_WRITE) {
      awaited.write_ready |= (1 << iface);

    } else {
      awaited.read_ready |= (1 << iface);
    }
  }

  // The value `timeout_ms` can be negative in a minority of cases, indicating a
  // deadline overrun. This is not a problem because we use the `timeout` only
  // to calculate a `deadline`, and having deadline in the past works fine
  // (except when it overflows, but the code misbehaves near the overflow
  // anyway). Instead of bothering to correct the negative value in Python, we
  // just coerce it to an uint. Deliberately assigning *get_int* to *uint_t*
  // will give us C's wrapping unsigned overflow behavior, and the `deadline`
  // result will come out correct.
  const mp_uint_t deadline = ticks_timeout(trezor_obj_get_int(timeout_ms));

  for (;;) {
    sysevents_t signalled = {0};
    sysevents_poll(&awaited, &signalled, deadline);

    if (signalled.read_ready == 0 && signalled.write_ready == 0) {
      return mp_const_false;
    }

#ifdef USE_TOUCH
    if (signalled.read_ready & (1 << SYSHANDLE_TOUCH)) {
      const uint32_t evt = touch_get_event();
      if (evt != 0) {
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
          switch (display_get_orientation()) {
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
          ret->items[0] = MP_OBJ_NEW_SMALL_INT(SYSHANDLE_TOUCH);
          ret->items[1] = MP_OBJ_FROM_PTR(tuple);
          return mp_const_true;
        }
      }
    }
#endif

#ifdef USE_BUTTON
    if (signalled.read_ready & (1 << SYSHANDLE_BUTTON)) {
      button_event_t btn_event = {0};
      if (button_get_event(&btn_event)) {
        mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(2, NULL));
        uint32_t etype = btn_event.event_type;
        uint32_t en = btn_event.button;
        if (display_get_orientation() == 180) {
          en = (en == BTN_LEFT) ? BTN_RIGHT : BTN_LEFT;
        }
        tuple->items[0] = MP_OBJ_NEW_SMALL_INT(etype);
        tuple->items[1] = MP_OBJ_NEW_SMALL_INT(en);
        ret->items[0] = MP_OBJ_NEW_SMALL_INT(SYSHANDLE_BUTTON);
        ret->items[1] = MP_OBJ_FROM_PTR(tuple);
        return mp_const_true;
      }
    }
#endif

#ifdef USE_BLE
    if (signalled.read_ready & (1 << SYSHANDLE_BLE_IFACE_0)) {
      ret->items[0] = MP_OBJ_NEW_SMALL_INT(SYSHANDLE_BLE_IFACE_0);
      ret->items[1] = MP_OBJ_NEW_SMALL_INT(BLE_RX_PACKET_SIZE);
      return mp_const_true;
    }

    if (signalled.write_ready & (1 << SYSHANDLE_BLE_IFACE_0)) {
      ret->items[0] = MP_OBJ_NEW_SMALL_INT(SYSHANDLE_BLE_IFACE_0 | POLL_WRITE);
      ret->items[1] = mp_const_none;
      return mp_const_true;
    }

    if (signalled.read_ready & (1 << SYSHANDLE_BLE)) {
      ble_event_t event = {0};
      if (ble_get_event(&event)) {
        mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(2, NULL));
        tuple->items[0] = MP_OBJ_NEW_SMALL_INT(event.type);
        tuple->items[1] = parse_ble_event_data(&event);
        ret->items[0] = MP_OBJ_NEW_SMALL_INT(SYSHANDLE_BLE);
        ret->items[1] = MP_OBJ_FROM_PTR(tuple);
        return mp_const_true;
      }
    }
#endif

    if (signalled.read_ready & (1 << SYSHANDLE_USB)) {
      usb_event_t event = usb_get_event();
      ret->items[0] = MP_OBJ_NEW_SMALL_INT(SYSHANDLE_USB);
      ret->items[1] = MP_OBJ_NEW_SMALL_INT((int32_t)event);
      return mp_const_true;
    }

    for (syshandle_t h = SYSHANDLE_USB_IFACE_0; h <= SYSHANDLE_USB_IFACE_7;
         h++) {
      if (signalled.read_ready & (1 << h)) {
        ret->items[0] = MP_OBJ_NEW_SMALL_INT(h);
        ret->items[1] = MP_OBJ_NEW_SMALL_INT(USB_PACKET_LEN);
        return mp_const_true;
      }

      if (signalled.write_ready & (1 << h)) {
        ret->items[0] = MP_OBJ_NEW_SMALL_INT(h | POLL_WRITE);
        ret->items[1] = mp_const_none;
        return mp_const_true;
      }
    }
  }
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorio_poll_obj, mod_trezorio_poll);
