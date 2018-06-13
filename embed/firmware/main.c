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
#include "mpu.h"
#include "rng.h"
#include "sdcard.h"
#include "touch.h"

int main(void)
{
    // Enable MPU
    mpu_config();

    // Init peripherals
    pendsv_init();
    sdcard_init();
    touch_init();

    display_clear();

    printf("CORE: Preparing stack\n");
    // Stack limit should be less than real stack size, so we have a chance
    // to recover from limit hit.
    mp_stack_set_top(&_estack);
    mp_stack_set_limit((char*)&_estack - (char*)&_heap_end - 1024);

    // GC init
    printf("CORE: Starting GC\n");
    gc_init(&_heap_start, &_heap_end);

    // Interpreter init
    printf("CORE: Starting interpreter\n");
    mp_init();
    mp_obj_list_init(mp_sys_argv, 0);
    mp_obj_list_init(mp_sys_path, 0);
    mp_obj_list_append(mp_sys_path, MP_OBJ_NEW_QSTR(MP_QSTR_)); // current dir (or base dir of the script)

    // Execute the main script
    printf("CORE: Executing main script\n");
    pyexec_frozen_module("main.py");

    // Clean up
    printf("CORE: Main script finished, cleaning up\n");
    mp_deinit();

    return 0;
}

// MicroPython default exception handler

void __attribute__((noreturn)) nlr_jump_fail(void *val) {
    ensure(secfalse, "uncaught exception");
}

void PendSV_Handler(void) {
    pendsv_isr_handler();
}

// MicroPython builtin stubs

mp_import_stat_t mp_import_stat(const char *path) {
    return MP_IMPORT_STAT_NO_EXIST;
}

mp_obj_t mp_builtin_open(uint n_args, const mp_obj_t *args, mp_map_t *kwargs) {
    return mp_const_none;
}
MP_DEFINE_CONST_FUN_OBJ_KW(mp_builtin_open_obj, 1, mp_builtin_open);
