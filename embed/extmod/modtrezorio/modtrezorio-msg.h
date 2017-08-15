/*
 * Copyright (c) Pavol Rusnak, SatoshiLabs
 *
 * Licensed under TREZOR License
 * see LICENSE file for details
 */

#include <string.h>
#include <unistd.h>

#if defined TREZOR_STM32
#include "usb.h"
#include "touch.h"
#include "pendsv.h"
#elif defined TREZOR_UNIX
#include "unix-msg-mock.h"
#else
#error Unsupported TREZOR port. Only STM32 and UNIX ports are supported.
#endif

#define TOUCH_IFACE (255)
#define POLL_READ  (0x0000)
#define POLL_WRITE (0x0100)

/// def poll(ifaces: Iterable[int], list_ref: List, timeout_us: int) -> bool:
///     '''
///     Wait until one of `ifaces` is ready to read or write (using masks
//      `io.POLL_READ` and `io.POLL_WRITE`) and assign the result into
///     `list_ref`:
///
///     `list_ref[0]` - the interface number, including the mask
///     `list_ref[1]` - for touch event, tuple of (event_type, x_position, y_position)
///                   - for HID read event, received bytes
///
///     If timeout occurs, False is returned, True otherwise.
///     '''
STATIC mp_obj_t mod_trezorio_poll(mp_obj_t ifaces, mp_obj_t list_ref, mp_obj_t timeout_us) {
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
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_trezorio_poll_obj, mod_trezorio_poll);

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
STATIC mp_obj_t mod_trezorio_HID_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {

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

/// def iface_num(self) -> int:
///     '''
///     Returns the configured number of this interface.
///     '''
STATIC mp_obj_t mod_trezorio_HID_iface_num(mp_obj_t self) {
    mp_obj_HID_t *o = MP_OBJ_TO_PTR(self);
    return MP_OBJ_NEW_SMALL_INT(o->info.iface_num);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_HID_iface_num_obj, mod_trezorio_HID_iface_num);

/// def write(self, msg: bytes) -> int:
///     '''
///     Sends message using USB HID (device) or UDP (emulator).
///     '''
STATIC mp_obj_t mod_trezorio_HID_write(mp_obj_t self, mp_obj_t msg) {
    mp_obj_HID_t *o = MP_OBJ_TO_PTR(self);
    mp_buffer_info_t buf;
    mp_get_buffer_raise(msg, &buf, MP_BUFFER_READ);
    ssize_t r = usb_hid_write(o->info.iface_num, buf.buf, buf.len);
    return MP_OBJ_NEW_SMALL_INT(r);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_HID_write_obj, mod_trezorio_HID_write);

STATIC const mp_rom_map_elem_t mod_trezorio_HID_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_iface_num), MP_ROM_PTR(&mod_trezorio_HID_iface_num_obj) },
    { MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&mod_trezorio_HID_write_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_HID_locals_dict, mod_trezorio_HID_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorio_HID_type = {
    { &mp_type_type },
    .name = MP_QSTR_HID,
    .make_new = mod_trezorio_HID_make_new,
    .locals_dict = (void*)&mod_trezorio_HID_locals_dict,
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
STATIC mp_obj_t mod_trezorio_VCP_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {

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

/// def iface_num(self) -> int:
///     '''
///     Returns the configured number of this interface.
///     '''
STATIC mp_obj_t mod_trezorio_VCP_iface_num(mp_obj_t self) {
    mp_obj_VCP_t *o = MP_OBJ_TO_PTR(self);
    return MP_OBJ_NEW_SMALL_INT(o->info.iface_num);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_VCP_iface_num_obj, mod_trezorio_VCP_iface_num);

STATIC const mp_rom_map_elem_t mod_trezorio_VCP_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_iface_num), MP_ROM_PTR(&mod_trezorio_HID_iface_num_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_VCP_locals_dict, mod_trezorio_VCP_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorio_VCP_type = {
    { &mp_type_type },
    .name = MP_QSTR_VCP,
    .make_new = mod_trezorio_VCP_make_new,
    .locals_dict = (void*)&mod_trezorio_VCP_locals_dict,
};

enum {
    USB_CLOSED = 0,
    USB_OPENED = 1,
};

/// class USB:
///     '''
///     USB device configuration.
///     '''
typedef struct _mp_obj_USB_t {
    mp_obj_base_t base;
    mp_obj_list_t ifaces;
    usb_dev_info_t info;
    mp_int_t state;
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
///              manufacturer: str,
///              product: str,
///              serial_number: str) -> None:
///     '''
///     '''
STATIC mp_obj_t mod_trezorio_USB_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {

    STATIC const mp_arg_t allowed_args[] = {
        { MP_QSTR_vendor_id,     MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_product_id,    MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_release_num,   MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_manufacturer,  MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_product,       MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_serial_number, MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
    };
    mp_arg_val_t vals[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, MP_ARRAY_SIZE(allowed_args), allowed_args, vals);

    const mp_int_t vendor_id      = vals[0].u_int;
    const mp_int_t product_id     = vals[1].u_int;
    const mp_int_t release_num    = vals[2].u_int;
    const char *manufacturer  = get_0str(vals[3].u_obj, 0, 32);
    const char *product       = get_0str(vals[4].u_obj, 0, 32);
    const char *serial_number = get_0str(vals[5].u_obj, 0, 32);

    if (vendor_id < 0 || vendor_id > 65535) {
        mp_raise_ValueError("vendor_id is invalid");
    }
    if (product_id < 0 || product_id > 65535) {
        mp_raise_ValueError("product_id is invalid");
    }
    if (manufacturer == NULL) {
        mp_raise_ValueError("manufacturer is invalid");
    }
    if (product == NULL) {
        mp_raise_ValueError("product is invalid");
    }
    if (serial_number == NULL) {
        mp_raise_ValueError("serial_number is invalid");
    }

    mp_obj_USB_t *o = m_new_obj(mp_obj_USB_t);
    o->base.type = type;

    o->state = USB_CLOSED;

    o->info.vendor_id     = (uint16_t)(vendor_id);
    o->info.product_id    = (uint16_t)(product_id);
    o->info.release_num   = (uint16_t)(release_num);
    o->info.manufacturer  = (const uint8_t *)(manufacturer);
    o->info.product       = (const uint8_t *)(product);
    o->info.serial_number = (const uint8_t *)(serial_number);
    mp_obj_list_init(&o->ifaces, 0);

    return MP_OBJ_FROM_PTR(o);
}

/// def add(self, iface: Union[HID, VCP]) -> None:
///     '''
///     Registers passed interface into the USB stack.
///     '''
STATIC mp_obj_t mod_trezorio_USB_add(mp_obj_t self, mp_obj_t iface) {
    mp_obj_USB_t *o = MP_OBJ_TO_PTR(self);

    if (o->state != USB_CLOSED) {
        mp_raise_msg(&mp_type_RuntimeError, "already initialized");
    }
    mp_obj_list_append(MP_OBJ_FROM_PTR(&o->ifaces), iface);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_trezorio_USB_add_obj, mod_trezorio_USB_add);

/// def open(self) -> None:
///     '''
///     Initializes the USB stack.
///     '''
STATIC mp_obj_t mod_trezorio_USB_open(mp_obj_t self) {
    mp_obj_USB_t *o = MP_OBJ_TO_PTR(self);

    if (o->state != USB_CLOSED) {
        mp_raise_msg(&mp_type_RuntimeError, "already initialized");
    }

    size_t iface_cnt;
    mp_obj_t *iface_objs;
    mp_obj_get_array(MP_OBJ_FROM_PTR(&o->ifaces), &iface_cnt, &iface_objs);

    // Initialize the USB stack
    if (usb_init(&o->info) != 0) {
        mp_raise_msg(&mp_type_RuntimeError, "failed to initialize USB");
    }

    int vcp_iface_num = -1;

    // Add all interfaces
    for (size_t i = 0; i < iface_cnt; i++) {
        mp_obj_t iface = iface_objs[i];

        if (MP_OBJ_IS_TYPE(iface, &mod_trezorio_HID_type)) {
            mp_obj_HID_t *hid = MP_OBJ_TO_PTR(iface);
            if (usb_hid_add(&hid->info) != 0) {
                usb_deinit();
                mp_raise_msg(&mp_type_RuntimeError, "failed to add HID interface");
            }
        } else if (MP_OBJ_IS_TYPE(iface, &mod_trezorio_VCP_type)) {
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
    o->state = USB_OPENED;

    // If we found any VCP interfaces, use the last one for stdio,
    // otherwise disable the stdio support
    mp_hal_set_vcp_iface(vcp_iface_num);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_USB_open_obj, mod_trezorio_USB_open);

/// def close(self) -> None:
///     '''
///     Cleans up the USB stack.
///     '''
STATIC mp_obj_t mod_trezorio_USB_close(mp_obj_t self) {
    mp_obj_USB_t *o = MP_OBJ_TO_PTR(self);

    if (o->state != USB_OPENED) {
        mp_raise_msg(&mp_type_RuntimeError, "not initialized");
    }
    usb_stop();
    usb_deinit();
    mp_obj_list_set_len(MP_OBJ_FROM_PTR(&o->ifaces), 0);
    mp_seq_clear(o->ifaces.items, 0, o->ifaces.alloc, sizeof(*o->ifaces.items));
    o->info.vendor_id     = 0;
    o->info.product_id    = 0;
    o->info.release_num   = 0;
    o->info.manufacturer  = NULL;
    o->info.product       = NULL;
    o->info.serial_number = NULL;
    o->state = USB_CLOSED;

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_USB_close_obj, mod_trezorio_USB_close);

STATIC mp_obj_t mod_trezorio_USB___del__(mp_obj_t self) {
    mp_obj_USB_t *o = MP_OBJ_TO_PTR(self);
    if (o->state != USB_CLOSED) {
        usb_stop();
        usb_deinit();
        o->state = USB_CLOSED;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_trezorio_USB___del___obj, mod_trezorio_USB___del__);

STATIC const mp_rom_map_elem_t mod_trezorio_USB_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_add), MP_ROM_PTR(&mod_trezorio_USB_add_obj) },
    { MP_ROM_QSTR(MP_QSTR_open), MP_ROM_PTR(&mod_trezorio_USB_open_obj) },
    { MP_ROM_QSTR(MP_QSTR_close), MP_ROM_PTR(&mod_trezorio_USB_close_obj) },
    { MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&mod_trezorio_USB___del___obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorio_USB_locals_dict, mod_trezorio_USB_locals_dict_table);

STATIC const mp_obj_type_t mod_trezorio_USB_type = {
    { &mp_type_type },
    .name = MP_QSTR_USB,
    .make_new = mod_trezorio_USB_make_new,
    .locals_dict = (void*)&mod_trezorio_USB_locals_dict,
};