#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "usbd_core.h"
#include "usbd_desc.h"
#include "usbd_cdc_msc_hid.h"
#include "usbd_cdc_interface.h"
#include "usbd_hid_interface.h"

#include "py/nlr.h"
#include "py/compile.h"
#include "py/runtime.h"
#include "py/stackctrl.h"
#include "py/repl.h"
#include "py/gc.h"
#include "lib/utils/pyexec.h"

#include "pendsv.h"

void SystemClock_Config(void);

extern uint32_t _etext;
extern uint32_t _sidata;
extern uint32_t _ram_start;
extern uint32_t _sdata;
extern uint32_t _edata;
extern uint32_t _sbss;
extern uint32_t _ebss;
extern uint32_t _heap_start;
extern uint32_t _heap_end;
extern uint32_t _estack;
extern uint32_t _ram_end;

void flash_init(void);
void usb_init(void);

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

// Flash

void flash_init(void) {
    // Enable the flash IRQ, which is used to also call our storage IRQ handler
    // It needs to go at a higher priority than all those components that rely on
    // the flash storage (eg higher than USB MSC).
    HAL_NVIC_SetPriority(FLASH_IRQn, 2, 0);
    HAL_NVIC_EnableIRQ(FLASH_IRQn);
}

// USB

USBD_HandleTypeDef hUSBDDevice;

void usb_init(void) {
    const uint16_t vid = 0x1209;
    const uint16_t pid = 0x53C1;

    USBD_HID_ModeInfoTypeDef hid_info = {
        .subclass = 0,
        .protocol = 0,
        .max_packet_len = 64,
        .polling_interval = 1,
        .report_desc = (const uint8_t*)"\x06\x00\xff\x09\x01\xa1\x01\x09\x20\x15\x00\x26\xff\x00\x75\x08\x95\x40\x81\x02\x09\x21\x15\x00\x26\xff\x00\x75\x08\x95\x40\x91\x02\xc0",
        .report_desc_len = 34,
    };

    USBD_SetVIDPIDRelease(vid, pid, 0x0200, 0);
    if (USBD_SelectMode(USBD_MODE_CDC_HID, &hid_info) != 0) {
        for (;;) {
            __fatal_error("USB init failed");
        }
    }
    USBD_Init(&hUSBDDevice, (USBD_DescriptorsTypeDef*)&USBD_Descriptors, 0); // 0 == full speed
    USBD_RegisterClass(&hUSBDDevice, &USBD_CDC_MSC_HID);
    USBD_CDC_RegisterInterface(&hUSBDDevice, (USBD_CDC_ItfTypeDef*)&USBD_CDC_fops);
    USBD_HID_RegisterInterface(&hUSBDDevice, (USBD_HID_ItfTypeDef*)&USBD_HID_fops);
    USBD_Start(&hUSBDDevice);
}

// I2C

I2C_HandleTypeDef *i2c_handle = 0;

void i2c_init(I2C_HandleTypeDef *i2c) {

    // Enable I2C clock
    __HAL_RCC_I2C1_CLK_ENABLE();

    // Init SCL and SDA GPIO lines (PB6 & PB7)
    GPIO_InitTypeDef GPIO_InitStructure = {
        .Pin = GPIO_PIN_6 | GPIO_PIN_7,
        .Mode = GPIO_MODE_AF_OD,
        .Pull = GPIO_NOPULL,
        .Speed = GPIO_SPEED_FREQ_VERY_HIGH,
        .Alternate = GPIO_AF4_I2C1,
    };
    HAL_GPIO_Init(GPIOB, &GPIO_InitStructure);

    // Init I2C handle
    if (HAL_I2C_Init(i2c) != HAL_OK) {
        for (;;) {
            __fatal_error("i2c_init failed");
        }
    }

    // Enable IRQs
    i2c_handle = i2c;
    HAL_NVIC_EnableIRQ(I2C1_EV_IRQn);
    HAL_NVIC_EnableIRQ(I2C1_ER_IRQn);
}

// RNG

STATIC RNG_HandleTypeDef rng_handle = {
    .State = HAL_RNG_STATE_RESET,
    .Instance = RNG,
};

void rng_init(RNG_HandleTypeDef *rng) {

    // Enable RNG clock
    __HAL_RCC_RNG_CLK_ENABLE();

    // Init RNG handle
    HAL_RNG_Init(rng);
}

uint32_t rng_get(void) {
    if (rng_handle.State == HAL_RNG_STATE_RESET) {
        rng_init(&rng_handle);
    }

    return HAL_RNG_GetRandomNumber(&rng_handle);
}

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
