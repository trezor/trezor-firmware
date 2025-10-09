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

#include <sys/sysevent_source.h>
#include <sys/systask.h>

#include <pthread.h>

// Task scheduler state
typedef struct {
  // Error handler called when a kernel task terminates
  systask_error_handler_t error_handler;
  // Error handler called when a kernel task terminates
  // !@# systask_error_handler_t error_handler;
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

static void systask_yield(void) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  pthread_mutex_lock(&scheduler->lock);

  if (scheduler->waiting_task->killed) {
    pthread_mutex_unlock(&scheduler->lock);
    return;
  }

  // Set the predicate *before* signaling to avoid lost wakeups
  scheduler->active_task = scheduler->waiting_task;
  pthread_cond_signal(&scheduler->waiting_task->cv);

  // Park until someone makes us active again (or we’re exiting)
  while (scheduler->active_task != scheduler->waiting_task &&
         !scheduler->waiting_task->killed) {
    pthread_cond_wait(&scheduler->waiting_task->cv, &scheduler->lock);
  }

  pthread_mutex_unlock(&scheduler->lock);
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

  if (task->entrypoint.fn != NULL) {
    task->entrypoint.fn(task->entrypoint.arg1, task->entrypoint.arg2,
                        task->entrypoint.arg3);
  } else {
    // !@# error: no function to call
  }

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
  task->entrypoint.fn = fn;
  task->entrypoint.arg1 = arg1;
  task->entrypoint.arg2 = arg2;
  task->entrypoint.arg3 = arg3;

  return true;
}

bool systask_is_alive(const systask_t* task) { return !task->killed; }
