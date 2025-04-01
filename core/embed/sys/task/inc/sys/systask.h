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

#pragma once

#include <trezor_types.h>

#include <sys/mpu.h>

// Termination reason for the task
typedef enum {
  TASK_TERM_REASON_EXIT = 0,
  TASK_TERM_REASON_ERROR,
  TASK_TERM_REASON_FATAL,
  TASK_TERM_REASON_FAULT,

} systask_term_reason_t;

typedef struct {
  // Fault/exception number (-15..-1)
  int irqn;
  // Configurable Fault Status Register
  // (combined UFSR/BFSR/MMFSR)
  uint32_t cfsr;
  // Hard Fault Status Register
  uint32_t hfsr;
  // Address associated with MemManage fault
  uint32_t mmfar;
  // Address associated with the BusFault
  uint32_t bfar;
  // Stack pointer at the time of the fault
  // (MSP or PSP depending on the privilege level)
  uint32_t sp;
#if !(defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__))
  // Stack pointer limit (for the stack overflow detection)
  uint32_t sp_lim;
#endif

} system_fault_t;

// Task post-mortem information
typedef struct {
  // Reason for the task termination
  systask_term_reason_t reason;
  // Whether the error occurred in privileged mode
  bool privileged;

  union {
    // Argument passed to `systask_exit()`
    struct {
      int code;
    } exit;

    // Fault information catched in `systask_exit_fault()`
    system_fault_t fault;

    // Arguments passed to `systask_exit_fatal()`
    struct {
      uint32_t line;
      char file[64];
      char expr[64];
    } fatal;

    // Arguments passed to `systask_exit_error()`
    struct {
      char title[64];
      char message[64];
      char footer[64];
    } error;
  };

} systask_postmortem_t;

// Error handler callback invoke when kernel task terminates.
//
// The purpose of this callbacks display RSOD (Red Screen of Death).
//
// The callback may be called from any context, including interrupt context.
typedef void (*systask_error_handler_t)(const systask_postmortem_t* pminfo);

#ifdef KERNEL_MODE

// Maximum number of tasks that can be created
#define SYSTASK_MAX_TASKS 2

// Zero-based task ID (up SYSTASK_MAX_TASKS - 1)
typedef uint8_t systask_id_t;

// Task context used by the kernel to save the state of each task
// when switching between them
typedef struct {
  //  `sp`, `sp_lim`, `exc_return` and `killed` should at the beginning
  //  and in this order to be compatible with the PendSV_Handler
  // Stack pointer value
  uint32_t sp;
  // Stack pointer limit (ARMv8-M only)
  uint32_t sp_lim;
  // Exception return value
  uint32_t exc_return;
  // Set to nonzero, if the task is killed
  volatile uint32_t killed;

  // Task id
  systask_id_t id;
  // MPU mode the task is running in
  mpu_mode_t mpu_mode;
  // Task post-mortem information
  systask_postmortem_t pminfo;
  // Applet bound to the task
  void* applet;

} systask_t;

// Initializes the scheduler for tasks
//
// No other task functions should be called before this function
void systask_scheduler_init(systask_error_handler_t error_handler);

// Returns the currently running task
systask_t* systask_active(void);

// Returns the kernel task
systask_t* systask_kernel(void);

// Makes the given task the currently running task.
void systask_yield_to(systask_t* task);

// Initializes a task with the given stack pointer, stack size
//
// The task must be not be running when the function is called
bool systask_init(systask_t* task, uint32_t stack_ptr, uint32_t stack_size,
                  void* context);

// Returns true if the task is alive (not terminated, killed or crashed)
bool systask_is_alive(const systask_t* task);

// Pushes data onto the stack of the task
//
// The task must be not be running when the function is called
uint32_t* systask_push_data(systask_t* task, const void* data, size_t size);

// Pops data from the stack of the task
//
// The task must be not be running when the function is called
void systask_pop_data(systask_t* task, size_t size);

// Runs the task with the given entrypoint and arguments
//
// The task must be not be running when the function is called
// Return `true` in case of success, `false` otherwise
bool systask_push_call(systask_t* task, void* fn, uint32_t arg1, uint32_t arg2,
                       uint32_t arg3);

// Gets the ID (zero-based index up SYSTASK_MAX_TASKS - 1) of the given task.
systask_id_t systask_id(const systask_t* task);

// Terminates the task with the given exit code
//
// If the task is not specified (NULL), it's automatically determined:
//  1) If the function is called in thread mode, the active task will be
//     terminated.
//  2) If the function is called in handler mode, the kernel task will be
//     terminated even if it is not the active task.
//
// If the terminated task is unprivileged, the kernel task will be scheduled
// next.
void systask_exit(systask_t* task, int exit_code);

// Terminates the task with an error message
//
// (see `systask_exit()` for more details)
void systask_exit_error(systask_t* task, const char* title, size_t title_len,
                        const char* message, size_t message_len,
                        const char* footer, size_t footer_len);

// Terminates the task with a fatal error message
//
// (see `systask_exit()` for more details)
void systask_exit_fatal(systask_t* task, const char* message,
                        size_t message_len, const char* file, size_t file_len,
                        int line);

#endif  // KERNEL_MODE
