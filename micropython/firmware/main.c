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
        .product_str       = (uint8_t *)"product_str",
        .manufacturer_str  = (uint8_t *)"manufacturer_str",
        .serial_number_str = (uint8_t *)"serial_number_str",
        .configuration_str = (uint8_t *)"configuration_str",
        .interface_str     = (uint8_t *)"interface_str",
    };
    static uint8_t hid_rx_buffer[64];
    static const usb_hid_info_t hid_info = {
        .iface_num        = 0x00,
        .ep_in            = 0x81,
        .ep_out           = 0x01,
        .subclass         = 0,
        .protocol         = 0,
        .rx_buffer        = hid_rx_buffer,
        .max_packet_len   = sizeof(hid_rx_buffer),
        .polling_interval = 1,
        .report_desc_len  = 34,
        .report_desc      = (uint8_t*)"\x06\x00\xff\x09\x01\xa1\x01\x09\x20\x15\x00\x26\xff\x00\x75\x08\x95\x40\x81\x02\x09\x21\x15\x00\x26\xff\x00\x75\x08\x95\x40\x91\x02\xc0",
    };
    static const usb_vcp_info_t vcp_info = {
        .iface_num           = 0x01,
        .data_iface_num      = 0x02,
        .ep_cmd              = 0x82,
        .ep_in               = 0x83,
        .ep_out              = 0x03,
        .polling_interval    = 1,
        .max_cmd_packet_len  = 8,
        .max_data_packet_len = 64,
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
