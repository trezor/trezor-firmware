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

#include STM32_HAL_H
#include <stdint.h>

// Enables simple IRQ statistics for debugging
#define IRQ_ENABLE_STATS (0)

#if IRQ_ENABLE_STATS
#define IRQ_STATS_MAX (128)
extern uint32_t irq_stats[IRQ_STATS_MAX];
#define IRQ_ENTER(irq) ++irq_stats[irq]
#define IRQ_EXIT(irq)
#else
#define IRQ_ENTER(irq)
#define IRQ_EXIT(irq)
#endif

// Checks if interrupts are enabled
#define IS_IRQ_ENABLED(state) (((state) & 1) == 0)

// Get the current value of the CPU's exception mask register.
// The least significant bit indicates if interrupts are enabled or disabled.
static inline uint32_t query_irq(void) { return __get_PRIMASK(); }

// Restore the CPU's exception mask register to a previous state
static inline void enable_irq(uint32_t state) { __set_PRIMASK(state); }

// Disable all interrupts and return the current state of the
// CPU's exception mask register
static inline uint32_t disable_irq(void) {
  uint32_t state = __get_PRIMASK();
  __disable_irq();
  return state;
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
