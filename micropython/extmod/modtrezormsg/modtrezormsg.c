/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <stdio.h>
#include <string.h>
#include <stdint.h>

#include "py/runtime.h"
#include "py/mphal.h"
#include "py/objstr.h"

#if MICROPY_PY_TREZORMSG

#if defined STM32_HAL_H
#include "modtrezormsg-stmhal.h"
#elif defined UNIX
#include "modtrezormsg-unix.h"
#else
#error Unsupported port. Only STMHAL and UNIX ports are supported.
#endif

#define MAX_INTERFACES 8

typedef struct _mp_obj_Msg_t {
    mp_obj_base_t base;
    uint16_t usage_pages[MAX_INTERFACES];
    mp_uint_t interface_count;
} mp_obj_Msg_t;

STATIC mp_obj_t mod_TrezorMsg_Msg_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    msg_init();
    mp_obj_Msg_t *o = m_new_obj(mp_obj_Msg_t);
    o->base.type = type;
    o->interface_count = 0;
    return MP_OBJ_FROM_PTR(o);
}

/// def trezor.msg.set_interfaces(ifaces: list/tuple) -> None:
///     '''
///     Configures USB interfaces with a list/tuple of (usage_page, ...)
///     '''
STATIC mp_obj_t mod_TrezorMsg_Msg_set_interfaces(mp_obj_t self, mp_obj_t ifaces) {
    mp_uint_t iface_cnt;
    mp_obj_t *usage_pages;
    if (MP_OBJ_IS_TYPE(ifaces, &mp_type_tuple)) {
        mp_obj_tuple_get(ifaces, &iface_cnt, &usage_pages);
    } else
    if (MP_OBJ_IS_TYPE(ifaces, &mp_type_list)) {
        mp_obj_list_get(ifaces, &iface_cnt, &usage_pages);
    } else {
        mp_raise_TypeError("List or tuple expected");
    }
    if (iface_cnt > MAX_INTERFACES) {
        mp_raise_ValueError("Maximum number of interfaces exceeded");
    }
    mp_obj_Msg_t *o = MP_OBJ_TO_PTR(self);
    for (mp_uint_t i = 0; i < iface_cnt; i++) {
       uint16_t usage_page = mp_obj_get_int(usage_pages[i]);
       o->usage_pages[i] = usage_page;
    }
    o->interface_count = iface_cnt;
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorMsg_Msg_set_interfaces_obj, mod_TrezorMsg_Msg_set_interfaces);

/// def trezor.msg.get_interfaces() -> tuple:
///     '''
///     Reads a tuple (of usage pages) of configured USB interfaces
///     '''
STATIC mp_obj_t mod_TrezorMsg_Msg_get_interfaces(mp_obj_t self) {
    mp_obj_Msg_t *o = MP_OBJ_TO_PTR(self);
    mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(o->interface_count, NULL));
    for (mp_uint_t i = 0; i < o->interface_count; i++) {
        tuple->items[i] = MP_OBJ_NEW_SMALL_INT(o->usage_pages[i]);
    }
    return MP_OBJ_FROM_PTR(tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_TrezorMsg_Msg_get_interfaces_obj, mod_TrezorMsg_Msg_get_interfaces);

/// def trezor.msg.send(usage_page: int, message: bytes) -> int:
///     '''
///     Sends message using USB HID (device) or UDP (emulator).
///     '''
STATIC mp_obj_t mod_TrezorMsg_Msg_send(mp_obj_t self, mp_obj_t usage_page, mp_obj_t message) {
    mp_obj_Msg_t *o = MP_OBJ_TO_PTR(self);
    if (o->interface_count == 0) {
        mp_raise_TypeError("No interfaces registered");
    }
    uint16_t up = mp_obj_get_int(usage_page);
    for (uint8_t i = 0; i < o->interface_count; i++) {
        if (o->usage_pages[i] == up) {
            mp_buffer_info_t msg;
            mp_get_buffer_raise(message, &msg, MP_BUFFER_READ);
            ssize_t r = msg_send(i, msg.buf, msg.len);
            return MP_OBJ_NEW_SMALL_INT(r);
        }
    }
    mp_raise_TypeError("Interface not found");
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorMsg_Msg_send_obj, mod_TrezorMsg_Msg_send);

