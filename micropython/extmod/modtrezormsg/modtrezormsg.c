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
#include "py/smallint.h"

#if MICROPY_PY_TREZORMSG

#if defined TREZOR_STM32
#include "modtrezormsg-stm32.h"
#include "pendsv.h"
#elif defined TREZOR_UNIX
#include "modtrezormsg-unix.h"
#else
#error Unsupported TREZOR port. Only STM32 and UNIX ports are supported.
#endif

/// class HID:
///     '''
///     USB HID interface configuration.
///     '''
typedef struct _mp_obj_HID_t {
    mp_obj_base_t base;
    usb_hid_info_t info;
} mp_obj_HID_t;

/// def __init__(self,
///              iface_num: int,
///              ep_in: int,
///              ep_out: int,
///              report_desc: bytes,
///              subclass: int = 0,
///              protocol: int = 0,
///              polling_interval: int = 1,
///              max_packet_len: int = 64) -> None:
///     '''
///     '''
STATIC mp_obj_t mod_trezormsg_HID_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {

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

STATIC const mp_rom_map_elem_t mod_trezormsg_HID_locals_dict_table[] = {};
STATIC MP_DEFINE_CONST_DICT(mod_trezormsg_HID_locals_dict, mod_trezormsg_HID_locals_dict_table);

STATIC const mp_obj_type_t mod_trezormsg_HID_type = {
    { &mp_type_type },
    .name = MP_QSTR_HID,
    .make_new = mod_trezormsg_HID_make_new,
    .locals_dict = (void*)&mod_trezormsg_HID_locals_dict,
};

/// class VCP:
///     '''
///     USB VCP interface configuration.
///     '''
typedef struct _mp_obj_VCP_t {
    mp_obj_base_t base;
    usb_vcp_info_t info;
} mp_obj_VCP_t;

/// def __init__(self,
///              iface_num: int,
///              data_iface_num: int,
///              ep_in: int,
///              ep_out: int,
///              ep_cmd: int) -> None:
///     '''
///     '''
STATIC mp_obj_t mod_trezormsg_VCP_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {

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

STATIC const mp_rom_map_elem_t mod_trezormsg_VCP_locals_dict_table[] = {};
STATIC MP_DEFINE_CONST_DICT(mod_trezormsg_VCP_locals_dict, mod_trezormsg_VCP_locals_dict_table);

STATIC const mp_obj_type_t mod_trezormsg_VCP_type = {
    { &mp_type_type },
    .name = MP_QSTR_VCP,
    .make_new = mod_trezormsg_VCP_make_new,
    .locals_dict = (void*)&mod_trezormsg_VCP_locals_dict,
};

/// class USB:
///     '''
///     USB device configuration.
///     '''
typedef struct _mp_obj_USB_t {
    mp_obj_base_t base;
    usb_dev_info_t info;
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

/// def __init__(self,
///              vendor_id: int,
///              product_id: int,
///              release_num: int,
///              manufacturer_str: str,
///              product_str: str,
///              serial_number_str: str,
///              configuration_str: str = '',
///              interface_str: str = '') -> None:
///     '''
///     '''
STATIC mp_obj_t mod_trezormsg_USB_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {

    STATIC const mp_arg_t allowed_args[] = {
        { MP_QSTR_vendor_id,         MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_product_id,        MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_release_num,       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_manufacturer_str,  MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_product_str,       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_serial_number_str, MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_configuration_str,                   MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_empty_bytes} },
        { MP_QSTR_interface_str,                       MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_empty_bytes} },
    };
    mp_arg_val_t vals[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, MP_ARRAY_SIZE(allowed_args), allowed_args, vals);

    const mp_int_t vendor_id      = vals[0].u_int;
    const mp_int_t product_id     = vals[1].u_int;
    const mp_int_t release_num    = vals[2].u_int;
    const char *manufacturer_str  = get_0str(vals[3].u_obj, 0, 32);
    const char *product_str       = get_0str(vals[4].u_obj, 0, 32);
    const char *serial_number_str = get_0str(vals[5].u_obj, 0, 32);
    const char *configuration_str = get_0str(vals[6].u_obj, 0, 32);
    const char *interface_str     = get_0str(vals[7].u_obj, 0, 32);

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

STATIC const mp_rom_map_elem_t mod_trezormsg_USB_locals_dict_table[] = {};
STATIC MP_DEFINE_CONST_DICT(mod_trezormsg_USB_locals_dict, mod_trezormsg_USB_locals_dict_table);

STATIC const mp_obj_type_t mod_trezormsg_USB_type = {
    { &mp_type_type },
    .name = MP_QSTR_USB,
    .make_new = mod_trezormsg_USB_make_new,
    .locals_dict = (void*)&mod_trezormsg_USB_locals_dict,
};

/// class Msg:
///     '''
///     Interface with USB and touch events.
///     '''
typedef struct _mp_obj_Msg_t {
    mp_obj_base_t base;
    mp_obj_t usb_info;
    mp_obj_t usb_ifaces;
} mp_obj_Msg_t;

/// def __init__(self) -> None:
///     '''
///     '''
STATIC mp_obj_t mod_trezormsg_Msg_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 0, 0, false);
    mp_obj_Msg_t *o = m_new_obj(mp_obj_Msg_t);
    o->base.type = type;
    o->usb_info = mp_const_none;
    o->usb_ifaces = mp_const_none;
    return MP_OBJ_FROM_PTR(o);
}

