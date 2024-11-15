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

#include <trezor_bsp.h>
#include <trezor_rtl.h>

#include <sys/bootutils.h>
#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/syscall.h>
#include <sys/systask.h>
#include <sys/system.h>

#ifdef KERNEL_MODE

// Disable stack protector for this file since it  may interfere
// with the stack manipulation and fault handling
#pragma GCC optimize("no-stack-protector")

#define STK_FRAME_R0 0
#define STK_FRAME_R1 1
#define STK_FRAME_R2 2
#define STK_FRAME_R3 3
#define STK_FRAME_R12 4
#define STK_FRAME_LR 5
#define STK_FRAME_RET_ADDR 6
#define STK_FRAME_XPSR 7

// Task manager state
typedef struct {
  // Error handler called when a kernel task terminates
  systask_error_handler_t error_handler;
  // Background kernel task
  systask_t kernel_task;
  // Currently running task
  systask_t* active_task;
  // Task to be scheduled next
  systask_t* waiting_task;
} systask_scheduler_t;

// Kernel stack base pointer defined in linker script
extern uint8_t _sstack;
extern uint8_t _estack;

// Global task manager state
static systask_scheduler_t g_systask_scheduler = {
    // This static initialization is required for exception handling
    // to function correctly before the scheduler is initialized.
    .active_task = &g_systask_scheduler.kernel_task,
    .waiting_task = &g_systask_scheduler.kernel_task,
    .kernel_task = {
        .sp_lim = (uint32_t)&_sstack,
    }};

void systask_scheduler_init(systask_error_handler_t error_handler) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  memset(scheduler, 0, sizeof(systask_scheduler_t));

  scheduler->error_handler = error_handler;
  scheduler->active_task = &scheduler->kernel_task;
  scheduler->waiting_task = scheduler->active_task;

  scheduler->kernel_task.sp_lim = (uint32_t)&_sstack;

  // SVCall priority should be the lowest since it is
  // generally a blocking operation
  NVIC_SetPriority(SVCall_IRQn, IRQ_PRI_LOWEST);
  NVIC_SetPriority(PendSV_IRQn, IRQ_PRI_LOWEST);

  // Enable BusFault and UsageFault handlers
  SCB->SHCSR |= (SCB_SHCSR_USGFAULTENA_Msk | SCB_SHCSR_BUSFAULTENA_Msk);
}

systask_t* systask_active(void) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  return scheduler->active_task;
}

static void systask_yield(void) {
  bool handler_mode = (__get_IPSR() & IPSR_ISR_Msk) != 0;

  if (handler_mode) {
    SCB->ICSR |= SCB_ICSR_PENDSVSET_Msk;
    __DSB();
  } else {
    // SVC_SYSTASK_YIELD is the only SVC that is allowed to be invoked from
    // kernel itself, and it is used to start the unprivileged application code.
    __asm__ volatile("svc %[svid]\n"
                     :  // no output
                     : [svid] "i"(SVC_SYSTASK_YIELD)
                     : "memory");
  }
}

void systask_yield_to(systask_t* task) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  irq_key_t irq_key = irq_lock();
  scheduler->waiting_task = task;
  irq_unlock(irq_key);

  systask_yield();
}

void systask_init(systask_t* task, uint32_t stack_ptr, uint32_t stack_size,
                  void* applet) {
  memset(task, 0, sizeof(systask_t));
  task->sp = stack_ptr + stack_size;
  task->sp_lim = stack_ptr + 256;
  task->exc_return = 0xFFFFFFED;  // Thread mode, use PSP, pop FP context
  task->mpu_mode = MPU_MODE_APP;
  task->applet = applet;
}

uint32_t* systask_push_data(systask_t* task, const void* data, size_t size) {
  if (task->sp < task->sp_lim) {
    // Stack overflow
    return NULL;
  }

  uint32_t stack_remaining = task->sp - task->sp_lim;

  if (stack_remaining < size) {
    // Not enough space on the stack
    return NULL;
  }

  task->sp -= size;

  if (data != NULL) {
    memcpy((void*)task->sp, data, size);
  } else {
    memset((void*)task->sp, 0, size);
  }

  return (void*)task->sp;
}

