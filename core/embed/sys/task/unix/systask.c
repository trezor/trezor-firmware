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

#include <trezor_rtl.h>

#include <sys/bootutils.h>
#include <sys/dbg_console.h>
#include <sys/sysevent_source.h>
#include <sys/systask.h>

#include <pthread.h>

// Task scheduler state
typedef struct {
  // Error handler called when a kernel task terminates
  systask_error_handler_t error_handler;
  // Background kernel task
  systask_t kernel_task;
  // Currently running task
  systask_t* active_task;
  // Task to be scheduled next
  systask_t* waiting_task;
  // Bitmap of used task IDs
  uint32_t task_id_map;
  // Mutex used for synchronizing access to the scheduler state
  pthread_mutex_t lock;

} systask_scheduler_t;

static systask_scheduler_t g_systask_scheduler = {
    // This static initialization is required for exception handling
    // to function correctly before the scheduler is initialized.
    .active_task = &g_systask_scheduler.kernel_task,
    .waiting_task = &g_systask_scheduler.kernel_task,
    .task_id_map = 0x00000001,  // Kernel task is always present
    .kernel_task = {
        .id = 0,  // Kernel task ID == 0
        .cv = PTHREAD_COND_INITIALIZER,
    }};

void systask_scheduler_init(systask_error_handler_t error_handler) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  memset(scheduler, 0, sizeof(systask_scheduler_t));

  scheduler->error_handler = error_handler;
  scheduler->active_task = &scheduler->kernel_task;
  scheduler->waiting_task = scheduler->active_task;
  scheduler->task_id_map = 0x00000001;  // Kernel task is always present
  scheduler->lock = (pthread_mutex_t)PTHREAD_MUTEX_INITIALIZER;
  scheduler->kernel_task.cv = (pthread_cond_t)PTHREAD_COND_INITIALIZER;
}

systask_t* systask_active(void) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  return scheduler->active_task;
}

systask_t* systask_kernel(void) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  return &scheduler->kernel_task;
}

systask_id_t systask_id(const systask_t* task) { return task->id; }

static uint32_t invoke_pushed_fn_call(systask_t* task) {
  systask_fn_call_t call = task->pushed_fn_call;

  // Clear the pushed call before invoking it to allow re-entrancy
  // (before the call returns, the kernel may push another call)
  task->pushed_fn_call = (systask_fn_call_t){0};

  return call.fn(call.arg1, call.arg2, call.arg3);
}

static void systask_yield(void) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  pthread_mutex_lock(&scheduler->lock);

  systask_t* current_task = scheduler->active_task;

  if (scheduler->waiting_task->killed) {
    pthread_mutex_unlock(&scheduler->lock);
    return;
  }

  // Set the predicate *before* signaling to avoid lost wakeups
  scheduler->active_task = scheduler->waiting_task;
  pthread_cond_signal(&scheduler->waiting_task->cv);

  // Park until someone makes us active again (or we’re exiting)
  while (scheduler->active_task != current_task && !current_task->killed) {
    pthread_cond_wait(&current_task->cv, &scheduler->lock);
  }

  pthread_mutex_unlock(&scheduler->lock);

  // Now the task called systask_yield() is active again

  // Do not return to a killed task
  if (current_task->killed) {
    pthread_exit(0);
  }

  // Process the pushed call first, if any
  // (used to throw exceptions into the task)
  if (current_task->pushed_fn_call.fn != NULL) {
    invoke_pushed_fn_call(current_task);
  }
}

void systask_yield_to(systask_t* task) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  pthread_mutex_lock(&scheduler->lock);
  scheduler->waiting_task = task;
  pthread_mutex_unlock(&scheduler->lock);

  systask_yield();
}

static systask_id_t systask_get_unused_id(void) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  pthread_mutex_lock(&scheduler->lock);

  systask_id_t id = 0;
  while (++id < SYSTASK_MAX_TASKS) {
    if ((scheduler->task_id_map & (1 << id)) == 0) {
      scheduler->task_id_map |= (1 << id);
      break;
    }
  }

  pthread_mutex_unlock(&scheduler->lock);

  return id;
}

static void* thread_trampoline(void* arg) {
  systask_t* task = (systask_t*)arg;
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  pthread_mutex_lock(&scheduler->lock);
  while (scheduler->active_task != task) {
    pthread_cond_wait(&task->cv, &scheduler->lock);
  }
  pthread_mutex_unlock(&scheduler->lock);

  invoke_pushed_fn_call(task);

  // Cooperative exit: pick someone else if possible
  pthread_mutex_lock(&scheduler->lock);
  task->killed = true;

  // If we're still active, hand off to the kernel thread
  if (scheduler->active_task == task) {
    scheduler->active_task = &scheduler->kernel_task;
    pthread_cond_signal(&scheduler->kernel_task.cv);
  }

  pthread_mutex_unlock(&scheduler->lock);
  return 0;
}

