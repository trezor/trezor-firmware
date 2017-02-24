#include <limits.h>
#include <stdint.h>
#include <stdbool.h>
#include <alloca.h>

// Memory allocation policies
#define MICROPY_ALLOC_PATH_MAX      (128)

// Emitters
#define MICROPY_PERSISTENT_CODE_LOAD (0)
#define MICROPY_EMIT_THUMB          (0)
#define MICROPY_EMIT_INLINE_THUMB   (0)

// Compiler configuration
#define MICROPY_ENABLE_COMPILER     (1)
#define MICROPY_COMP_MODULE_CONST   (1)
#define MICROPY_COMP_DOUBLE_TUPLE_ASSIGN (1)
#define MICROPY_COMP_TRIPLE_TUPLE_ASSIGN (1)

// Optimisations
#define MICROPY_OPT_COMPUTED_GOTO   (1)
#define MICROPY_OPT_MPZ_BITWISE     (1)

// Python internal features
#define MICROPY_READER_VFS          (0)
#define MICROPY_ENABLE_GC           (1)
#define MICROPY_ENABLE_FINALISER    (1)
#define MICROPY_STACK_CHECK         (1)
#define MICROPY_ENABLE_EMERGENCY_EXCEPTION_BUF (1)
#define MICROPY_EMERGENCY_EXCEPTION_BUF_SIZE (0)
#define MICROPY_KBD_EXCEPTION       (1)
#define MICROPY_HELPER_REPL         (1)
#define MICROPY_REPL_EMACS_KEYS     (1)
#define MICROPY_REPL_AUTO_INDENT    (1)
#define MICROPY_LONGINT_IMPL        (MICROPY_LONGINT_IMPL_MPZ)
#define MICROPY_ENABLE_SOURCE_LINE  (1)
#define MICROPY_FLOAT_IMPL          (MICROPY_FLOAT_IMPL_FLOAT)
#define MICROPY_STREAMS_NON_BLOCK   (1)
#define MICROPY_MODULE_WEAK_LINKS   (1)
#define MICROPY_MODULE_FROZEN_MPY   (1)
#define MICROPY_CAN_OVERRIDE_BUILTINS (1)
#define MICROPY_USE_INTERNAL_ERRNO  (1)
#define MICROPY_VFS                 (0)
#define MICROPY_VFS_FAT             (0)
#define MICROPY_QSTR_EXTRA_POOL     mp_qstr_frozen_const_pool

// Control over Python builtins
#define MICROPY_PY_FUNCTION_ATTRS   (1)
#define MICROPY_PY_BUILTINS_STR_UNICODE (1)
#define MICROPY_PY_BUILTINS_STR_CENTER (1)
#define MICROPY_PY_BUILTINS_STR_PARTITION (1)
#define MICROPY_PY_BUILTINS_STR_SPLITLINES (1)
#define MICROPY_PY_BUILTINS_MEMORYVIEW (1)
#define MICROPY_PY_BUILTINS_FROZENSET (1)
#define MICROPY_PY_BUILTINS_SLICE_ATTRS (1)
#define MICROPY_PY_ALL_SPECIAL_METHODS (1)
#define MICROPY_PY_BUILTINS_COMPILE (1)
#define MICROPY_PY_BUILTINS_EXECFILE (1)
#define MICROPY_PY_BUILTINS_POW3    (0)
#define MICROPY_PY_BUILTINS_HELP    (0)
#define MICROPY_PY_BUILTINS_HELP_MODULES (0)
#define MICROPY_PY_MICROPYTHON_MEM_INFO (1)
#define MICROPY_PY_ARRAY_SLICE_ASSIGN (1)
#define MICROPY_PY_COLLECTIONS_ORDEREDDICT (1)
#define MICROPY_PY_MATH_SPECIAL_FUNCTIONS (1)
#define MICROPY_PY_CMATH            (1)
#define MICROPY_PY_IO               (0)
#define MICROPY_PY_IO_FILEIO        (0)
#define MICROPY_PY_SYS_MAXSIZE      (0)
#define MICROPY_PY_SYS_EXIT         (0)
#define MICROPY_PY_SYS_STDFILES     (0)
#define MICROPY_PY_SYS_STDIO_BUFFER (0)
#define MICROPY_PY_UERRNO           (1)
#define MICROPY_PY_THREAD           (0)
#define MICROPY_PY_THREAD_GIL       (0)

