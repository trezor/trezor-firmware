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

int main(void)
{
    __stack_chk_guard = rng_get();

    periph_init();

    pendsv_init();

    display_pwm_init();
    display_orientation(0);
    display_backlight(255);

    trassert(0 == flash_init(), NULL);
    trassert(0 == sdcard_init(), NULL);
    trassert(0 == touch_init(), NULL);

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

// MicroPython default exception handler

void __attribute__((noreturn)) nlr_jump_fail(void *val) {
    trassert(0, "uncaught exception");
}

void PendSV_Handler(void) {
    pendsv_isr_handler();
}

// MicroPython file I/O stubs

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
