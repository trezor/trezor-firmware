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

#ifndef TREZORHAL_IRQ_H
#define TREZORHAL_IRQ_H

#include <trezor_bsp.h>
#include <trezor_types.h>

#ifdef SYSTEM_VIEW
#include <sys/systemview.h>
#endif

#ifdef SYSTEM_VIEW
#define IRQ_LOG_ENTER() SEGGER_SYSVIEW_RecordEnterISR();
#define IRQ_LOG_EXIT() SEGGER_SYSVIEW_RecordExitISR();
#else
#define IRQ_LOG_ENTER()
#define IRQ_LOG_EXIT()
#endif

typedef uint32_t irq_key_t;

// Checks if interrupts are enabled
#define IS_IRQ_ENABLED(key) (((key) & 1) == 0)

// Get the current value of the CPU's exception mask register.
// The least significant bit indicates if interrupts are enabled or disabled.
static inline irq_key_t query_irq(void) { return __get_PRIMASK(); }

// Disables interrupts and returns the previous interrupt state.
//
// This function is used to create critical sections by disabling interrupts
// on a Cortex-M platform. It returns the current state of the PRIMASK register,
// which controls the global interrupt enable/disable state.
//
// Important:
// - The `"memory"` clobber is included to prevent the compiler from reordering
//   memory operations across this function, ensuring that all memory accesses
//   efore `irq_lock()` are completed before interrupts are disabled.
// - The order of operations on non-volatile variables relative to this
//   function is not guaranteed without memory barriers or other
//   synchronization mechanisms.
// - When using Link-Time Optimization (LTO), ensure that the behavior of these
//   functions is thoroughly tested, as LTO can lead to more aggressive
//   optimizations. While GCC typically respects the order of `volatile`
//   operations, this is not guaranteed by the C standard.
static inline irq_key_t irq_lock(void) {
  uint32_t key;
  __asm volatile(
      "MRS %0, PRIMASK\n"
      "CPSID i"
      : "=r"(key)
      :
      : "memory"  // Clobber memory to ensure correct memory operations
  );
  return key;
}

// Restores the interrupt state to what it was before `irq_lock`.
//
// This function re-enables interrupts based on the PRIMASK state passed to it.
// It should be used in conjunction with `irq_lock` to restore the previous
// interrupt state after a critical section.
static inline void irq_unlock(irq_key_t key) {
  __asm volatile(
      "MSR PRIMASK, %0\n"
      :
      : "r"(key)
      : "memory"  // Clobber memory to ensure correct memory operations
  );
}

// IRQ priority levels used throughout the system

// Highest priority in the system (only RESET, NMI, and
// HardFault can preempt exceptions at this priority level)
#define IRQ_PRI_HIGHEST NVIC_EncodePriority(NVIC_PRIORITYGROUP_4, 0, 0)

// Standard priority for common interrupt handlers
#define IRQ_PRI_NORMAL NVIC_EncodePriority(NVIC_PRIORITYGROUP_4, 8, 0)

// Lowest priority in the system used by SVC and PENDSV exception handlers
#define IRQ_PRI_LOWEST NVIC_EncodePriority(NVIC_PRIORITYGROUP_4, 15, 0)

#endif  // TREZORHAL_IRQ_H