// Extended modules
#define MICROPY_PY_UBINASCII        (1)
#define MICROPY_PY_UCTYPES          (1)
#define MICROPY_PY_UZLIB            (1)
#define MICROPY_PY_UTIME_MP_HAL     (1)
#define MICROPY_PY_UTIMEQ           (1)
#define MICROPY_PY_TREZORCONFIG     (1)
#define MICROPY_PY_TREZORCRYPTO     (1)
#define MICROPY_PY_TREZORDEBUG      (1)
#define MICROPY_PY_TREZORMSG        (1)
#define MICROPY_PY_TREZORUI         (1)
#define MICROPY_PY_TREZORUTILS      (1)

// Type definitions for the specific machine

#include STM32_HAL_H

static inline void enable_irq(uint32_t state) {
    __set_PRIMASK(state);
}

static inline uint32_t disable_irq(void) {
    uint32_t st = __get_PRIMASK();
    __disable_irq();
    return st;
}

#define BYTES_PER_WORD (4)
#define MP_HAL_UNIQUE_ID_ADDRESS (0x1fff7a10)
#define MICROPY_MAKE_POINTER_CALLABLE(p) ((void*)((mp_uint_t)(p) | 1))
#define MP_PLAT_PRINT_STRN(str, len) mp_hal_stdout_tx_strn_cooked(str, len)

// This port is intended to be 32-bit, but unfortunately, int32_t for
// different targets may be defined in different ways - either as int
// or as long. This requires different printf formatting specifiers
// to print such value. So, we avoid int32_t and use int directly.
#define UINT_FMT "%u"
#define INT_FMT "%d"
typedef int mp_int_t; // must be pointer size
typedef unsigned mp_uint_t; // must be pointer size
typedef long mp_off_t;

#define MP_SSIZE_MAX INT_MAX
#define MICROPY_MIN_USE_CORTEX_CPU  (1)
#define MICROPY_MIN_USE_STM32_MCU   (1)
#define MICROPY_HW_BOARD_NAME "TREZORv2"
#define MICROPY_HW_MCU_NAME "STM32F405VG"
#define MICROPY_PY_SYS_PLATFORM "trezor"

#define MP_STATE_PORT MP_STATE_VM
#define MICROPY_PORT_ROOT_POINTERS const char *readline_hist[8];

extern const struct _mp_obj_module_t mp_module_utime;
extern const struct _mp_obj_module_t mp_module_TrezorConfig;
extern const struct _mp_obj_module_t mp_module_TrezorCrypto;
extern const struct _mp_obj_module_t mp_module_TrezorDebug;
extern const struct _mp_obj_module_t mp_module_TrezorMsg;
extern const struct _mp_obj_module_t mp_module_TrezorUi;
extern const struct _mp_obj_module_t mp_module_TrezorUtils;

// Extra built in modules to add to the list of known ones
#define MICROPY_PORT_BUILTIN_MODULES \
    { MP_OBJ_NEW_QSTR(MP_QSTR_utime), (mp_obj_t)&mp_module_utime }, \
    { MP_OBJ_NEW_QSTR(MP_QSTR_TrezorConfig), (mp_obj_t)&mp_module_TrezorConfig }, \
    { MP_OBJ_NEW_QSTR(MP_QSTR_TrezorCrypto), (mp_obj_t)&mp_module_TrezorCrypto }, \
    { MP_OBJ_NEW_QSTR(MP_QSTR_TrezorDebug), (mp_obj_t)&mp_module_TrezorDebug }, \
    { MP_OBJ_NEW_QSTR(MP_QSTR_TrezorMsg), (mp_obj_t)&mp_module_TrezorMsg }, \
    { MP_OBJ_NEW_QSTR(MP_QSTR_TrezorUi), (mp_obj_t)&mp_module_TrezorUi }, \
    { MP_OBJ_NEW_QSTR(MP_QSTR_TrezorUtils), (mp_obj_t)&mp_module_TrezorUtils },

// Extra built in names to add to the global namespace
#define MICROPY_PORT_BUILTINS \
    { MP_OBJ_NEW_QSTR(MP_QSTR_open), (mp_obj_t)&mp_builtin_open_obj },

// Timing functions

#include "stmhal/systick.h"

#define mp_hal_delay_ms HAL_Delay
#define mp_hal_delay_us(us) sys_tick_udelay(us)
#define mp_hal_delay_us_fast(us) sys_tick_udelay(us)
#define mp_hal_ticks_ms HAL_GetTick
#define mp_hal_ticks_us() sys_tick_get_microseconds()

extern bool mp_hal_ticks_cpu_enabled;

void mp_hal_ticks_cpu_enable(void);

static inline mp_uint_t mp_hal_ticks_cpu(void) {
    if (!mp_hal_ticks_cpu_enabled) {
        mp_hal_ticks_cpu_enable();
    }
    return DWT->CYCCNT;
}
