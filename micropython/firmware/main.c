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

void SystemClock_Config(void);
void USBD_CDC_TxAlways(const uint8_t * buf, uint32_t len);
int USBD_CDC_Rx(uint8_t * buf, uint32_t len, uint32_t timeout);

void flash_init(void);
void usb_init(void);
void i2c_init(void);

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

    pendsv_init();
    flash_init();
    usb_init();
    i2c_init();

    // TODO: sdcard

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

// Errors

void NORETURN nlr_jump_fail(void *val) {
    for (;;) {}
}

void NORETURN __fatal_error(const char *msg) {
    for (;;) {}
}

#ifndef NDEBUG
void MP_WEAK __assert_func(const char *file, int line, const char *func, const char *expr) {
    printf("Assertion '%s' failed, at file %s:%d\n", expr, file, line);
    __fatal_error("Assertion failed");
}
#endif

// I/O

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

int mp_hal_stdin_rx_chr(void) {
    for (;;) {
        byte c;
        if (USBD_CDC_Rx(&c, 1, 0) != 0) {
            return c;
        }
    }
}

void mp_hal_stdout_tx_strn(const char *str, size_t len) {
    USBD_CDC_TxAlways((const uint8_t*)str, len);
}

int mp_reader_new_file(mp_reader_t *reader, const char *filename) {
    return 2; // assume error was "file not found"
}

// Time

bool mp_hal_ticks_cpu_enabled;

void mp_hal_ticks_cpu_enable(void) {
    if (!mp_hal_ticks_cpu_enabled) {
        // CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
        // DWT->CYCCNT = 0;
        // DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
        mp_hal_ticks_cpu_enabled = true;
    }
}