#define TICK_RESOLUTION 1000
#define TOUCH_IFACE 0

/// def trezor.msg.select(timeout_us: int) -> tuple:
///     '''
///     Polls the event queue and returns the event object.
///     Function returns None if timeout specified in microseconds is reached.
///     '''
STATIC mp_obj_t mod_TrezorMsg_Msg_select(mp_obj_t self, mp_obj_t timeout_us) {
    mp_obj_Msg_t *o = MP_OBJ_TO_PTR(self);
    int timeout = mp_obj_get_int(timeout_us);
    if (timeout < 0) {
        timeout = 0;
    }
    for(;;) {
        uint32_t e = msg_poll_ui_event();
        if (e) {
            mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(4, NULL));
            tuple->items[0] = MP_OBJ_NEW_SMALL_INT(TOUCH_IFACE);
            tuple->items[1] = MP_OBJ_NEW_SMALL_INT((e & 0xFF0000) >> 16); // event type
            tuple->items[2] = MP_OBJ_NEW_SMALL_INT((e & 0xFF00) >> 8); // x position
            tuple->items[3] = MP_OBJ_NEW_SMALL_INT((e & 0xFF)); // y position
            return MP_OBJ_FROM_PTR(tuple);
        }
        // check for interfaces only when some have been registered
        if (o->interface_count > 0) {
            uint8_t iface;
            uint8_t recvbuf[64];
            ssize_t l = msg_recv(&iface, recvbuf, 64);
            if (l > 0 && iface < o->interface_count) {
                if (l == 8 && memcmp("PINGPING", recvbuf, 8) == 0) {
                    msg_send(iface, (const uint8_t *)"PONGPONG", 8);
                    return mp_const_none;
                } else {
                    uint16_t iface_usage_page = o->usage_pages[iface];
                    mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(2, NULL));
                    tuple->items[0] = MP_OBJ_NEW_SMALL_INT(iface_usage_page);
                    tuple->items[1] = mp_obj_new_str_of_type(&mp_type_bytes, recvbuf, l);
                    return MP_OBJ_FROM_PTR(tuple);
                }
             }
        }
        if (timeout <= 0) {
            break;
        }
        mp_hal_delay_us(TICK_RESOLUTION);
        timeout -= TICK_RESOLUTION;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_TrezorMsg_Msg_select_obj, mod_TrezorMsg_Msg_select);

STATIC const mp_rom_map_elem_t mod_TrezorMsg_Msg_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_select), MP_ROM_PTR(&mod_TrezorMsg_Msg_select_obj) },
    { MP_ROM_QSTR(MP_QSTR_send), MP_ROM_PTR(&mod_TrezorMsg_Msg_send_obj) },
    { MP_ROM_QSTR(MP_QSTR_set_interfaces), MP_ROM_PTR(&mod_TrezorMsg_Msg_set_interfaces_obj) },
    { MP_ROM_QSTR(MP_QSTR_get_interfaces), MP_ROM_PTR(&mod_TrezorMsg_Msg_get_interfaces_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorMsg_Msg_locals_dict, mod_TrezorMsg_Msg_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorMsg_Msg_type = {
    { &mp_type_type },
    .name = MP_QSTR_Msg,
    .make_new = mod_TrezorMsg_Msg_make_new,
    .locals_dict = (void*)&mod_TrezorMsg_Msg_locals_dict,
};

STATIC const mp_rom_map_elem_t mp_module_TrezorMsg_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_TrezorMsg) },
    { MP_ROM_QSTR(MP_QSTR_Msg), MP_ROM_PTR(&mod_TrezorMsg_Msg_type) },
};

STATIC MP_DEFINE_CONST_DICT(mp_module_TrezorMsg_globals, mp_module_TrezorMsg_globals_table);

const mp_obj_module_t mp_module_TrezorMsg = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mp_module_TrezorMsg_globals,
};

#endif // MICROPY_PY_TREZORMSG
