#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "py/nlr.h"
#include "py/compile.h"
#include "py/runtime.h"
#include "py/stackctrl.h"
#include "py/repl.h"
#include "py/gc.h"
#include "lib/utils/pyexec.h"

#include "gccollect.h"
#include "pendsv.h"

#include "flash.h"
#include "rng.h"
#include "sdcard.h"
#include "touch.h"
#include "usb.h"

void SystemClock_Config(void);

void NORETURN nlr_jump_fail(void *val) {
    for (;;) {}
}

void NORETURN __fatal_error(const char *msg) {
    for (;;) {}
}

int main(void) {

    // STM32F4xx HAL library initialization:
    //  - configure the Flash prefetch, instruction and data caches
    //  - configure the Systick to generate an interrupt each 1 msec
    //  - set NVIC Group Priority to 4
    //  - global MSP (MCU Support Package) initialization
    HAL_Init();

    // Set the system clock to be HSE
    SystemClock_Config();

    // Enable GPIO clocks
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();

    // Enable the CCM RAM
    __HAL_RCC_CCMDATARAMEN_CLK_ENABLE();

    // machine_init
    if (PWR->CSR & PWR_CSR_SBF) {
        PWR->CR |= PWR_CR_CSBF;
    }
    RCC->CSR |= RCC_CSR_RMVF;

    // Enable CPU ticks
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    DWT->CYCCNT = 0;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;

    pendsv_init();

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

    if (0 != usb_init()) {
        __fatal_error("usb_init failed");
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

int mp_reader_new_file(mp_reader_t *reader, const char *filename) {
    return 2; // assume error was "file not found"
}