void systask_pop_data(systask_t* task, size_t size) { task->sp += size; }

bool systask_push_call(systask_t* task, void* entrypoint, uint32_t arg1,
                       uint32_t arg2, uint32_t arg3) {
  uint32_t original_sp = task->sp;

  // Align stack pointer to 8 bytes
  task->sp &= ~7;

  // FP extension context
  if (systask_push_data(task, NULL, 0x48) == NULL) {
    goto cleanup;
  }

  // Standard exception frame
  uint32_t* stk_frame = systask_push_data(task, NULL, 0x20);
  if (stk_frame == NULL) {
    goto cleanup;
  }

  // Registers r4-r11
  if (systask_push_data(task, NULL, 0x20) == NULL) {
    goto cleanup;
  }
  // Registers s16-s31
  if (systask_push_data(task, NULL, 0x40) == NULL) {
    goto cleanup;
  }

  // Return to thread mode, use PSP, pop FP context
  task->exc_return = 0xFFFFFFED;

  stk_frame[STK_FRAME_R0] = arg1;
  stk_frame[STK_FRAME_R1] = arg2;
  stk_frame[STK_FRAME_R2] = arg3;
  stk_frame[STK_FRAME_RET_ADDR] = (uint32_t)entrypoint & ~1;
  stk_frame[STK_FRAME_XPSR] = 0x01000000;  // T (Thumb state) bit set

  return true;

cleanup:
  task->sp = original_sp;
  return false;
}

static void systask_kill(systask_t* task) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  task->killed = 1;

  if (task == &scheduler->kernel_task) {
    // Call panic handler
    if (scheduler->error_handler != NULL) {
      scheduler->error_handler(&task->pminfo);
    }
    secure_shutdown();
  } else if (task == scheduler->active_task) {
    // Switch to the kernel task
    systask_yield_to(&scheduler->kernel_task);
  }
}

void systask_exit(systask_t* task, int exit_code) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  if (task == NULL) {
    bool handler_mode = (__get_IPSR() & IPSR_ISR_Msk) != 0;
    task = handler_mode ? &scheduler->kernel_task : scheduler->active_task;
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
    bool handler_mode = (__get_IPSR() & IPSR_ISR_Msk) != 0;
    task = handler_mode ? &scheduler->kernel_task : scheduler->active_task;
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
    bool handler_mode = (__get_IPSR() & IPSR_ISR_Msk) != 0;
    task = handler_mode ? &scheduler->kernel_task : scheduler->active_task;
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

// Terminate active task from fault/exception handler
__attribute((used)) static void systask_exit_fault(bool privileged,
                                                   uint32_t sp) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  systask_scheduler_t* scheduler = &g_systask_scheduler;

  systask_t* task =
      privileged ? &scheduler->kernel_task : scheduler->active_task;

  systask_postmortem_t* pminfo = &task->pminfo;

  // Do not overwrite the reason if it is already set to fault
  // (exception handlers may call this function multiple times, and
  //  we want to preserve the first reason)
  if (pminfo->reason != TASK_TERM_REASON_FAULT) {
    pminfo->reason = TASK_TERM_REASON_FAULT;
    pminfo->privileged = privileged;
    pminfo->fault.sp = sp;
#if !(defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__))
    pminfo->fault.sp_lim = task->sp_lim;
#endif
    pminfo->fault.irqn = (__get_IPSR() & IPSR_ISR_Msk) - 16;
    pminfo->fault.cfsr = SCB->CFSR;
    pminfo->fault.mmfar = SCB->MMFAR;
    pminfo->fault.bfar = SCB->BFAR;
    pminfo->fault.hfsr = SCB->HFSR;
  }

  systask_kill(task);

  mpu_restore(mpu_mode);
}

