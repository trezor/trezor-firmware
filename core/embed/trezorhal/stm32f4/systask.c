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

#include STM32_HAL_H

#include <stdbool.h>
#include <string.h>

#include "bootutils.h"
#include "irq.h"
#include "mpu.h"
#include "syscall.h"
#include "systask.h"
#include "system.h"

#ifdef KERNEL_MODE

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

// Global task manager state
systask_scheduler_t g_systask_scheduler = {0};

void systask_scheduler_init(systask_error_handler_t error_handler) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  memset(scheduler, 0, sizeof(systask_scheduler_t));

  scheduler->error_handler = error_handler;
  scheduler->active_task = &scheduler->kernel_task;
  scheduler->waiting_task = scheduler->active_task;

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

void systask_yield_to(systask_t* task) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  bool handler_mode = (__get_IPSR() & IPSR_ISR_Msk) != 0;

  if (handler_mode) {
    scheduler->waiting_task = task;
    SCB->ICSR |= SCB_ICSR_PENDSVSET_Msk;
    __DSB();
  } else {
    register uint32_t r0 __asm__("r0") = (uint32_t)task;

    // SVC_SYSTASK_YIELD is the only SVC that is allowed to be invoked from
    // kernel itself, and it is used to start the unprivileged application code.
    __asm__ volatile("svc %[svid]\n"
                     : "=r"(r0)
                     : [svid] "i"(SVC_SYSTASK_YIELD), "r"(r0)
                     : "memory");
  }
}

void systask_init(systask_t* task, uint32_t stack_ptr, uint32_t stack_size) {
  task->sp = stack_ptr + stack_size;
  task->sp_lim = stack_ptr + 256;
  task->exc_return = 0xFFFFFFED;  // Thread mode, use PSP, pop FP context
  task->mpu_mode = MPU_MODE_APP;
}

