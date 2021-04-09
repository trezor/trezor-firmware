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

// frozen modules
#ifdef TREZOR_EMULATOR_FROZEN
#define MICROPY_MODULE_FROZEN_MPY   (1)
#define MICROPY_QSTR_EXTRA_POOL     (mp_qstr_frozen_const_pool)
#define MPZ_DIG_SIZE                (16)
#endif

// memory allocation policies
#define MICROPY_ALLOC_PATH_MAX      (PATH_MAX)
#define MICROPY_MALLOC_USES_ALLOCATED_SIZE (1)
#define MICROPY_MEM_STATS           (1)
#define MICROPY_ENABLE_PYSTACK      (1)
#define MICROPY_LOADED_MODULES_DICT_SIZE (160)

// emitters
#define MICROPY_PERSISTENT_CODE_LOAD (0)

// compiler configuration
#define MICROPY_ENABLE_COMPILER     (1)
#define MICROPY_COMP_MODULE_CONST   (1)
#define MICROPY_COMP_TRIPLE_TUPLE_ASSIGN (1)
#define MICROPY_COMP_RETURN_IF_EXPR (1)
#define MICROPY_HELPER_LEXER_UNIX   (1)
#define MICROPY_READER_POSIX        (1)

// optimisations
#define MICROPY_OPT_COMPUTED_GOTO   (1)
#define MICROPY_OPT_CACHE_MAP_LOOKUP_IN_BYTECODE (0)
#define MICROPY_OPT_MPZ_BITWISE     (1)
#define MICROPY_OPT_MATH_FACTORIAL  (0)

// Python internal features
#define MICROPY_READER_VFS          (0)
#define MICROPY_ENABLE_GC           (1)
#define MICROPY_ENABLE_FINALISER    (1)
#define MICROPY_STACK_CHECK         (1)
#define MICROPY_ENABLE_EMERGENCY_EXCEPTION_BUF (1)
#define MICROPY_EMERGENCY_EXCEPTION_BUF_SIZE (256)
#define MICROPY_KBD_EXCEPTION       (1)
#define MICROPY_USE_READLINE         (1)
#define MICROPY_USE_READLINE_HISTORY (1)
#define MICROPY_HELPER_REPL         (1)
#define MICROPY_REPL_EMACS_KEYS     (1)
#define MICROPY_REPL_AUTO_INDENT    (1)
#define MICROPY_LONGINT_IMPL        (MICROPY_LONGINT_IMPL_MPZ)
#define MICROPY_ENABLE_SOURCE_LINE  (1)
#define MICROPY_FLOAT_IMPL          (MICROPY_FLOAT_IMPL_FLOAT)
#define MICROPY_STREAMS_NON_BLOCK   (1)
#define MICROPY_MODULE_WEAK_LINKS   (1)
#define MICROPY_CAN_OVERRIDE_BUILTINS (0)
#define MICROPY_VFS_POSIX_FILE      (1)
#define MICROPY_USE_INTERNAL_ERRNO  (0)
#define MICROPY_ENABLE_SCHEDULER    (0)
#define MICROPY_SCHEDULER_DEPTH     (0)
#define MICROPY_VFS                 (0)

