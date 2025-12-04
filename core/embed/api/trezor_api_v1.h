/*
From musl include/elf.h

Copyright © 2005-2014 Rich Felker, et al.

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*/

#pragma once

#include <sys/sysevent.h>
#include <sys/system.h>
#include <sys/systick.h>

#ifdef USE_DBG_CONSOLE
#include <sys/dbg_console.h>
#endif

#ifdef USE_IPC
#include <sys/ipc.h>
#endif

#ifndef USE_DBG_CONSOLE
// temporary hack to allow compilation when DBG console is disabled
void dbg_console_write(const void* data, size_t data_size);
#endif

#define API_FN(ret_, name_, args_decl_, args_) ret_(*name_) args_decl_;
#define API_FN_VOID(name_, args_decl_, args_) void(*name_) args_decl_;

typedef struct {
#include "trezor_api_v1_def.h"
} trezor_api_v1_t;

#undef API_FN
#undef API_FN_VOID