// C part of PendSV handler that switches tasks
//
// `sp` is the stack pointer of the current task
// `sp_lim` is the stack pointer limit of the current task
// `exc_return` is the execution state of the current task
//
// Returns the context struct of the next task
__attribute((no_stack_protector, used)) static uint32_t scheduler_pendsv(
    uint32_t sp, uint32_t sp_lim, uint32_t exc_return) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  IRQ_LOG_ENTER();

  // Save the current task context
  systask_t* prev_task = scheduler->active_task;
  prev_task->sp = sp;
#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__)
  // sp_lim is not valid on ARMv7-M
  prev_task->sp_lim = sp_lim;
#endif
  prev_task->exc_return = exc_return;
  prev_task->mpu_mode = mpu_get_mode();

  // Switch to the next task
  scheduler->active_task = scheduler->waiting_task;

  // Load the scheduled task context
  systask_t* next_task = scheduler->active_task;

  // Set task privilege level
  uint32_t control = __get_CONTROL();
  if (next_task == &scheduler->kernel_task) {
    control &= ~CONTROL_nPRIV_Msk;
  } else {
    control |= CONTROL_nPRIV_Msk;
  }
  __set_CONTROL(control);

  // Setup the MPU for the new task
  mpu_reconfig(next_task->mpu_mode);

  IRQ_LOG_EXIT();

  return (uint32_t)next_task;
}

__attribute__((naked, no_stack_protector)) void PendSV_Handler(void) {
  __asm__ volatile(
      "LDR     R0, =%[active_task] \n"
      "LDR     R1, =%[waiting_task]\n"
      "CMP     R0, R1              \n"
      "BEQ     3f                  \n"  // No task switch needed

      "LDR     R0, [R0]            \n"  // R0 =  active_task
      "LDR     R0, [R0, #12]       \n"  // R0 =  active_task->killed
      "CMP     R0, #0              \n"
      "BEQ     1f                  \n"  // =0 => normal processing

      // We are switching from a killed task to the kernel task.
      // Since the reason might be a stack overflow, we must not
      // attempt to save the task context.

      "LDR     R1, = 0xE000EF34    \n"  // FPU->FPCCR
      "LDR     R0, [R1]            \n"
      "BIC     R0, R0, #1          \n"  // Clear LSPACT to suppress later lazy
      "STR     R0, [R1]            \n"  // stacking to the killed task stack

      "MOV     R0, #0              \n"  // Skip context save
      "MOV     R1, R0              \n"  //
      "MOV     R2, R0              \n"  //
      "B       2f                  \n"  //

      "1:                          \n"

      // Save the current task context on its stack before switching

      "TST      LR, #0x4           \n"  // Return stack (1=>PSP, 0=>MSP)

#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__)
      "ITTEE    EQ                 \n"
      "MRSEQ    R0, MSP            \n"  // Get current SP
      "MRSEQ    R1, MSPLIM         \n"  // Get current SP Limit
      "MRSNE    R0, PSP            \n"
      "MRSNE    R1, PSPLIM         \n"
#else
      "ITE      EQ                 \n"
      "MRSEQ    R0, MSP            \n"  // Get current SP
      "MRSNE    R0, PSP            \n"
      "MOV      R1, #0             \n"  // (fake SPLIM)
#endif
      "IT       EQ                 \n"  // If using main stack:
      "SUBEQ    SP, SP, #0x60      \n"  // reserve space for R4-11 and S16-S31

      "MOV      R2, LR             \n"  // Get current EXC_RETURN

      "STMDB    R0!, {R4-R11}      \n"  // Save R4-R11 to SP Frame Stack
      "TST      LR, #0x10          \n"  // Check EXC_RETURN.Ftype bit to see if
                                        // the current thread has a FP context
      "IT       EQ                 \n"
      "VSTMDBEQ R0!, {S16-S31}     \n"  // If so, save S16-S31 FP addition
                                        // context, that will also trigger lazy
                                        // fp context preservation of S0-S15
      "2:                          \n"

      "BL       scheduler_pendsv   \n"  // Save SP value of current task
      "LDR      LR, [R0, #8]       \n"  // Get the EXC_RETURN value
      "LDR      R1, [R0, #4]       \n"  // Get the SP_LIM value
      "LDR      R0, [R0, #0]       \n"  // Get the SP value

      "TST      LR, #0x10          \n"  // Check EXC_RETURN.Ftype bit to see if
                                        // the next thread has a FP context
      "IT       EQ                 \n"
      "VLDMIAEQ R0!, {S16-S31}     \n"  // If so, restore S16-S31
      "LDMIA    R0!, {R4-R11}      \n"  // Restore R4-R11

      "TST      LR, #0x4           \n"  // Return stack (1=>PSP, 0=>MSP)
#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__)
      "ITEE     EQ                 \n"
      "MSREQ    MSP, R0            \n"  // Update MSP
      "MSRNE    PSPLIM, R1         \n"  // Update PSPLIM & PSP
      "MSRNE    PSP, R0            \n"
#else
      "ITE      EQ                 \n"
      "MSREQ    MSP, R0            \n"  // Update the MSP
      "MSRNE    PSP, R0            \n"  // Update the PSP
#endif
      "3:                          "
      "BX       LR                 \n"
      :                                                        // No output
      : [active_task] "i"(&g_systask_scheduler.active_task),   // Input
        [waiting_task] "i"(&g_systask_scheduler.waiting_task)  // Input
      :                                                        // Clobber
  );
}