uint32_t* systask_push_data(systask_t* task, const void* data, size_t size) {
  uint32_t stack_remaining = task->sp - task->sp_lim;
  if (stack_remaining < size) {
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

void systask_push_call(systask_t* task, void* entrypoint, uint32_t arg1,
                       uint32_t arg2, uint32_t arg3) {
  // FP extension context
  systask_push_data(task, NULL, 0x48);
  // Standard exception frame
  uint32_t* stk_frame = systask_push_data(task, NULL, 0x20);
  // Registers r4-r11
  systask_push_data(task, NULL, 0x20);
  // Registers s16-s31
  systask_push_data(task, NULL, 0x40);

  // Return to thread mode, use PSP, pop FP context
  task->exc_return = 0xFFFFFFED;

  stk_frame[STK_FRAME_R0] = arg1;
  stk_frame[STK_FRAME_R1] = arg2;
  stk_frame[STK_FRAME_R2] = arg3;
  stk_frame[STK_FRAME_RET_ADDR] = (uint32_t)entrypoint & ~1;
  stk_frame[STK_FRAME_XPSR] = 0x01000000;  // T (Thumb state) bit set
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

  // Save the current task context
  systask_t* prev_task = scheduler->active_task;
  prev_task->sp = sp;
  prev_task->sp_lim = sp_lim;
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

  return (uint32_t)next_task;
}

static void systask_kill(systask_t* task) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;

  if (task == &scheduler->kernel_task) {
    if (scheduler->error_handler != NULL) {
      scheduler->error_handler(&task->pminfo);
    }
    secure_shutdown();
  } else if (task == scheduler->active_task) {
    systask_yield_to(&scheduler->kernel_task);
  } else {
    // Inactive task
    // !@# what to do?? mark it somehow??
  }
}

void systask_exit(systask_t* task, int exit_code) {
  systask_postmortem_t* pminfo = &task->pminfo;

  pminfo->reason = TASK_TERM_REASON_EXIT;
  pminfo->exit.code = exit_code;

  systask_kill(task);
}

void systask_exit_error(systask_t* task, const char* title, const char* message,
                        const char* footer) {
  systask_postmortem_t* pminfo = &task->pminfo;

  pminfo->reason = TASK_TERM_REASON_ERROR;

  strncpy(pminfo->error.title, title, sizeof(pminfo->error.title) - 1);
  pminfo->error.title[sizeof(pminfo->error.title) - 1] = '\0';

  strncpy(pminfo->error.message, message, sizeof(pminfo->error.message) - 1);
  pminfo->error.message[sizeof(pminfo->error.message) - 1] = '\0';

  strncpy(pminfo->error.footer, footer, sizeof(pminfo->error.footer) - 1);
  pminfo->error.footer[sizeof(pminfo->error.footer) - 1] = '\0';

  systask_kill(task);
}

void systask_exit_fatal(systask_t* task, const char* message, const char* file,
                        int line) {
  systask_postmortem_t* pminfo = &task->pminfo;

  pminfo->reason = TASK_TERM_REASON_FATAL;

  strncpy(pminfo->fatal.file, file, sizeof(pminfo->fatal.file) - 1);
  pminfo->fatal.file[sizeof(pminfo->fatal.file) - 1] = '\0';

  strncpy(pminfo->fatal.expr, message, sizeof(pminfo->fatal.expr) - 1);
  pminfo->fatal.expr[sizeof(pminfo->fatal.expr) - 1] = '\0';

  pminfo->fatal.line = line;

  systask_kill(task);
}

// Terminate active task from fault/exception handler
static void systask_exit_fault(void) {
  systask_scheduler_t* scheduler = &g_systask_scheduler;
  systask_t* task = scheduler->active_task;
  systask_postmortem_t* pminfo = &task->pminfo;

  pminfo->reason = TASK_TERM_REASON_FAULT;
  pminfo->fault.irqn = (__get_IPSR() & IPSR_ISR_Msk) - 16;
  pminfo->fault.cfsr = SCB->CFSR;
  pminfo->fault.mmfar = SCB->MMFAR;
  pminfo->fault.bfar = SCB->BFAR;
  pminfo->fault.hfsr = SCB->HFSR;

  systask_kill(task);
}

__attribute__((naked, no_stack_protector)) void PendSV_Handler(void) {
  __asm__ volatile(
      "TST      LR,     #0x4       \n"  // Return stack (1=>PSP, 0=>MSP)

#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__)
      "ITTEE    EQ                 \n"
      "MRSEQ    R0,     MSP        \n"  // Get current SP
      "MRSEQ    R1,     MSPLIM     \n"  // Get current SP Limit
      "MRSNE    R0,     PSP        \n"
      "MRSNE    R1,     PSPLIM     \n"
#else
      "ITE      EQ                 \n"
      "MRSEQ    R0,     MSP        \n"  // Get current SP
      "MRSNE    R0,     PSP        \n"
      "MOV      R1,     #0         \n"  // (fake SPLIM)
#endif

      "MOV      R2,     LR         \n"  // Get current EXC_RETURN

      "STMDB    R0!,    {R4-R11}   \n"  // Save R4-R11 to SP Frame Stack
      "TST      LR,     #0x10      \n"  // Check EXC_RETURN.Ftype bit to see if
                                        // the current thread has a FP context
      "IT       EQ                 \n"
      "VSTMDBEQ R0!,    {S16-S31}  \n"  // If so, save S16-S31 FP addition
                                        // context, that will also trigger lazy
                                        // fp context preservation of S0-S15

      "BL       scheduler_pendsv   \n"  // Save SP value of current task
      "LDR      LR,     [R0, #8]   \n"  // Get the EXC_RETURN value
      "LDR      R1,     [R0, #4]   \n"  // Get the SP_LIM value
      "LDR      R0,     [R0, #0]   \n"  // Get the SP value

      "TST      LR,     #0x10      \n"  // Check EXC_RETURN.Ftype bit to see if
                                        // the next thread has a FP context
      "IT       EQ                 \n"
      "VLDMIAEQ R0!,    {S16-S31}  \n"  // If so, restore S16-S31
      "LDMIA    R0!,    {R4-R11}   \n"  // Restore R4-R11

      "TST      LR,     #0x4       \n"  // Check EXC_RETURN to determine which
                                        // SP the next thread is using
#if defined(__ARM_ARCH_8M_MAIN__) || defined(__ARM_ARCH_8M_BASE__)
      "ITT      NE                 \n"
      "MSRNE    PSPLIM, R1         \n"  // Update the SP Limit and SP since MSP
                                        // won't be changed
      "MSRNE    PSP,    R0         \n"
#else
      "IT       NE                 \n"
      "MSRNE    PSP,    R0         \n"  // Update the SP Limit and SP since MSP
                                        // won't be changed
#endif
      "BX       LR                 \n");
}

__attribute__((no_stack_protector, used)) static uint32_t svc_handler(
    uint32_t* stack, uint32_t* msp, uint32_t exc_return, uint32_t r4,
    uint32_t r5, uint32_t r6) {
  uint8_t svc_number = ((uint8_t*)stack[6])[-2];
  uint32_t args[6] = {stack[0], stack[1], stack[2], stack[3], r4, r5};

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  switch (svc_number) {
#ifdef SYSTEM_VIEW
    case SVC_GET_DWT_CYCCNT:
      cyccnt_cycles = *DWT_CYCCNT_ADDR;
      break;
#endif
    case SVC_SYSTASK_YIELD:
      systask_yield_to((systask_t*)args[0]);
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
  return exc_return;
}

__attribute((naked, no_stack_protector)) void SVC_Handler(void) {
  __asm__ volatile(
      "TST     LR, #0x4            \n"  // Called from Process stack pointer?
      "ITE     EQ                  \n"
      "MRSEQ   R0, MSP             \n"
      "MRSNE   R0, PSP             \n"
      "TST     LR, #0x20           \n"
      "IT      EQ                  \n"
      "ADDEQ   R0, R0, #0x40       \n"
      "MRS     R1, MSP             \n"
      "MOV     R2, LR              \n"
      "MOV     R3, R4              \n"
      "PUSH    {R5, R6}            \n"
      "BL      svc_handler         \n"
      "POP     {R5, R6}            \n"
      "BX      R0                  \n"  // Branch to the returned value
  );
}

void HardFault_Handler(void) {
  // A HardFault may also be caused by exception escalation.
  // To ensure we have enough space to handle the exception,
  // we set the stack pointer to the end of the stack.
  extern uint8_t _estack;  // linker script symbol
  // Fix stack pointer
  __set_MSP((uint32_t)&_estack);

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  systask_exit_fault();
  mpu_restore(mpu_mode);
}

/*
  .global MemManage_Handler
  .type MemManage_Handler, STT_FUNC
MemManage_Handler:
  ldr r2, =_sstack
  mrs r1, msp
  ldr r0, =_estack
  msr msp, r0
  cmp r1, r2
  IT lt
  bllt MemManage_Handler_SO
  bl MemManage_Handler_MM
*/

void MemManage_Handler(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  systask_exit_fault();
  mpu_restore(mpu_mode);
}

void BusFault_Handler(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  systask_exit_fault();
  mpu_restore(mpu_mode);
}

void UsageFault_Handler(void) {
#ifdef STM32U5
  if (SCB->CFSR & SCB_CFSR_STKOF_Msk) {
    // Stack overflow
    extern uint8_t _estack;  // linker script symbol
    // Fix stack pointer
    __set_MSP((uint32_t)&_estack);
  }
#endif

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  systask_exit_fault();
  mpu_restore(mpu_mode);
}

#ifdef STM32U5
void SecureFault_Handler(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  systask_exit_fault();
  mpu_restore(mpu_mode);
}
#endif

#ifdef STM32U5
void GTZC_IRQHandler(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
  systask_exit_fault();
  mpu_restore(mpu_mode);
}
#endif

void NMI_Handler(void) {
  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);
#ifdef STM32U5
  if ((RCC->CIFR & RCC_CIFR_CSSF) != 0) {
#else
  if ((RCC->CIR & RCC_CIR_CSSF) != 0) {
#endif
    // Clock Security System triggered NMI
    systask_exit_fault();
  }
  mpu_restore(mpu_mode);
}

// from util.s
extern void shutdown_privileged(void);

void PVD_PVM_IRQHandler(void) {
  mpu_reconfig(MPU_MODE_DEFAULT);
#ifdef BACKLIGHT_PWM_TIM
  // Turn off display backlight
  BACKLIGHT_PWM_TIM->BACKLIGHT_PWM_TIM_CCR = 0;
#endif
  shutdown_privileged();
}

#endif  // KERNEL_MODE