// control over Python builtins
#define MICROPY_PY_FUNCTION_ATTRS   (1)
#define MICROPY_PY_DESCRIPTORS      (0)
#define MICROPY_PY_DELATTR_SETATTR  (0)
#define MICROPY_PY_BUILTINS_STR_UNICODE (1)
#define MICROPY_PY_BUILTINS_STR_CENTER (1)
#define MICROPY_PY_BUILTINS_STR_PARTITION (0)
#define MICROPY_PY_BUILTINS_STR_SPLITLINES (0)
#define MICROPY_PY_BUILTINS_MEMORYVIEW (1)
#define MICROPY_PY_BUILTINS_FROZENSET (0)
#define MICROPY_PY_BUILTINS_SLICE_ATTRS (1)
#define MICROPY_PY_BUILTINS_SLICE_INDICES (0)
#define MICROPY_PY_BUILTINS_ROUND_INT (0)
#define MICROPY_PY_REVERSE_SPECIAL_METHODS (0)
#define MICROPY_PY_ALL_SPECIAL_METHODS (0)
#define MICROPY_PY_BUILTINS_COMPILE (MICROPY_ENABLE_COMPILER)
#define MICROPY_PY_BUILTINS_EXECFILE (MICROPY_ENABLE_COMPILER)
#define MICROPY_PY_BUILTINS_NOTIMPLEMENTED (1)
#define MICROPY_PY_BUILTINS_INPUT   (0)
#define MICROPY_PY_BUILTINS_POW3    (0)
#define MICROPY_PY_BUILTINS_HELP    (0)
#define MICROPY_PY_BUILTINS_HELP_TEXT stm32_help_text
#define MICROPY_PY_BUILTINS_HELP_MODULES (0)
#define MICROPY_PY_MICROPYTHON_MEM_INFO (1)
#define MICROPY_PY_ARRAY_SLICE_ASSIGN (1)
#define MICROPY_PY_COLLECTIONS       (0)
#define MICROPY_PY_COLLECTIONS_DEQUE (0)
#define MICROPY_PY_COLLECTIONS_ORDEREDDICT (0)
#define MICROPY_PY_MATH_SPECIAL_FUNCTIONS (0)
#define MICROPY_PY_MATH_ISCLOSE     (0)
#define MICROPY_PY_MATH_FACTORIAL   (0)
#define MICROPY_PY_CMATH            (0)
#define MICROPY_PY_IO               (1)
#define MICROPY_PY_IO_IOBASE        (1)
#define MICROPY_PY_IO_FILEIO        (1)
#define MICROPY_PY_SYS_MAXSIZE      (0)
#define MICROPY_PY_SYS_EXIT         (0)
#define MICROPY_PY_SYS_STDFILES     (0)
#define MICROPY_PY_SYS_STDIO_BUFFER (0)
#define MICROPY_PY_SYS_PLATFORM     "trezor-emulator"
#define MICROPY_PY_UERRNO           (0)
#define MICROPY_PY_THREAD           (0)

// extended modules
#define MICROPY_PY_UCTYPES          (1)
#define MICROPY_PY_UZLIB            (0)
#define MICROPY_PY_UJSON            (0)
#define MICROPY_PY_URE              (0)
#define MICROPY_PY_URE_SUB          (0)
#define MICROPY_PY_UHEAPQ           (0)
#define MICROPY_PY_UHASHLIB         (0)
#define MICROPY_PY_UHASHLIB_MD5     (0)
#define MICROPY_PY_UHASHLIB_SHA1    (0)
#define MICROPY_PY_UCRYPTOLIB       (0)
#define MICROPY_PY_UBINASCII        (1)
#define MICROPY_PY_UBINASCII_CRC32  (0)
#define MICROPY_PY_URANDOM          (0)
#define MICROPY_PY_URANDOM_EXTRA_FUNCS (0)
#define MICROPY_PY_USELECT          (0)
#define MICROPY_PY_UTIMEQ           (1)
#define MICROPY_PY_UTIME            (1)
#define MICROPY_PY_UTIME_MP_HAL     (1)
#define MICROPY_PY_OS_DUPTERM       (0)
#define MICROPY_PY_LWIP_SOCK_RAW    (0)
#define MICROPY_PY_MACHINE          (0)
#define MICROPY_PY_UWEBSOCKET       (0)
#define MICROPY_PY_WEBREPL          (0)
#define MICROPY_PY_FRAMEBUF         (0)
#define MICROPY_PY_USOCKET          (0)
#define MICROPY_PY_NETWORK          (0)

// Debugging and interactive functionality.
#define MICROPY_DEBUG_PRINTERS      (1)
// Printing debug to stderr may give tests which
// check stdout a chance to pass, etc.
#define MICROPY_DEBUG_PRINTER       (&mp_stderr_print)
#define MICROPY_ASYNC_KBD_INTR      (1)

#define mp_type_fileio mp_type_vfs_posix_fileio
#define mp_type_textio mp_type_vfs_posix_textio

// Define to MICROPY_ERROR_REPORTING_DETAILED to get function, etc.
// names in exception messages (may require more RAM).
#define MICROPY_ERROR_REPORTING     (MICROPY_ERROR_REPORTING_DETAILED)
#define MICROPY_WARNINGS            (1)
#define MICROPY_ERROR_PRINTER       (&mp_stderr_print)
#define MICROPY_PY_STR_BYTES_CMP_WARN (1)

extern const struct _mp_print_t mp_stderr_print;

