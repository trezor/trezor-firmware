/*
 * This file is part of the MicroPython project, http://micropython.org/
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2013-2015 Damien P. George
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#include <stdbool.h> // bool
#include <alloca.h>  // alloca

// Memory allocation policies
#define MICROPY_ALLOC_PATH_MAX      (128)

// Emitters
#define MICROPY_PERSISTENT_CODE_LOAD (0)
#define MICROPY_EMIT_THUMB          (0)
#define MICROPY_EMIT_INLINE_THUMB   (0)

// Compiler configuration
#define MICROPY_COMP_MODULE_CONST   (1)
#define MICROPY_COMP_TRIPLE_TUPLE_ASSIGN (1)

// Optimisations
#define MICROPY_OPT_COMPUTED_GOTO   (1)
#define MICROPY_OPT_CACHE_MAP_LOOKUP_IN_BYTECODE (0)
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
#define MICROPY_CAN_OVERRIDE_BUILTINS (1)
#define MICROPY_USE_INTERNAL_ERRNO  (1)
#define MICROPY_VFS                 (0)
#define MICROPY_VFS_FAT             (0)

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
#define MICROPY_PY_UBINASCII_CRC32  (1)
#define MICROPY_PY_UCTYPES          (1)
#define MICROPY_PY_UZLIB            (1)
#define MICROPY_PY_UTIME_MP_HAL     (1)
#define MICROPY_PY_UTIMEQ           (1)
#define MICROPY_PY_TREZORCONFIG     (1)
#define MICROPY_PY_TREZORCRYPTO     (1)
#define MICROPY_PY_TREZORIO         (1)
#define MICROPY_PY_TREZORMSG        (1)
#define MICROPY_PY_TREZORUI         (1)
#define MICROPY_PY_TREZORUTILS      (1)

// Type definitions for the specific machine

#include STM32_HAL_H

#define BYTES_PER_WORD (4)

#define MICROPY_MAKE_POINTER_CALLABLE(p) ((void*)((mp_uint_t)(p) | 1))

#define INT_FMT  "%d"
#define UINT_FMT "%u"
#define MP_SSIZE_MAX (0x0fffffff)

typedef long mp_off_t;
typedef int mp_int_t;
typedef unsigned mp_uint_t;

static inline void enable_irq(mp_uint_t state) {
    __set_PRIMASK(state);
}

static inline mp_uint_t disable_irq(void) {
    mp_uint_t state = __get_PRIMASK();
    __disable_irq();
    return state;
}

#define MICROPY_BEGIN_ATOMIC_SECTION()     disable_irq()
#define MICROPY_END_ATOMIC_SECTION(state)  enable_irq(state)
#define MICROPY_EVENT_POLL_HOOK            __WFI();

#define MICROPY_HW_BOARD_NAME "TREZORv2"
#define MICROPY_HW_MCU_NAME "STM32F405VG"
#define MICROPY_PY_SYS_PLATFORM "trezor"

#define MICROPY_PORT_ROOT_POINTERS

#define MP_STATE_PORT MP_STATE_VM

// Extra built in modules to add to the list of known ones
extern const struct _mp_obj_module_t mp_module_utime;
extern const struct _mp_obj_module_t mp_module_TrezorConfig;
extern const struct _mp_obj_module_t mp_module_TrezorCrypto;
extern const struct _mp_obj_module_t mp_module_TrezorIO;
extern const struct _mp_obj_module_t mp_module_TrezorMsg;
extern const struct _mp_obj_module_t mp_module_TrezorUi;
extern const struct _mp_obj_module_t mp_module_TrezorUtils;
#define MICROPY_PORT_BUILTIN_MODULES \
    { MP_OBJ_NEW_QSTR(MP_QSTR_utime), (mp_obj_t)&mp_module_utime }, \
    { MP_OBJ_NEW_QSTR(MP_QSTR_TrezorConfig), (mp_obj_t)&mp_module_TrezorConfig }, \
    { MP_OBJ_NEW_QSTR(MP_QSTR_TrezorCrypto), (mp_obj_t)&mp_module_TrezorCrypto }, \
    { MP_OBJ_NEW_QSTR(MP_QSTR_TrezorIO), (mp_obj_t)&mp_module_TrezorIO }, \
    { MP_OBJ_NEW_QSTR(MP_QSTR_TrezorMsg), (mp_obj_t)&mp_module_TrezorMsg }, \
    { MP_OBJ_NEW_QSTR(MP_QSTR_TrezorUi), (mp_obj_t)&mp_module_TrezorUi }, \
    { MP_OBJ_NEW_QSTR(MP_QSTR_TrezorUtils), (mp_obj_t)&mp_module_TrezorUtils },

// Extra built in names to add to the global namespace
#define MICROPY_PORT_BUILTINS \
    { MP_OBJ_NEW_QSTR(MP_QSTR_open), (mp_obj_t)&mp_builtin_open_obj },

// Make sure all allocations are done through GC
#define malloc(n) m_malloc(n)
#define free(p) m_free(p)
#define realloc(p, n) m_realloc(p, n)
