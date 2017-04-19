/*
 * Copyright (c) Pavol Rusnak, Jan Pochyla, SatoshiLabs
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

#if defined TREZOR_STM32
#include "modtrezormsg-stm32.h"
#include "pendsv.h"
#elif defined TREZOR_UNIX
#include "modtrezormsg-unix.h"
#else
#error Unsupported TREZOR port. Only STM32 and UNIX ports are supported.
#endif

typedef struct _mp_obj_USB_t {
    mp_obj_base_t base;
    usb_dev_info_t info;
} mp_obj_USB_t;

static const char *get_0str(mp_obj_t o, size_t min_len, size_t max_len) {
    size_t len;
    const char *s = mp_obj_str_get_data(o, &len);
    if ((s != NULL) && (len >= min_len) && (len <= max_len)) {
        return s;
    } else {
        return NULL;
    }
}

STATIC mp_obj_t mod_TrezorMsg_USB_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {

    STATIC const mp_arg_t allowed_args[] = {
        { MP_QSTR_vendor_id,         MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_product_id,        MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_release_num,       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_manufacturer_str,  MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_product_str,       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_serial_number_str, MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_configuration_str, MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_interface_str,     MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
    };
    mp_arg_val_t vals[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, MP_ARRAY_SIZE(allowed_args), allowed_args, vals);

    const mp_int_t vendor_id      = vals[0].u_int;
    const mp_int_t product_id     = vals[1].u_int;
    const mp_int_t release_num    = vals[2].u_int;
    const char *manufacturer_str  = get_0str(vals[3].u_obj, 1, 32);
    const char *product_str       = get_0str(vals[4].u_obj, 1, 32);
    const char *serial_number_str = get_0str(vals[5].u_obj, 1, 32);
    const char *configuration_str = get_0str(vals[6].u_obj, 1, 32);
    const char *interface_str     = get_0str(vals[7].u_obj, 1, 32);

    if (vendor_id < 0 || vendor_id > 65535) {
        mp_raise_ValueError("vendor_id is invalid");
    }
    if (product_id < 0 || product_id > 65535) {
        mp_raise_ValueError("product_id is invalid");
    }
    if (manufacturer_str == NULL) {
        mp_raise_ValueError("manufacturer_str is invalid");
    }
    if (product_str == NULL) {
        mp_raise_ValueError("product_str is invalid");
    }
    if (serial_number_str == NULL) {
        mp_raise_ValueError("serial_number_str is invalid");
    }
    if (configuration_str == NULL) {
        mp_raise_ValueError("configuration_str is invalid");
    }
    if (interface_str == NULL) {
        mp_raise_ValueError("interface_str is invalid");
    }

    mp_obj_USB_t *o = m_new_obj(mp_obj_USB_t);
    o->base.type = type;

    o->info.vendor_id         = (uint16_t)(vendor_id);
    o->info.product_id        = (uint16_t)(product_id);
    o->info.release_num       = (uint16_t)(release_num);
    o->info.manufacturer_str  = (const uint8_t *)(manufacturer_str);
    o->info.product_str       = (const uint8_t *)(product_str);
    o->info.serial_number_str = (const uint8_t *)(serial_number_str);
    o->info.configuration_str = (const uint8_t *)(configuration_str);
    o->info.interface_str     = (const uint8_t *)(interface_str);

    return MP_OBJ_FROM_PTR(o);
}

STATIC const mp_rom_map_elem_t mod_TrezorMsg_USB_locals_dict_table[] = {};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorMsg_USB_locals_dict, mod_TrezorMsg_USB_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorMsg_USB_type = {
    { &mp_type_type },
    .name = MP_QSTR_USB,
    .make_new = mod_TrezorMsg_USB_make_new,
    .locals_dict = (void*)&mod_TrezorMsg_USB_locals_dict,
};

typedef struct _mp_obj_HID_t {
    mp_obj_base_t base;
    usb_hid_info_t info;
} mp_obj_HID_t;

STATIC mp_obj_t mod_TrezorMsg_HID_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {

    STATIC const mp_arg_t allowed_args[] = {
        { MP_QSTR_iface_num,        MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_ep_in,            MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_ep_out,           MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_subclass,                           MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_protocol,                           MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_polling_interval,                   MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 1} },
        { MP_QSTR_max_packet_len,                     MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 64} },
        { MP_QSTR_report_desc,      MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
    };
    mp_arg_val_t vals[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, MP_ARRAY_SIZE(allowed_args), allowed_args, vals);

    const mp_int_t iface_num        = vals[0].u_int;
    const mp_int_t ep_in            = vals[1].u_int;
    const mp_int_t ep_out           = vals[2].u_int;
    const mp_int_t subclass         = vals[3].u_int;
    const mp_int_t protocol         = vals[4].u_int;
    const mp_int_t polling_interval = vals[5].u_int;
    const mp_int_t max_packet_len   = vals[6].u_int;
    mp_buffer_info_t report_desc;
    mp_get_buffer_raise(vals[7].u_obj, &report_desc, MP_BUFFER_READ);

    if (report_desc.buf == NULL || report_desc.len == 0 || report_desc.len > 255) {
        mp_raise_ValueError("report_desc is invalid");
    }
    if (iface_num < 0 || iface_num > 32) {
        mp_raise_ValueError("iface_num is invalid");
    }
    if (ep_in < 0 || ep_in > 255) {
        mp_raise_ValueError("ep_in is invalid");
    }
    if (ep_out < 0 || ep_out > 255) {
        mp_raise_ValueError("ep_out is invalid");
    }
    if (subclass < 0 || subclass > 255) {
        mp_raise_ValueError("subclass is invalid");
    }
    if (protocol < 0 || protocol > 255) {
        mp_raise_ValueError("protocol is invalid");
    }
    if (polling_interval < 1 || polling_interval > 255) {
        mp_raise_ValueError("polling_interval is invalid");
    }
    if (max_packet_len != 64) {
        mp_raise_ValueError("max_packet_len is invalid");
    }

    mp_obj_HID_t *o = m_new_obj(mp_obj_HID_t);
    o->base.type = type;

    o->info.rx_buffer        = m_new(uint8_t, max_packet_len);
    o->info.report_desc      = report_desc.buf;
    o->info.iface_num        = (uint8_t)(iface_num);
    o->info.ep_in            = (uint8_t)(ep_in);
    o->info.ep_out           = (uint8_t)(ep_out);
    o->info.subclass         = (uint8_t)(subclass);
    o->info.protocol         = (uint8_t)(protocol);
    o->info.polling_interval = (uint8_t)(polling_interval);
    o->info.max_packet_len   = (uint8_t)(max_packet_len);
    o->info.report_desc_len  = (uint8_t)(report_desc.len);

    return MP_OBJ_FROM_PTR(o);
}

STATIC const mp_rom_map_elem_t mod_TrezorMsg_HID_locals_dict_table[] = {};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorMsg_HID_locals_dict, mod_TrezorMsg_HID_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorMsg_HID_type = {
    { &mp_type_type },
    .name = MP_QSTR_HID,
    .make_new = mod_TrezorMsg_HID_make_new,
    .locals_dict = (void*)&mod_TrezorMsg_HID_locals_dict,
};

typedef struct _mp_obj_VCP_t {
    mp_obj_base_t base;
    usb_vcp_info_t info;
} mp_obj_VCP_t;

STATIC mp_obj_t mod_TrezorMsg_VCP_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {

    STATIC const mp_arg_t allowed_args[] = {
        { MP_QSTR_iface_num,        MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_data_iface_num,   MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_ep_in,            MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_ep_out,           MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_ep_cmd,           MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
    };
    mp_arg_val_t vals[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, MP_ARRAY_SIZE(allowed_args), allowed_args, vals);

    const mp_int_t iface_num      = vals[0].u_int;
    const mp_int_t data_iface_num = vals[1].u_int;
    const mp_int_t ep_in          = vals[2].u_int;
    const mp_int_t ep_out         = vals[3].u_int;
    const mp_int_t ep_cmd         = vals[4].u_int;

    if (iface_num < 0 || iface_num > 32) {
        mp_raise_ValueError("iface_num is invalid");
    }
    if (data_iface_num < 0 || data_iface_num > 32) {
        mp_raise_ValueError("iface_num is invalid");
    }
    if (ep_in < 0 || ep_in > 255) {
        mp_raise_ValueError("ep_in is invalid");
    }
    if (ep_out < 0 || ep_out > 255) {
        mp_raise_ValueError("ep_out is invalid");
    }
    if (ep_cmd < 0 || ep_cmd > 255) {
        mp_raise_ValueError("ep_cmd is invalid");
    }

    const size_t vcp_buffer_len = 1024;
    const size_t vcp_packet_len = 64;

    mp_obj_VCP_t *o = m_new_obj(mp_obj_VCP_t);
    o->base.type = type;

    o->info.tx_packet        = m_new(uint8_t, vcp_packet_len);
    o->info.tx_buffer        = m_new(uint8_t, vcp_buffer_len);
    o->info.rx_packet        = m_new(uint8_t, vcp_packet_len);
    o->info.rx_buffer        = m_new(uint8_t, vcp_buffer_len);
    o->info.tx_buffer_len    = vcp_buffer_len;
    o->info.rx_buffer_len    = vcp_buffer_len;
    o->info.rx_intr_fn       = pendsv_kbd_intr;
    o->info.rx_intr_byte     = 3; // Ctrl-C
    o->info.iface_num        = (uint8_t)(iface_num);
    o->info.data_iface_num   = (uint8_t)(data_iface_num);
    o->info.ep_cmd           = (uint8_t)(ep_cmd);
    o->info.ep_in            = (uint8_t)(ep_in);
    o->info.ep_out           = (uint8_t)(ep_out);
    o->info.polling_interval = 10;
    o->info.max_packet_len   = (uint8_t)(vcp_packet_len);

    return MP_OBJ_FROM_PTR(o);
}

STATIC const mp_rom_map_elem_t mod_TrezorMsg_VCP_locals_dict_table[] = {};
STATIC MP_DEFINE_CONST_DICT(mod_TrezorMsg_VCP_locals_dict, mod_TrezorMsg_VCP_locals_dict_table);

STATIC const mp_obj_type_t mod_TrezorMsg_VCP_type = {
    { &mp_type_type },
    .name = MP_QSTR_VCP,
    .make_new = mod_TrezorMsg_VCP_make_new,
    .locals_dict = (void*)&mod_TrezorMsg_VCP_locals_dict,
};

typedef struct _mp_obj_Msg_t {
    mp_obj_base_t base;
    mp_obj_t usb_info;
    mp_obj_t usb_ifaces;
} mp_obj_Msg_t;

STATIC mp_obj_t mod_TrezorMsg_Msg_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    msg_init();
    mp_obj_Msg_t *o = m_new_obj(mp_obj_Msg_t);
    o->base.type = type;
    o->usb_info = mp_const_none;
    o->usb_ifaces = mp_const_none;
    return MP_OBJ_FROM_PTR(o);
}

/// def trezor.msg.init_usb(usb_info, usb_ifaces) -> None:
///     '''
///     Registers passed interfaces and initializes the USB stack
///     '''
STATIC mp_obj_t mod_TrezorMsg_Msg_init_usb(mp_obj_t self, mp_obj_t usb_info, mp_obj_t usb_ifaces) {

    if (!MP_OBJ_IS_TYPE(usb_info, &mod_TrezorMsg_USB_type)) {
        mp_raise_TypeError("Expected USB type");
    }
    mp_obj_USB_t *usb = MP_OBJ_TO_PTR(self);
    if (0 != usb_init(&usb->info)) {
        mp_raise_msg(&mp_type_RuntimeError, "Failed to initialize USB layer");
    }

    size_t iface_cnt;
    mp_obj_t *iface_objs;
    mp_obj_get_array(usb_ifaces, &iface_cnt, &iface_objs);

    for (size_t i = 0; i < iface_cnt; i++) {
        mp_obj_t iface = iface_objs[i];

        if (MP_OBJ_IS_TYPE(iface, &mod_TrezorMsg_HID_type)) {
            mp_obj_HID_t *hid = MP_OBJ_TO_PTR(iface);
            if (0 != usb_hid_add(&hid->info)) {
                usb_deinit();
                mp_raise_msg(&mp_type_RuntimeError, "Failed to add HID interface");
            }
        } else if (MP_OBJ_IS_TYPE(iface, &mod_TrezorMsg_VCP_type)) {
            mp_obj_VCP_t *vcp = MP_OBJ_TO_PTR(iface);
            if (0 != usb_vcp_add(&vcp->info)) {
                usb_deinit();
                mp_raise_msg(&mp_type_RuntimeError, "Failed to add VCP interface");
            }
        } else {
            usb_deinit();
            mp_raise_TypeError("Unknown interface type");
        }
    }

    if (0 != usb_start()) {
        usb_deinit();
        mp_raise_msg(&mp_type_RuntimeError, "Failed to start USB layer");
    }

    mp_obj_Msg_t *o = MP_OBJ_TO_PTR(self);
    o->usb_info = usb_info;
    o->usb_ifaces = usb_ifaces;

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorMsg_Msg_init_usb_obj, mod_TrezorMsg_Msg_init_usb);

/// def trezor.msg.send(iface: int, message: bytes) -> int:
///     '''
///     Sends message using USB HID (device) or UDP (emulator).
///     '''
STATIC mp_obj_t mod_TrezorMsg_Msg_send(mp_obj_t self, mp_obj_t iface, mp_obj_t message) {
    // mp_obj_Msg_t *o = MP_OBJ_TO_PTR(self);
    uint8_t i = mp_obj_get_int(iface);
    mp_buffer_info_t msg;
    mp_get_buffer_raise(message, &msg, MP_BUFFER_READ);
    ssize_t r = msg_send(i, msg.buf, msg.len);
    return MP_OBJ_NEW_SMALL_INT(r);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_TrezorMsg_Msg_send_obj, mod_TrezorMsg_Msg_send);

#define TICK_RESOLUTION 1000
#define TOUCH_IFACE 0
extern uint32_t touch_read(void); // defined in HAL

/// def trezor.msg.select(timeout_us: int) -> tuple:
///     '''
///     Polls the event queue and returns the event object.
///     Function returns None if timeout specified in microseconds is reached.
///     '''
STATIC mp_obj_t mod_TrezorMsg_Msg_select(mp_obj_t self, mp_obj_t timeout_us) {
    // mp_obj_Msg_t *o = MP_OBJ_TO_PTR(self);
    int timeout = mp_obj_get_int(timeout_us);
    if (timeout < 0) {
        timeout = 0;
    }
    for (;;) {
        uint32_t e = touch_read();
        if (e) {
            mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(4, NULL));
            tuple->items[0] = MP_OBJ_NEW_SMALL_INT(TOUCH_IFACE);
            tuple->items[1] = MP_OBJ_NEW_SMALL_INT((e & 0xFF0000) >> 16); // event type
            tuple->items[2] = MP_OBJ_NEW_SMALL_INT((e & 0xFF00) >> 8); // x position
            tuple->items[3] = MP_OBJ_NEW_SMALL_INT((e & 0xFF)); // y position
            return MP_OBJ_FROM_PTR(tuple);
        }
        uint8_t iface;
        uint8_t recvbuf[64];
        ssize_t l = msg_recv(&iface, recvbuf, 64);
        if (l > 0) {
            if (l == 8 && memcmp("PINGPING", recvbuf, 8) == 0) {
                msg_send(iface, (const uint8_t *)"PONGPONG", 8);
                return mp_const_none;
            } else {
                mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(2, NULL));
                tuple->items[0] = MP_OBJ_NEW_SMALL_INT(iface);
                tuple->items[1] = mp_obj_new_str_of_type(&mp_type_bytes, recvbuf, l);
                return MP_OBJ_FROM_PTR(tuple);
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
    { MP_ROM_QSTR(MP_QSTR_init_usb), MP_ROM_PTR(&mod_TrezorMsg_Msg_init_usb_obj) },
    // { MP_ROM_QSTR(MP_QSTR_deinit_usb), MP_ROM_PTR(&mod_TrezorMsg_Msg_deinit_usb_obj) },
    { MP_ROM_QSTR(MP_QSTR_send), MP_ROM_PTR(&mod_TrezorMsg_Msg_send_obj) },
    { MP_ROM_QSTR(MP_QSTR_select), MP_ROM_PTR(&mod_TrezorMsg_Msg_select_obj) },
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
    { MP_ROM_QSTR(MP_QSTR_USB), MP_ROM_PTR(&mod_TrezorMsg_USB_type) },
    { MP_ROM_QSTR(MP_QSTR_HID), MP_ROM_PTR(&mod_TrezorMsg_HID_type) },
    { MP_ROM_QSTR(MP_QSTR_VCP), MP_ROM_PTR(&mod_TrezorMsg_VCP_type) },
    { MP_ROM_QSTR(MP_QSTR_Msg), MP_ROM_PTR(&mod_TrezorMsg_Msg_type) },
};
STATIC MP_DEFINE_CONST_DICT(mp_module_TrezorMsg_globals, mp_module_TrezorMsg_globals_table);

const mp_obj_module_t mp_module_TrezorMsg = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mp_module_TrezorMsg_globals,
};

#endif // MICROPY_PY_TREZORMSG