/// def init_usb(self, usb_info: USB, usb_ifaces: List[Union[HID, VCP]]) -> None:
///     '''
///     Registers passed interfaces and initializes the USB stack.
///     '''
STATIC mp_obj_t mod_trezormsg_Msg_init_usb(mp_obj_t self, mp_obj_t usb_info, mp_obj_t usb_ifaces) {

    mp_obj_Msg_t *o = MP_OBJ_TO_PTR(self);
    if (o->usb_info != mp_const_none || o->usb_ifaces != mp_const_none) {
        mp_raise_msg(&mp_type_RuntimeError, "already initialized");
    }

    size_t iface_cnt;
    mp_obj_t *iface_objs;
    mp_obj_get_array(usb_ifaces, &iface_cnt, &iface_objs);

    // Initialize the USB stack
    if (MP_OBJ_IS_TYPE(usb_info, &mod_trezormsg_USB_type)) {
        mp_obj_USB_t *usb = MP_OBJ_TO_PTR(usb_info);
        if (usb_init(&usb->info) != 0) {
            mp_raise_msg(&mp_type_RuntimeError, "failed to initialize USB");
        }
    } else {
        mp_raise_TypeError("expected USB type");
    }

    int vcp_iface_num = -1;

    // Add all interfaces
    for (size_t i = 0; i < iface_cnt; i++) {
        mp_obj_t iface = iface_objs[i];

        if (MP_OBJ_IS_TYPE(iface, &mod_trezormsg_HID_type)) {
            mp_obj_HID_t *hid = MP_OBJ_TO_PTR(iface);
            if (usb_hid_add(&hid->info) != 0) {
                usb_deinit();
                mp_raise_msg(&mp_type_RuntimeError, "failed to add HID interface");
            }
        } else if (MP_OBJ_IS_TYPE(iface, &mod_trezormsg_VCP_type)) {
            mp_obj_VCP_t *vcp = MP_OBJ_TO_PTR(iface);
            if (usb_vcp_add(&vcp->info) != 0) {
                usb_deinit();
                mp_raise_msg(&mp_type_RuntimeError, "failed to add VCP interface");
            }
            vcp_iface_num = vcp->info.iface_num;
        } else {
            usb_deinit();
            mp_raise_TypeError("expected HID or VCP type");
        }
    }

    // Start the USB stack
    if (usb_start() != 0) {
        usb_deinit();
        mp_raise_msg(&mp_type_RuntimeError, "failed to start USB");
    }

    // If we found any VCP interfaces, use the last one for stdio,
    // otherwise disable the stdio support
    mp_hal_set_vcp_iface(vcp_iface_num);

    o->usb_info = usb_info;
    o->usb_ifaces = usb_ifaces;

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezormsg_Msg_init_usb_obj, mod_trezormsg_Msg_init_usb);