__attribute__((no_stack_protector, used)) static uint32_t svc_handler(
    uint32_t* stack, uint32_t* msp, uint32_t exc_return, uint32_t r4,
    uint32_t r5, uint32_t r6) {
  IRQ_LOG_ENTER();

  uint8_t svc_number = ((uint8_t*)stack[6])[-2];

#ifdef SYSCALL_DISPATCH
  uint32_t args[6] = {stack[0], stack[1], stack[2], stack[3], r4, r5};
#endif

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  switch (svc_number) {
    case SVC_SYSTASK_YIELD:
      // Yield to the waiting task
      systask_yield();
      break;
#ifdef SYSCALL_DISPATCH
    case SVC_SYSCALL:
      syscall_handler(args, r6);
      stack[0] = args[0];
      stack[1] = args[1];
      break;
    case SVC_CALLBACK_RETURN:
      // g_return_value = args[0]
      // exc_return = return_from_callback;
      mpu_restore(mpu_mode);
      return_from_app_callback(args[0], msp);
      break;
#endif
    default:
      break;
  }

  mpu_restore(mpu_mode);

  IRQ_LOG_EXIT();

  return exc_return;
}

__attribute((naked, no_stack_protector)) void SVC_Handler(void) {
  __asm__ volatile(
      "TST      LR, #0x4            \n"  // Return stack (1=>PSP, 0=>MSP)
      "ITE      EQ                  \n"
      "MRSEQ    R0, MSP             \n"  // `stack` argument
      "MRSNE    R0, PSP             \n"
      "TST      LR, #0x20           \n"
      "IT       EQ                  \n"
      "ADDEQ    R0, R0, #0x40       \n"
      "MRS      R1, MSP             \n"  // `msp` argument
      "MOV      R2, LR              \n"  // `exc_return` argument
      "MOV      R3, R4              \n"  // 'r4' argument
      "PUSH     {R5, R6}            \n"  // 'r5' and 'r6' arguments on stack
      "BL       svc_handler         \n"
      "POP      {R5, R6}            \n"
      "BX       R0                  \n"  // Branch to the returned value
  );
}

__attribute__((naked, no_stack_protector)) void HardFault_Handler(void) {
  // A HardFault may also be caused by exception escalation.
  // To ensure we have enough space to handle the exception,
  // we set the stack pointer to the end of the stack.

  __asm__ volatile(
      "MRS      R1, MSP               \n"  // R1 = MSP
      "LDR      R0, =%[estack]        \n"  // Reset main stack
      "MSR      MSP, R0               \n"  //
      "MOV      R0, #1                \n"  // R0 = 1 (Privileged)
      "B        systask_exit_fault    \n"  // Exit task with fault
      :
      : [estack] "i"(&_estack)
      : "memory");
}