// coverage support
#define MICROPY_PY_SYS_ATEXIT       (1)
#define MICROPY_PY_SYS_SETTRACE     (1)
#if MICROPY_PY_SYS_SETTRACE
#define MICROPY_PERSISTENT_CODE_SAVE (1)
#define MICROPY_COMP_CONST (0)
#endif
#define MICROPY_PY_SYS_EXC_INFO     (1)

// extern const struct _mp_print_t mp_stderr_print;

#define MICROPY_PY_TREZORCONFIG     (1)
#define MICROPY_PY_TREZORCRYPTO     (1)
#define MICROPY_PY_TREZORIO         (1)
#define MICROPY_PY_TREZORUI         (1)
#define MICROPY_PY_TREZORUTILS      (1)

#define MP_STATE_PORT MP_STATE_VM

// ============= this ends common config section ===================

// extra built in modules to add to the list of known ones
extern const struct _mp_obj_module_t mp_module_os;
// on unix, we use time, not utime
extern const struct _mp_obj_module_t mp_module_time;

#define MICROPY_PORT_BUILTIN_MODULES \
    { MP_ROM_QSTR(MP_QSTR_uos), MP_ROM_PTR(&mp_module_os) }, \
    { MP_ROM_QSTR(MP_QSTR_utime), MP_ROM_PTR(&mp_module_time) },



// For size_t and ssize_t
#include <unistd.h>

// assume that if we already defined the obj repr then we also defined types
#ifndef MICROPY_OBJ_REPR
#ifdef __LP64__
typedef long mp_int_t; // must be pointer size
typedef unsigned long mp_uint_t; // must be pointer size
#else
// These are definitions for machines where sizeof(int) == sizeof(void*),
// regardless of actual size.
typedef int mp_int_t; // must be pointer size
typedef unsigned int mp_uint_t; // must be pointer size
#endif
#endif

#define MICROPY_EVENT_POLL_HOOK mp_hal_delay_ms(1);

// Cannot include <sys/types.h>, as it may lead to symbol name clashes
#if _FILE_OFFSET_BITS == 64 && !defined(__LP64__)
typedef long long mp_off_t;
#else
typedef long mp_off_t;
#endif

void mp_unix_alloc_exec(size_t min_size, void** ptr, size_t *size);
void mp_unix_free_exec(void *ptr, size_t size);
void mp_unix_mark_exec(void);
#define MP_PLAT_ALLOC_EXEC(min_size, ptr, size) mp_unix_alloc_exec(min_size, ptr, size)
#define MP_PLAT_FREE_EXEC(ptr, size) mp_unix_free_exec(ptr, size)
#ifndef MICROPY_FORCE_PLAT_ALLOC_EXEC
// Use MP_PLAT_ALLOC_EXEC for any executable memory allocation, including for FFI
// (overriding libffi own implementation)
#define MICROPY_FORCE_PLAT_ALLOC_EXEC (1)
#endif

#ifdef __linux__
// Can access physical memory using /dev/mem
#define MICROPY_PLAT_DEV_MEM  (1)
#endif

// Assume that select() call, interrupted with a signal, and erroring
// with EINTR, updates remaining timeout value.
#define MICROPY_SELECT_REMAINING_TIME (1)

#define MICROPY_PORT_ROOT_POINTERS \
    const char *readline_hist[50]; \
    void *mmap_region_head; \
    mp_obj_t trezorconfig_ui_wait_callback; \

// We need to provide a declaration/definition of alloca()
// unless support for it is disabled.
#if !defined(MICROPY_NO_ALLOCA) || MICROPY_NO_ALLOCA == 0
#ifdef __FreeBSD__
#include <stdlib.h>
#else
#include <alloca.h>
#endif
#endif

// From "man readdir": "Under glibc, programs can check for the availability
// of the fields [in struct dirent] not defined in POSIX.1 by testing whether
// the macros [...], _DIRENT_HAVE_D_TYPE are defined."
// Other libc's don't define it, but proactively assume that dirent->d_type
// is available on a modern *nix system.
#ifndef _DIRENT_HAVE_D_TYPE
#define _DIRENT_HAVE_D_TYPE (1)
#endif
// This macro is not provided by glibc but we need it so ports that don't have
// dirent->d_ino can disable the use of this field.
#ifndef _DIRENT_HAVE_D_INO
#define _DIRENT_HAVE_D_INO (1)
#endif

#ifndef __APPLE__
// For debugging purposes, make printf() available to any source file.
#include <stdio.h>
#endif

#endif // __INCLUDED_MPCONFIGPORT_H
