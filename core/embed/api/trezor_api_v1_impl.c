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

#include "trezor_api_v1.h"

#ifndef USE_DBG_CONSOLE
// temporary hack to allow compilation when DBG console is disabled
void dbg_console_write(const void* data, size_t data_size) {}
#endif

const trezor_api_v1_t trezor_api_v1 = {
    .system_exit = system_exit,
    .system_exit_error = system_exit_error,
    .system_exit_error_ex = system_exit_error_ex,
    .system_exit_fatal = system_exit_fatal,
    .system_exit_fatal_ex = system_exit_fatal_ex,
    .systick_ms = systick_ms,
    .sysevents_poll = sysevents_poll,
    .syshandle_read = syshandle_read,
    .dbg_console_write = dbg_console_write,
    .ipc_register = ipc_register,
    .ipc_unregister = ipc_unregister,
    .ipc_try_receive = ipc_try_receive,
    .ipc_message_free = ipc_message_free,
    .ipc_send = ipc_send,
};

const void* coreapp_api_get(uint32_t version) {
  if (version == 1) {
    return &trezor_api_v1;
  }
  return NULL;
}