__attribute__((naked, no_stack_protector)) void MemManage_Handler(void) {
  __asm__ volatile(
      "TST      LR, #0x4              \n"  // Return stack (1=>PSP, 0=>MSP)
      "ITTEE    EQ                    \n"
      "MOVEQ    R0, #1                \n"  // R0 = 1 (Privileged)
      "MRSEQ    R1, MSP               \n"  // R1 = MSP
      "MOVNE    R0, #0                \n"  // R0 = 0 (Unprivileged)
      "MRSNE    R1, PSP               \n"  // R1 = PSP
#if !(defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__))
      "CMP      R0, #0                \n"
      "BEQ      1f                    \n"  // Skip stack ptr checking for PSP
      "LDR      R2, =%[sstack]        \n"
      "CMP      R1, R2                \n"  // Check if PSP is below the stack
      "ITT      LO                    \n"  // base
      "LDRLO    R2, =%[estack]        \n"
      "MSRLO    MSP, R2               \n"  // Reset MSP
      "1:                             \n"
#endif
      "B        systask_exit_fault    \n"  // Exit task with fault
      :
      : [estack] "i"(&_estack), [sstack] "i"((uint32_t)&_sstack + 256)
      : "memory");
}

__attribute__((naked, no_stack_protector)) void BusFault_Handler(void) {
  __asm__ volatile(
      "TST      LR, #0x4              \n"  // Return stack (1=>PSP, 0=>MSP)
      "ITTEE    EQ                    \n"
      "MOVEQ    R0, #1                \n"  // R0 = 1 (Privileged)
      "MRSEQ    R1, MSP               \n"  // R1 = MSP
      "MOVNE    R0, #0                \n"  // R0 = 0 (Unprivileged)
      "MRSNE    R1, PSP               \n"  // R1 = PSP
      "B        systask_exit_fault    \n"  // Exit task with fault
  );
}

__attribute__((naked, no_stack_protector)) void UsageFault_Handler(void) {
  __asm__ volatile(
      "TST      LR, #0x4              \n"  // Return stack (1=>PSP, 0=>MSP)
      "ITTT     NE                    \n"
      "MOVNE    R0, #0                \n"  // R0 = 0 (Unprivileged)
      "MRSNE    R1, PSP               \n"  // R1 = PSP
      "BNE      systask_exit_fault    \n"  // Exit task with fault
#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__)
      "MRS      R1, MSP               \n"  // R1 = MSP
      "LDR      R0, =0xE000ED28       \n"  // SCB->CFSR
      "LDR      R0, [R0]              \n"
      "TST      R0, #0x100000         \n"  // STKOF bit set?
      "ITT      NE                    \n"
      "LDRNE    R0, =%[estack]        \n"  // Reset main stack in case of stack
      "MSRNE    MSP, R0               \n"  // overflow
#endif
      "MOV      R0, #1                \n"  // R0 = 1 (Privileged)
      "B        systask_exit_fault    \n"  // Exit task with fault
      :
      : [estack] "i"(&_estack)
      : "memory");
}

#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__)
__attribute__((naked, no_stack_protector)) void SecureFault_Handler(void) {
  __asm__ volatile(
      "TST      LR, #0x4              \n"  // Return stack (1=>PSP, 0=>MSP)
      "ITTEE    EQ                    \n"
      "MOVEQ    R0, #1                \n"  // R0 = 1 (Privileged)
      "MRSEQ    R1, MSP               \n"  // R1 = MSP
      "MOVNE    R0, #0                \n"  // R0 = 0 (Unprivileged)
      "MRSNE    R1, PSP               \n"  // R1 = PSP
      "B        systask_exit_fault    \n"  // Exit task with fault
  );
}
#endif

#ifdef STM32U5
void GTZC_IRQHandler(void) { systask_exit_fault(true, __get_MSP()); }
#endif

void NMI_Handler(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
#ifdef STM32U5
  if ((RCC->CIFR & RCC_CIFR_CSSF) != 0) {
#else
  if ((RCC->CIR & RCC_CIR_CSSF) != 0) {
#endif
    // Clock Security System triggered NMI
    systask_exit_fault(true, __get_MSP());
  }
  mpu_restore(mpu_mode);
}

#endif  // KERNEL_MODE
