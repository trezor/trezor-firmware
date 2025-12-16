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

#ifdef TREZOR_EMULATOR
#include <pthread.h>
#endif

/** Termination reason for the task */
typedef enum {
  TASK_TERM_REASON_EXIT = 0,
  TASK_TERM_REASON_ERROR,
  TASK_TERM_REASON_FATAL,
  TASK_TERM_REASON_FAULT,

} systask_term_reason_t;

typedef struct {
  /** Fault/exception number (-15..-1) */
  int irqn;
  /** Configurable Fault Status Register (combined UFSR/BFSR/MMFSR) */
  uint32_t cfsr;
  /** Hard Fault Status Register */
  uint32_t hfsr;
  /** Address associated with MemManage fault */
  uint32_t mmfar;
  /** Address associated with the BusFault */
  uint32_t bfar;
#if defined(__ARM_FEATURE_CMSE)
  /** Secure Fault Status Register */
  uint32_t sfsr;
  /** Address associated with the SecureFault */
  uint32_t sfar;
#endif
  /** PC (return address) at the time of the fault */
  uint32_t pc;
  /** Stack pointer at the time of the fault (MSP or PSP depending on the
   * privilege level) */
  uint32_t sp;
#if !(defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__))
  /** Stack pointer limit (for the stack overflow detection) */
  uint32_t sp_lim;
#endif

} system_fault_t;

/** Task post-mortem information */
typedef struct {
  /** Reason for the task termination  */
  systask_term_reason_t reason;
  /** Whether the error occurred in privileged mode */
  bool privileged;

  union {
    /** Argument passed to `systask_exit()` */
    struct {
      int code;
    } exit;

    /** Fault information catched in `systask_exit_fault()` */
    system_fault_t fault;

    /** Arguments passed to `systask_exit_fatal()` */
    struct {
      int32_t line;
      char file[64];
      char expr[64];
    } fatal;

    /** Arguments passed to `systask_exit_error()`  */
    struct {
      char title[64];
      char message[64];
      char footer[64];
    } error;
  };

} systask_postmortem_t;

/**
 * @brief Error handler callback invoked when kernel task terminates.
 *
 * The purpose of this callbacks display RSOD (Red Screen of Death).
 *
 * The callback may be called from any context, including interrupt context.
 *
 * @param pminfo Pointer to post-mortem information.
 */
typedef void (*systask_error_handler_t)(const systask_postmortem_t* pminfo);

/**
 * Maximum number of tasks that can be created
 *
 * 1. kernel
 * 2. coreapp
 * 3. user app
 */
#ifdef USE_APP_LOADING
#define SYSTASK_MAX_TASKS 3
#else
#define SYSTASK_MAX_TASKS 2
#endif

/** Zero-based task ID (up SYSTASK_MAX_TASKS - 1) */
typedef uint8_t systask_id_t;

#ifdef KERNEL_MODE

/** Function call pushed onto the stack of the task */
typedef struct {
  uintptr_t (*fn)(uintptr_t, uintptr_t, uintptr_t);
  uintptr_t arg1;
  uintptr_t arg2;
  uintptr_t arg3;
} systask_fn_call_t;

/**
 * Task context used by the kernel to save the state of each task
 * when switching between them
 */
typedef struct {
  // `sp`, `sp_lim`, `exc_return` and `killed` should at the beginning
  // and in this order to be compatible with the PendSV_Handler
#ifndef TREZOR_EMULATOR
  /** Stack pointer value */
  uint32_t sp;
  /** Stack pointer limit (ARMv8-M only) */
  uint32_t sp_lim;
  /** Exception return value */
  uint32_t exc_return;
#endif
  /** Set to nonzero, if the task is killed */
  volatile uint32_t killed;

  /** Task id */
  systask_id_t id;
  /** Task post-mortem information */
  systask_postmortem_t pminfo;
  /** Applet bound to the task */
  void* applet;

#ifndef TREZOR_EMULATOR
  /** MPU mode the task is running in */
  mpu_mode_t mpu_mode;
  /** Original stack base */
  uint32_t stack_base;
  /** Original stack end */
  uint32_t stack_end;

  /** Static base (SB) address of RW segment used with dynamically linked
   * apps, otherwise set to 0. */
  uint32_t sb_addr;

  /** Address of the global TLS area */
  void* tls_addr;
  /** Number of bytes used in the TLS area */
  size_t tls_size;
  /** TLS copy if the task is inactive */
  uint32_t tls_copy[20];

  /** Set if the task is processing the kernel callback */
  bool in_callback;
#else
  /** System thread handle */
  pthread_t pthread;
  /** Condition variable used to signal the task is ready to run */
  pthread_cond_t cv;

  /** Emulation of the call pushed onto the stack */
  systask_fn_call_t pushed_fn_call;
#endif

} systask_t;

/**
 * @brief Initializes the scheduler for tasks
 *
 * No other task functions should be called before this function
 *
 * @param error_handler Callback invoked when a kernel task terminates with an
 * error.
 */
void systask_scheduler_init(systask_error_handler_t error_handler);

/**
 * @brief Returns the currently running task
 * @return Pointer to the currently running task.
 */
systask_t* systask_active(void);

/**
 * @brief Returns the kernel task
 * @return Pointer to the kernel task.
 */
systask_t* systask_kernel(void);

