/*
 * This file is part of the TREZOR project, https://trezor.io/
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

void mp_hal_set_vcp_iface(int iface_num);

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
///              device_class: int=0,
///              device_subclass: int=0,
///              device_protocol: int=0,
///              vendor_id: int,
///              product_id: int,
///              release_num: int,
///              manufacturer: str='',
///              product: str='',
///              serial_number: str='',
///              interface: str='',
///              usb21_enabled: bool=True,
///              usb21_landing: bool=True) -> None:
///     '''
///     '''
STATIC mp_obj_t mod_trezorio_USB_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args) {

    STATIC const mp_arg_t allowed_args[] = {
        { MP_QSTR_device_class,                    MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_device_subclass,                 MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_device_protocol,                 MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_vendor_id,     MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_product_id,    MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_release_num,   MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_manufacturer,                    MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_empty_bytes} },
        { MP_QSTR_product,                         MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_empty_bytes} },
        { MP_QSTR_serial_number,                   MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_empty_bytes} },
        { MP_QSTR_interface,                       MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = mp_const_empty_bytes} },
        { MP_QSTR_usb21_enabled,                   MP_ARG_KW_ONLY | MP_ARG_BOOL, {.u_bool = true} },
        { MP_QSTR_usb21_landing,                   MP_ARG_KW_ONLY | MP_ARG_BOOL, {.u_bool = true} },
    };
    mp_arg_val_t vals[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, args, MP_ARRAY_SIZE(allowed_args), allowed_args, vals);

    const mp_int_t device_class     = vals[0].u_int;
    const mp_int_t device_subclass  = vals[1].u_int;
    const mp_int_t device_protocol  = vals[2].u_int;
    const mp_int_t vendor_id        = vals[3].u_int;
    const mp_int_t product_id       = vals[4].u_int;
    const mp_int_t release_num      = vals[5].u_int;
    const char *manufacturer        = get_0str(vals[6].u_obj, 0, 32);
    const char *product             = get_0str(vals[7].u_obj, 0, 32);
    const char *serial_number       = get_0str(vals[8].u_obj, 0, 32);
    const char *interface           = get_0str(vals[9].u_obj, 0, 32);
    const secbool usb21_enabled     = vals[10].u_bool ? sectrue : secfalse;
    const secbool usb21_landing     = vals[11].u_bool ? sectrue : secfalse;

    CHECK_PARAM_RANGE(device_class, 0, 255)
    CHECK_PARAM_RANGE(device_subclass, 0, 255)
    CHECK_PARAM_RANGE(device_protocol, 0, 255)
    CHECK_PARAM_RANGE(vendor_id, 0, 65535)
    CHECK_PARAM_RANGE(product_id, 0, 65535)
    CHECK_PARAM_RANGE(release_num, 0, 65535)
    if (manufacturer == NULL) {
        mp_raise_ValueError("manufacturer is invalid");
    }
    if (product == NULL) {
        mp_raise_ValueError("product is invalid");
    }
    if (serial_number == NULL) {
        mp_raise_ValueError("serial_number is invalid");
    }
    if (interface == NULL) {
        mp_raise_ValueError("interface is invalid");
    }

    mp_obj_USB_t *o = m_new_obj(mp_obj_USB_t);
    o->base.type = type;

    o->state = USB_CLOSED;

    o->info.device_class    = (uint8_t)(device_class);
    o->info.device_subclass = (uint8_t)(device_subclass);
    o->info.device_protocol = (uint8_t)(device_protocol);
    o->info.vendor_id       = (uint16_t)(vendor_id);
    o->info.product_id      = (uint16_t)(product_id);
    o->info.release_num     = (uint16_t)(release_num);
    o->info.manufacturer    = manufacturer;
    o->info.product         = product;
    o->info.serial_number   = serial_number;
    o->info.interface       = interface;
    o->info.usb21_enabled   = usb21_enabled;
    o->info.usb21_landing   = usb21_landing;

    mp_obj_list_init(&o->ifaces, 0);

    return MP_OBJ_FROM_PTR(o);
}

/// def add(self, iface: Union[HID, VCP, WebUSB]) -> None:
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
    usb_init(&o->info);

    int vcp_iface_num = -1;

    // Add all interfaces
    for (size_t i = 0; i < iface_cnt; i++) {
        mp_obj_t iface = iface_objs[i];

        if (MP_OBJ_IS_TYPE(iface, &mod_trezorio_HID_type)) {
            mp_obj_HID_t *hid = MP_OBJ_TO_PTR(iface);
            if (sectrue != usb_hid_add(&hid->info)) {
                usb_deinit();
                mp_raise_msg(&mp_type_RuntimeError, "failed to add HID interface");
            }
        } else if (MP_OBJ_IS_TYPE(iface, &mod_trezorio_WebUSB_type)) {
            mp_obj_WebUSB_t *webusb = MP_OBJ_TO_PTR(iface);
            if (sectrue != usb_webusb_add(&webusb->info)) {
                usb_deinit();
                mp_raise_msg(&mp_type_RuntimeError, "failed to add WebUSB interface");
            }
        } else if (MP_OBJ_IS_TYPE(iface, &mod_trezorio_VCP_type)) {
            mp_obj_VCP_t *vcp = MP_OBJ_TO_PTR(iface);
            if (sectrue != usb_vcp_add(&vcp->info)) {
                usb_deinit();
                mp_raise_msg(&mp_type_RuntimeError, "failed to add VCP interface");
            }
            vcp_iface_num = vcp->info.iface_num;
        } else {
            usb_deinit();
            mp_raise_TypeError("expected HID, WebUSB or VCP type");
        }
    }

    // Start the USB stack
    usb_start();
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
