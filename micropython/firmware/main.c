#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "py/nlr.h"
#include "py/compile.h"
#include "py/runtime.h"
#include "py/stackctrl.h"
#include "py/repl.h"
#include "py/gc.h"
#include "py/mperrno.h"
#include "lib/utils/pyexec.h"

#include "gccollect.h"
#include "pendsv.h"

#include "common.h"
#include "display.h"
#include "flash.h"
#include "rng.h"
#include "sdcard.h"
#include "touch.h"
#include "usb.h"

int usb_init_all(void) {
    static const usb_dev_info_t dev_info = {
        .vendor_id         = 0x1209,
        .product_id        = 0x53C1,
        .release_num       = 0x0002,
        .manufacturer_str  = (const uint8_t *)"manufacturer_str",
        .product_str       = (const uint8_t *)"product_str",
        .serial_number_str = (const uint8_t *)"serial_number_str",
        .configuration_str = (const uint8_t *)"configuration_str",
        .interface_str     = (const uint8_t *)"interface_str",
    };
    static uint8_t hid_rx_buffer[64];
    static const uint8_t hid_report_desc[] = {
        0x06, 0x00, 0xff,  // USAGE_PAGE (Vendor Defined)
        0x09, 0x01,        // USAGE (1)
        0xa1, 0x01,        // COLLECTION (Application)
        0x09, 0x20,        // USAGE (Input Report Data)
        0x15, 0x00,        // LOGICAL_MINIMUM (0)
        0x26, 0xff, 0x00,  // LOGICAL_MAXIMUM (255)
        0x75, 0x08,        // REPORT_SIZE (8)
        0x95, 0x40,        // REPORT_COUNT (64)
        0x81, 0x02,        // INPUT (Data,Var,Abs)
        0x09, 0x21,        // USAGE (Output Report Data)
        0x15, 0x00,        // LOGICAL_MINIMUM (0)
        0x26, 0xff, 0x00,  // LOGICAL_MAXIMUM (255)
        0x75, 0x08,        // REPORT_SIZE (8)
        0x95, 0x40,        // REPORT_COUNT (64)
        0x91, 0x02,        // OUTPUT (Data,Var,Abs)
        0xc0               // END_COLLECTION
    };
    static const usb_hid_info_t hid_info = {
        .iface_num        = 0x00,
        .ep_in            = USB_EP_DIR_IN | 0x01,
        .ep_out           = USB_EP_DIR_OUT | 0x01,
        .subclass         = 0,
        .protocol         = 0,
        .max_packet_len   = sizeof(hid_rx_buffer),
        .rx_buffer        = hid_rx_buffer,
        .polling_interval = 1,
        .report_desc_len  = sizeof(hid_report_desc),
        .report_desc      = hid_report_desc,
    };
    static uint8_t vcp_rx_buffer[1024];
    static uint8_t vcp_rx_packet[64];
    static uint8_t vcp_tx_buffer[1024];
    static uint8_t vcp_tx_packet[64];  // Needs to be same size as vcp_rx_packet
    static const usb_vcp_info_t vcp_info = {
        .iface_num        = 0x01,
        .data_iface_num   = 0x02,
        .ep_cmd           = USB_EP_DIR_IN | 0x02,
        .ep_in            = USB_EP_DIR_IN | 0x03,
        .ep_out           = USB_EP_DIR_OUT | 0x03,
        .polling_interval = 10,
        .max_packet_len   = sizeof(vcp_rx_packet),
        .rx_packet        = vcp_rx_packet,
        .tx_packet        = vcp_tx_packet,

        .rx_buffer_len    = sizeof(vcp_rx_buffer),
        .rx_buffer        = vcp_rx_buffer,

        .tx_buffer_len    = sizeof(vcp_tx_buffer),
        .tx_buffer        = vcp_tx_buffer,

        .rx_intr_byte     = 3, // Ctrl-C
        .rx_intr_fn       = pendsv_kbd_intr,
    };

    if (0 != usb_init(&dev_info)) {
        __fatal_error("usb_init failed");
    }
    if (0 != usb_hid_add(&hid_info)) {
        __fatal_error("usb_hid_add failed");
    }
    if (0 != usb_vcp_add(&vcp_info)) {
        __fatal_error("usb_vcp_add failed");
    }
    if (0 != usb_start()) {
        __fatal_error("usb_start failed");
    }

    return 0;
}

int main(void) {

    periph_init();

    pendsv_init();

    if (0 != display_init()) {
        __fatal_error("display_init failed");
    }

    if (0 != flash_init()) {
        __fatal_error("flash_init failed");
    }

    if (0 != rng_init()) {
        __fatal_error("rng_init failed");
    }

    if (0 != sdcard_init()) {
        __fatal_error("sdcard_init failed");
    }

    if (0 != touch_init()) {
        __fatal_error("touch_init failed");
    }

    if (0 != usb_init_all()) {
        __fatal_error("usb_init_all failed");
    }

    for (;;) {
        // Stack limit should be less than real stack size, so we have a chance
        // to recover from limit hit.
        mp_stack_set_top(&_estack);
        mp_stack_set_limit((char*)&_estack - (char*)&_heap_end - 1024);

        // GC init
        gc_init(&_heap_start, &_heap_end);

        // Interpreter init
        mp_init();
        mp_obj_list_init(mp_sys_argv, 0);
        mp_obj_list_init(mp_sys_path, 0);
        mp_obj_list_append(mp_sys_path, MP_OBJ_NEW_QSTR(MP_QSTR_)); // current dir (or base dir of the script)

        // Run the main script
        pyexec_frozen_module("main.py");

        // Clean up
        mp_deinit();
    }

    return 0;
}

#ifndef NDEBUG
void MP_WEAK __assert_func(const char *file, int line, const char *func, const char *expr) {
    printf("Assertion '%s' failed, at file %s:%d\n", expr, file, line);
    __fatal_error("Assertion failed");
}
#endif

// Micropython file I/O stubs

mp_lexer_t *mp_lexer_new_from_file(const char *filename) {
    return NULL;
}

mp_import_stat_t mp_import_stat(const char *path) {
    return MP_IMPORT_STAT_NO_EXIST;
}

mp_obj_t mp_builtin_open(uint n_args, const mp_obj_t *args, mp_map_t *kwargs) {
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_KW(mp_builtin_open_obj, 1, mp_builtin_open);

void mp_reader_new_file(mp_reader_t *reader, const char *filename) {
    mp_raise_OSError(MP_ENOENT); // assume "file not found"
}
