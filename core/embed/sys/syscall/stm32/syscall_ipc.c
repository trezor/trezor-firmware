/*
 * This file is part of the Trezor project, https://trezor.io/
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

#ifdef KERNEL

#include <trezor_rtl.h>

#include <sys/syscall.h>
#include <sys/syscall_ipc.h>
#include <sys/sysevent_source.h>
#include <sys/systask.h>

typedef struct {
  // Task that requested the syscall
  systask_t* task;
  // Syscall number
  syscall_number_t number;
  // Syscall arguments
  uint32_t args[6];
} syscall_struct_t;

typedef struct {
  // Syscall to process
  syscall_struct_t syscall;

} syscall_ipc_t;

static syscall_ipc_t g_syscall_ipc = {0};

// forward declaration
static const syshandle_vmt_t g_syscall_handle_vmt;

bool syscall_ipc_init(void) {
  syscall_ipc_t* ipc = &g_syscall_ipc;

  memset(ipc, 0, sizeof(*ipc));

  if (!syshandle_register(SYSHANDLE_SYSCALL, &g_syscall_handle_vmt, ipc)) {
    return false;
  }

  return true;
}

void syscall_ipc_enqueue(uint32_t* args, syscall_number_t number) {
  syscall_ipc_t* ipc = &g_syscall_ipc;

  // Enqueue the syscall
  syscall_struct_t* syscall = &ipc->syscall;
  syscall->task = systask_active();
  syscall->number = number;
  memcpy(syscall->args, args, sizeof(syscall->args));

  // Switch to the kernel task to process the syscall
  systask_yield_to(systask_kernel());
}

void syscall_ipc_dequeue(void) {
  syscall_ipc_t* ipc = &g_syscall_ipc;

  syscall_struct_t* syscall = &ipc->syscall;

  if (syscall->task != NULL) {
    // Process enqueued syscall
    syscall_handler(syscall->args, syscall->number, syscall->task->applet);
    // Copy return value back to the task's registers
    systask_set_r0r1(syscall->task, syscall->args[0], syscall->args[1]);

    // Remove the syscall from the queue
    systask_t* task = syscall->task;
    memset(syscall, 0, sizeof(*syscall));

    // Get back to the unprivileged task
    systask_yield_to(task);
  }
}

static void on_task_killed(void* context, systask_id_t task_id) {
  syscall_ipc_t* ipc = (syscall_ipc_t*)context;

  if (ipc->syscall.task != NULL && ipc->syscall.task->id == task_id) {
    memset(&ipc->syscall, 0, sizeof(ipc->syscall));
  }
}

static inline bool syscall_requested(syscall_ipc_t* ipc) {
  return (ipc->syscall.task != NULL);
}

static void on_event_poll(void* context, bool read_awaited,
                          bool write_awaited) {
  syscall_ipc_t* ipc = (syscall_ipc_t*)context;

  UNUSED(write_awaited);

  if (read_awaited && syscall_requested(ipc)) {
    syshandle_signal_read_ready(SYSHANDLE_SYSCALL, NULL);
  }
}

static bool on_check_read_ready(void* context, systask_id_t task_id,
                                void* param) {
  syscall_ipc_t* ipc = (syscall_ipc_t*)context;

  UNUSED(param);

  return (task_id == 0) && syscall_requested(ipc);
}

static const syshandle_vmt_t g_syscall_handle_vmt = {
    .task_created = NULL,
    .task_killed = on_task_killed,
    .check_read_ready = on_check_read_ready,
    .check_write_ready = NULL,
    .poll = on_event_poll,
};

#endif  // KERNEL