/// def deinit_usb(self) -> None:
///     '''
///     Cleans up the USB stack.
///     '''
STATIC mp_obj_t mod_trezormsg_Msg_deinit_usb(mp_obj_t self) {

    usb_stop();
    usb_deinit();

    mp_obj_Msg_t *o = MP_OBJ_TO_PTR(self);
    o->usb_info = mp_const_none;
    o->usb_ifaces = mp_const_none;

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezormsg_Msg_deinit_usb_obj, mod_trezormsg_Msg_deinit_usb);

/// def send(self, iface: int, message: bytes) -> int:
///     '''
///     Sends message using USB HID (device) or UDP (emulator).
///     '''
STATIC mp_obj_t mod_trezormsg_Msg_send(mp_obj_t self, mp_obj_t iface, mp_obj_t message) {
    // mp_obj_Msg_t *o = MP_OBJ_TO_PTR(self);
    uint8_t i = mp_obj_get_int(iface);
    mp_buffer_info_t msg;
    mp_get_buffer_raise(message, &msg, MP_BUFFER_READ);
    ssize_t r = usb_hid_write(i, msg.buf, msg.len);
    return MP_OBJ_NEW_SMALL_INT(r);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezormsg_Msg_send_obj, mod_trezormsg_Msg_send);

STATIC mp_obj_t mod_trezormsg_Msg___del__(mp_obj_t self) {
    mp_obj_Msg_t *o = MP_OBJ_TO_PTR(self);
    if (o->usb_info != mp_const_none || o->usb_ifaces != mp_const_none) {
        usb_stop();
        usb_deinit();
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezormsg_Msg___del___obj, mod_trezormsg_Msg___del__);

STATIC const mp_rom_map_elem_t mod_trezormsg_Msg_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&mod_trezormsg_Msg___del___obj) },
    { MP_ROM_QSTR(MP_QSTR_init_usb), MP_ROM_PTR(&mod_trezormsg_Msg_init_usb_obj) },
    { MP_ROM_QSTR(MP_QSTR_deinit_usb), MP_ROM_PTR(&mod_trezormsg_Msg_deinit_usb_obj) },
    { MP_ROM_QSTR(MP_QSTR_send), MP_ROM_PTR(&mod_trezormsg_Msg_send_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezormsg_Msg_locals_dict, mod_trezormsg_Msg_locals_dict_table);

STATIC const mp_obj_type_t mod_trezormsg_Msg_type = {
    { &mp_type_type },
    .name = MP_QSTR_Msg,
    .make_new = mod_trezormsg_Msg_make_new,
    .locals_dict = (void*)&mod_trezormsg_Msg_locals_dict,
};

#define TOUCH_IFACE (255)
#define POLL_READ  (0x0000)
#define POLL_WRITE (0x0100)

/// def poll(ifaces: Iterable[int], list_ref: List, timeout_us: int) -> bool:
///     '''
///     '''
STATIC mp_obj_t mod_trezormsg_poll(mp_obj_t ifaces, mp_obj_t list_ref, mp_obj_t timeout_us) {
    mp_obj_list_t *ret = MP_OBJ_TO_PTR(list_ref);
    if (!MP_OBJ_IS_TYPE(list_ref, &mp_type_list) || ret->len < 2) {
        mp_raise_TypeError("invalid list_ref");
    }

    const mp_uint_t timeout = mp_obj_get_int(timeout_us);
    const mp_uint_t deadline = mp_hal_ticks_us() + timeout;
    mp_obj_iter_buf_t iterbuf;

    for (;;) {
        mp_obj_t iter = mp_getiter(ifaces, &iterbuf);
        mp_obj_t item;
        while ((item = mp_iternext(iter)) != MP_OBJ_STOP_ITERATION) {
            const mp_uint_t i = mp_obj_int_get_truncated(item);
            const mp_uint_t iface = i & 0x00FF;
            const mp_uint_t mode = i & 0xFF00;

            if (iface == TOUCH_IFACE) {
                uint32_t evt = touch_read();
                if (evt) {
                    mp_obj_tuple_t *tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(3, NULL));
                    tuple->items[0] = MP_OBJ_NEW_SMALL_INT((evt & 0xFF0000) >> 16); // event type
                    tuple->items[1] = MP_OBJ_NEW_SMALL_INT((evt & 0xFF00) >> 8); // x position
                    tuple->items[2] = MP_OBJ_NEW_SMALL_INT((evt & 0xFF)); // y position
                    ret->items[0] = MP_OBJ_NEW_SMALL_INT(i);
                    ret->items[1] = MP_OBJ_FROM_PTR(tuple);
                    return mp_const_true;
                }
            } else
            if (mode == POLL_READ) {
                if (usb_hid_can_read(iface)) {
                    uint8_t buf[64];
                    int l = usb_hid_read(iface, buf, sizeof(buf));
                    if (l > 0) {
                        ret->items[0] = MP_OBJ_NEW_SMALL_INT(i);
                        ret->items[1] = mp_obj_new_str_of_type(&mp_type_bytes, buf, l);
                        return mp_const_true;
                    }
                }
            } else
            if (mode == POLL_WRITE) {
                if (usb_hid_can_write(iface)) {
                    ret->items[0] = MP_OBJ_NEW_SMALL_INT(i);
                    ret->items[1] = mp_const_none;
                    return mp_const_true;
                }
            }
        }

        if (mp_hal_ticks_us() >= deadline) {
            break;
        } else {
            MICROPY_EVENT_POLL_HOOK
        }
    }

    return mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezormsg_poll_obj, mod_trezormsg_poll);