#ifndef TREZOR_EMULATOR
/**
 * @brief Enables automatics restoring of TLS area
 *
 * When task is deactivated, the tls area is automatically stored in the
 * `task->tls_copy` array and restored when the task is activated again.
 *
 * @param task Pointer to the task.
 * @param tls TLS MPU area.
 */
void systask_enable_tls(systask_t* task, mpu_area_t tls);
#endif

/**
 * @brief Makes the given task the currently running task.
 * @param task Pointer to the task to yield to.
 */
void systask_yield_to(systask_t* task);

/**
 * @brief Initializes a task with the given stack pointer, stack size
 *
 * The task must be not be running when the function is called
 *
 * @param task Pointer to the task to initialize.
 * @param stack_base Stack base address.
 * @param stack_size Stack size in bytes.
 * @param sb_addr Static base address.
 * @param context Context pointer.
 * @return true on success, false otherwise.
 */
bool systask_init(systask_t* task, uint32_t stack_base, uint32_t stack_size,
                  uint32_t sb_addr, void* context);

/**
 * @brief Returns true if the task is alive (not terminated, killed or crashed)
 * @param task Pointer to the task.
 * @return true if the task is alive, false otherwise.
 */
bool systask_is_alive(const systask_t* task);

/**
 * @brief Pushes data onto the stack of the task
 *
 * The task must be not be running when the function is called
 *
 * @param task Pointer to the task.
 * @param data Pointer to data to push.
 * @param size Number of bytes to push.
 * @return Pointer to the location on the stack where data was pushed.
 */
uint32_t* systask_push_data(systask_t* task, const void* data, size_t size);

/**
 * @brief Pops data from the stack of the task
 *
 * The task must be not be running when the function is called
 *
 * @param task Pointer to the task.
 * @param size Number of bytes to pop.
 */
void systask_pop_data(systask_t* task, size_t size);

/**
 * @brief Runs the task with the given entrypoint and arguments
 *
 * The task must be not be running when the function is called
 *
 * @param task Pointer to the task.
 * @param fn Entry function pointer.
 * @param arg1 First argument.
 * @param arg2 Second argument.
 * @param arg3 Third argument.
 * @return true in case of success, false otherwise.
 */
bool systask_push_call(systask_t* task, void* fn, uintptr_t arg1,
                       uintptr_t arg2, uintptr_t arg3);

/**
 * @brief Invokes the callback function in the context of the given task
 *
 * @param task Pointer to the task.
 * @param arg1 First callback argument.
 * @param arg2 Second callback argument.
 * @param arg3 Third callback argument.
 * @param callback Pointer to the callback function.
 * @return Result returned by the callback.
 */
//   uint32_t callback(uint32_t arg1, uint32_t arg2, uint32_t arg3);
uint32_t systask_invoke_callback(systask_t* task, uintptr_t arg1,
                                 uintptr_t arg2, uintptr_t arg3,
                                 void* callback);

#ifndef TREZOR_EMULATOR
/**
 * @brief Sets R0 and R1 registers of the suspended task
 * @param task Pointer to the task.
 * @param r0 Value to set in R0.
 * @param r1 Value to set in R1.
 */
void systask_set_r0r1(systask_t* task, uint32_t r0, uint32_t r1);

/**
 * @brief Gets R0 register value of the suspended task
 * @param task Pointer to the task.
 * @return Value of R0 register.
 */
uint32_t systask_get_r0(systask_t* task);
#endif

/**
 * @brief Gets the ID (zero-based index up SYSTASK_MAX_TASKS - 1) of the given
 * task.
 * @param task Pointer to the task.
 * @return Task ID.
 */
systask_id_t systask_id(const systask_t* task);

/**
 * @brief Terminates the task with the given exit code
 *
 * If the task is not specified (NULL), it's automatically determined:
 *  1) If the function is called in thread mode, the active task will be
 *     terminated.
 *  2) If the function is called in handler mode, the kernel task will be
 *     terminated even if it is not the active task.
 *
 * If the terminated task is unprivileged, the kernel task will be scheduled
 * next.
 *
 * @param task Pointer to the task to terminate, or NULL.
 * @param exit_code Exit code for the task.
 */
void systask_exit(systask_t* task, int exit_code);

/**
 * @brief Terminates the task with an error message
 *
 * (see `systask_exit()` for more details)
 *
 * @param task Pointer to the task.
 * @param title Title string.
 * @param title_len Length of the title.
 * @param message Message string.
 * @param message_len Length of the message.
 * @param footer Footer string.
 * @param footer_len Length of the footer.
 */
void systask_exit_error(systask_t* task, const char* title, size_t title_len,
                        const char* message, size_t message_len,
                        const char* footer, size_t footer_len);

/**
 * @brief Terminates the task with a fatal error message
 *
 * (see `systask_exit()` for more details)
 *
 * @param task Pointer to the task.
 * @param message Message string.
 * @param message_len Length of the message.
 * @param file File string.
 * @param file_len Length of the file string.
 * @param line Line number.
 */
void systask_exit_fatal(systask_t* task, const char* message,
                        size_t message_len, const char* file, size_t file_len,
                        int line);

/**
 * @brief Prints the post-mortem information about the task to the debug output
 * @param task Pointer to the task.
 */
void systask_print_pminfo(systask_t* task);

#endif  // KERNEL_MODE
