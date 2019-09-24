// clang-format off

/*
 * This file is part of the MicroPython project, http://micropython.org/
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2013-2017 Damien P. George
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

// Options to control how MicroPython is built for this port,
// overriding defaults in py/mpconfig.h.

#pragma once
#ifndef __INCLUDED_MPCONFIGPORT_H
#define __INCLUDED_MPCONFIGPORT_H

// stuff from py/mpconfig.h
#define MICROPY_ENABLE_COMPILER     (0)

// frozen modules
#define MICROPY_MODULE_FROZEN_MPY   (1)
#define MICROPY_QSTR_EXTRA_POOL     (mp_qstr_frozen_const_pool)

// memory allocation policies
#define MICROPY_ALLOC_PATH_MAX      (128)

// emitters
#define MICROPY_PERSISTENT_CODE_LOAD (0)
#define MICROPY_EMIT_THUMB          (0)
#define MICROPY_EMIT_INLINE_THUMB   (0)

// compiler configuration
#define MICROPY_COMP_MODULE_CONST   (1)
#define MICROPY_COMP_TRIPLE_TUPLE_ASSIGN (1)
#define MICROPY_COMP_RETURN_IF_EXPR (1)

// optimisations
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
#ifndef MICROPY_FLOAT_IMPL // can be configured by each board via mpconfigboard.mk
#define MICROPY_FLOAT_IMPL          (MICROPY_FLOAT_IMPL_FLOAT)
#endif
#define MICROPY_STREAMS_NON_BLOCK   (1)
#define MICROPY_MODULE_WEAK_LINKS   (1)
#define MICROPY_CAN_OVERRIDE_BUILTINS (0)
#define MICROPY_USE_INTERNAL_ERRNO  (1)
#define MICROPY_ENABLE_SCHEDULER    (0)
#define MICROPY_SCHEDULER_DEPTH     (0)
#define MICROPY_VFS                 (0)
#define MICROPY_VFS_FAT             (0)

// control over Python builtins
#define MICROPY_PY_FUNCTION_ATTRS   (1)
#define MICROPY_PY_BUILTINS_STR_UNICODE (1)
#define MICROPY_PY_BUILTINS_STR_CENTER (1)
#define MICROPY_PY_BUILTINS_STR_PARTITION (0)
#define MICROPY_PY_BUILTINS_STR_SPLITLINES (0)
#define MICROPY_PY_BUILTINS_MEMORYVIEW (1)
#define MICROPY_PY_BUILTINS_FROZENSET (0)
#define MICROPY_PY_BUILTINS_SLICE_ATTRS (1)
#define MICROPY_PY_ALL_SPECIAL_METHODS (0)
#define MICROPY_PY_BUILTINS_COMPILE (0)
#define MICROPY_PY_BUILTINS_EXECFILE (0)
#define MICROPY_PY_BUILTINS_INPUT   (0)
#define MICROPY_PY_BUILTINS_POW3    (0)
#define MICROPY_PY_BUILTINS_HELP    (0)
#define MICROPY_PY_BUILTINS_HELP_TEXT stm32_help_text
#define MICROPY_PY_BUILTINS_HELP_MODULES (0)
#define MICROPY_PY_MICROPYTHON_MEM_INFO (1)
#define MICROPY_PY_ARRAY_SLICE_ASSIGN (1)
#define MICROPY_PY_COLLECTIONS        (0)
#define MICROPY_PY_COLLECTIONS_ORDEREDDICT (0)
#define MICROPY_PY_MATH_SPECIAL_FUNCTIONS (0)
#define MICROPY_PY_CMATH            (0)
#define MICROPY_PY_IO               (0)
#define MICROPY_PY_IO_FILEIO        (0)
#define MICROPY_PY_SYS_MAXSIZE      (0)
#define MICROPY_PY_SYS_EXIT         (0)
#define MICROPY_PY_SYS_STDFILES     (0)
#define MICROPY_PY_SYS_STDIO_BUFFER (0)
#define MICROPY_PY_UERRNO           (0)
#ifndef MICROPY_PY_THREAD
#define MICROPY_PY_THREAD           (0)
#endif
#define MICROPY_PY_THREAD_GIL       (0)

// extended modules
#define MICROPY_PY_UCTYPES          (1)
#define MICROPY_PY_UZLIB            (0)
#define MICROPY_PY_UJSON            (0)
#define MICROPY_PY_URE              (0)
#define MICROPY_PY_UHEAPQ           (0)
#define MICROPY_PY_UHASHLIB         (0)
#define MICROPY_PY_UBINASCII        (1)
#define MICROPY_PY_UBINASCII_CRC32  (0)
#define MICROPY_PY_URANDOM          (0)
#define MICROPY_PY_URANDOM_EXTRA_FUNCS (0)
#define MICROPY_PY_USELECT          (0)
#define MICROPY_PY_UTIMEQ           (1)
#define MICROPY_PY_UTIME_MP_HAL     (1)
#define MICROPY_PY_MACHINE          (0)
#define MICROPY_PY_FRAMEBUF         (0)
#define MICROPY_PY_USOCKET          (0)
#define MICROPY_PY_NETWORK          (0)

#define MICROPY_PY_TREZORCONFIG     (1)
#define MICROPY_PY_TREZORCRYPTO     (1)
#define MICROPY_PY_TREZORIO         (1)
#define MICROPY_PY_TREZORUI         (1)
#define MICROPY_PY_TREZORUTILS      (1)

// extra built in names to add to the global namespace
#define MICROPY_PORT_BUILTINS

// extra built in modules to add to the list of known ones
extern const struct _mp_obj_module_t mp_module_utime;
extern const struct _mp_obj_module_t mp_module_trezorconfig;
extern const struct _mp_obj_module_t mp_module_trezorcrypto;
extern const struct _mp_obj_module_t mp_module_trezorio;
extern const struct _mp_obj_module_t mp_module_trezorui;
extern const struct _mp_obj_module_t mp_module_trezorutils;

#define MICROPY_PORT_BUILTIN_MODULES \
    { MP_ROM_QSTR(MP_QSTR_utime), MP_ROM_PTR(&mp_module_utime) }, \
    { MP_ROM_QSTR(MP_QSTR_trezorconfig), MP_ROM_PTR(&mp_module_trezorconfig) }, \
    { MP_ROM_QSTR(MP_QSTR_trezorcrypto), MP_ROM_PTR(&mp_module_trezorcrypto) }, \
    { MP_ROM_QSTR(MP_QSTR_trezorio), MP_ROM_PTR(&mp_module_trezorio) }, \
    { MP_ROM_QSTR(MP_QSTR_trezorui), MP_ROM_PTR(&mp_module_trezorui) }, \
    { MP_ROM_QSTR(MP_QSTR_trezorutils), MP_ROM_PTR(&mp_module_trezorutils) },

#define MP_STATE_PORT MP_STATE_VM

#define MICROPY_PORT_ROOT_POINTERS \
    const char *readline_hist[8]; \

// type definitions for the specific machine

#define BYTES_PER_WORD (4)

#define MICROPY_MAKE_POINTER_CALLABLE(p) ((void*)((mp_uint_t)(p) | 1))

#define MP_SSIZE_MAX (0x0fffffff)

#define UINT_FMT "%u"
#define INT_FMT "%d"

typedef int mp_int_t; // must be pointer size
typedef unsigned int mp_uint_t; // must be pointer size
typedef long mp_off_t;

#define MP_PLAT_PRINT_STRN(str, len) mp_hal_stdout_tx_strn_cooked(str, len)

// We have inlined IRQ functions for efficiency (they are generally
// 1 machine instruction).
//
// Note on IRQ state: you should not need to know the specific
// value of the state variable, but rather just pass the return
// value from disable_irq back to enable_irq.  If you really need
// to know the machine-specific values, see irq.h.

#include STM32_HAL_H

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
#define MICROPY_HW_MCU_NAME "STM32F427xx"
#define MICROPY_PY_SYS_PLATFORM "trezor"
#define MICROPY_HW_HAS_SDCARD 1

// There is no classical C heap in bare-metal ports, only Python
// garbage-collected heap. For completeness, emulate C heap via
// GC heap. Note that MicroPython core never uses malloc() and friends,
// so these defines are mostly to help extension module writers.
#define malloc(n) m_malloc(n)
#define free(p) m_free(p)
#define realloc(p, n) m_realloc(p, n)

// We need to provide a declaration/definition of alloca()
#include <alloca.h>

#endif // __INCLUDED_MPCONFIGPORT_H