bool systask_init(systask_t* task, uint32_t stack_base, uint32_t stack_size,
                  uint32_t sb_addr, void* applet) {
  UNUSED(stack_base);
  UNUSED(stack_size);
  UNUSED(sb_addr);

  systask_id_t id = systask_get_unused_id();
  if (id >= SYSTASK_MAX_TASKS) {
    return false;
  }

  memset(task, 0, sizeof(systask_t));
  task->id = id;
  task->applet = applet;
  task->cv = (pthread_cond_t)PTHREAD_COND_INITIALIZER;

  if (pthread_create(&task->pthread, NULL, thread_trampoline, task) != 0) {
    return false;
  }

  // Notify all event sources about the task creation
  sysevents_notify_task_created(task);

  return true;
}

bool systask_push_call(systask_t* task, void* fn, uintptr_t arg1,
                       uintptr_t arg2, uintptr_t arg3) {
  if (task->pushed_fn_call.fn != NULL) {
    return false;
  }

  task->pushed_fn_call.fn = fn;
  task->pushed_fn_call.arg1 = arg1;
  task->pushed_fn_call.arg2 = arg2;
  task->pushed_fn_call.arg3 = arg3;

  return true;
}

static void systask_kill(systask_t* task) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  systask_print_pminfo(task);

  task->killed = 1;

  if (task == &scheduler->kernel_task) {
    // Call panic handler
    if (scheduler->error_handler != NULL) {
      scheduler->error_handler(&task->pminfo);
    }

    // We reach this point only if error_handler is NULL or
    // if it returns. Neither is expected to happen.
    reboot_device();
  } else {
    // Free task ID
    scheduler->task_id_map &= ~(1 << task->id);
    // Notify all event sources about the task termination
    sysevents_notify_task_killed(task);
    // Switch to the kernel task
    systask_yield_to(&scheduler->kernel_task);
  }
}

bool systask_is_alive(const systask_t* task) { return !task->killed; }

void systask_exit(systask_t* task, int exit_code) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  if (task == NULL) {
    task = systask_active();
  }

  systask_postmortem_t* pminfo = &task->pminfo;

  memset(pminfo, 0, sizeof(systask_postmortem_t));
  pminfo->reason = TASK_TERM_REASON_EXIT;
  pminfo->privileged = (task == &scheduler->kernel_task);
  pminfo->exit.code = exit_code;

  systask_kill(task);
}

void systask_exit_error(systask_t* task, const char* title, size_t title_len,
                        const char* message, size_t message_len,
                        const char* footer, size_t footer_len) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  if (task == NULL) {
    task = systask_active();
  }

  systask_postmortem_t* pminfo = &task->pminfo;

  memset(pminfo, 0, sizeof(systask_postmortem_t));
  pminfo->reason = TASK_TERM_REASON_ERROR;
  pminfo->privileged = (task == &scheduler->kernel_task);

  if (title != NULL) {
    size_t len = MIN(title_len, sizeof(pminfo->error.title) - 1);
    strncpy(pminfo->error.title, title, len);
  }

  if (message != NULL) {
    size_t len = MIN(message_len, sizeof(pminfo->error.message) - 1);
    strncpy(pminfo->error.message, message, len);
  }

  if (footer != NULL) {
    size_t len = MIN(footer_len, sizeof(pminfo->error.footer) - 1);
    strncpy(pminfo->error.footer, footer, len);
  }

  systask_kill(task);
}

void systask_exit_fatal(systask_t* task, const char* message,
                        size_t message_len, const char* file, size_t file_len,
                        int line) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  if (task == NULL) {
    task = systask_active();
  }

  systask_postmortem_t* pminfo = &task->pminfo;

  memset(pminfo, 0, sizeof(systask_postmortem_t));
  pminfo->reason = TASK_TERM_REASON_FATAL;
  pminfo->privileged = (task == &scheduler->kernel_task);

  if (message != NULL) {
    size_t len = MIN(message_len, sizeof(pminfo->fatal.expr) - 1);
    strncpy(pminfo->fatal.expr, message, len);
  }

  if (file != NULL) {
    size_t len = MIN(file_len, sizeof(pminfo->fatal.file) - 1);
    strncpy(pminfo->fatal.file, file, len);
  }

  pminfo->fatal.line = line;

  systask_kill(task);
}

void systask_print_pminfo(systask_t* task) {
#ifdef USE_DBG_CONSOLE
  dbg_printf("Task #%u terminated.\n", task->id);
  dbg_printf("  Post-mortem info:\n");

  const systask_postmortem_t* pminfo = &task->pminfo;

  switch (pminfo->reason) {
    case TASK_TERM_REASON_EXIT:
      dbg_printf("    EXIT: %d\n", pminfo->exit.code);
      break;

    case TASK_TERM_REASON_ERROR:
      dbg_printf("    ERROR: %s\n", pminfo->error.message);
      if (pminfo->error.title[0] != '\0') {
        dbg_printf("      Title: %s\n", pminfo->error.title);
      }
      if (pminfo->error.footer[0] != '\0') {
        dbg_printf("      Footer: %s\n", pminfo->error.footer);
      }
      break;

    case TASK_TERM_REASON_FATAL:
      dbg_printf("    FATAL: %s\n", pminfo->fatal.expr);
      if (pminfo->fatal.file[0] != '\0') {
        dbg_printf("      at %s:%u\n", pminfo->fatal.file,
                   (unsigned int)pminfo->fatal.line);
      }
      break;

    case TASK_TERM_REASON_FAULT:
      dbg_printf("    FAULT\n");
      break;
  }
#endif  // USE_DBG_CONSOLE
}