STATIC const mp_rom_map_elem_t mp_module_trezormsg_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_trezormsg) },
    { MP_ROM_QSTR(MP_QSTR_USB), MP_ROM_PTR(&mod_trezormsg_USB_type) },
    { MP_ROM_QSTR(MP_QSTR_HID), MP_ROM_PTR(&mod_trezormsg_HID_type) },
    { MP_ROM_QSTR(MP_QSTR_VCP), MP_ROM_PTR(&mod_trezormsg_VCP_type) },
    { MP_ROM_QSTR(MP_QSTR_Msg), MP_ROM_PTR(&mod_trezormsg_Msg_type) },

    { MP_ROM_QSTR(MP_QSTR_poll), MP_ROM_PTR(&mod_trezormsg_poll_obj) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH), MP_OBJ_NEW_SMALL_INT(TOUCH_IFACE) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH_START), MP_OBJ_NEW_SMALL_INT((TOUCH_START & 0xFF0000) >> 16) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH_MOVE), MP_OBJ_NEW_SMALL_INT((TOUCH_MOVE & 0xFF0000) >> 16) },
    { MP_ROM_QSTR(MP_QSTR_TOUCH_END), MP_OBJ_NEW_SMALL_INT((TOUCH_END & 0xFF0000) >> 16) },
    { MP_ROM_QSTR(MP_QSTR_POLL_READ), MP_OBJ_NEW_SMALL_INT(POLL_READ) },
    { MP_ROM_QSTR(MP_QSTR_POLL_WRITE), MP_OBJ_NEW_SMALL_INT(POLL_WRITE) },
};
STATIC MP_DEFINE_CONST_DICT(mp_module_trezormsg_globals, mp_module_trezormsg_globals_table);

const mp_obj_module_t mp_module_trezormsg = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t*)&mp_module_trezormsg_globals,
};

#endif // MICROPY_PY_TREZORMSG
