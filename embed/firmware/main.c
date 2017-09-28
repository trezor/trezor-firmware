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

bool firmware_standalone(void)
{
    extern const uint32_t _flash_start;
    return _flash_start == 0x0800000;
}

int main(void) {

    periph_init();

    pendsv_init();

    if (firmware_standalone()) {
        display_init();
    }

    display_pwm_init();
    display_orientation(0);
    display_backlight(255);

    if (0 != flash_init()) {
        __fatal_error("flash_init", __FILE__, __LINE__, __FUNCTION__);
    }

    if (0 != rng_init()) {
        __fatal_error("rng_init", __FILE__, __LINE__, __FUNCTION__);
    }

    if (0 != sdcard_init()) {
        __fatal_error("sdcard_init", __FILE__, __LINE__, __FUNCTION__);
    }

    if (0 != touch_init()) {
        __fatal_error("touch_init", __FILE__, __LINE__, __FUNCTION__);
    }

    for (;;) {
        printf("CORE: Starting main loop\n");
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
        printf("CORE: Executing main script\n");
        pyexec_frozen_module("main.py");

        // Run REPL
        printf("CORE: Executing REPL\n");
        for (;;) {
            if (pyexec_friendly_repl() != 0) {
                break;
            }
        }

        // Clean up
        mp_deinit();
    }

    return 0;
}

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
