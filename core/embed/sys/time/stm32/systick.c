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

#include <sys/irq.h>
#include <sys/mpu.h>
#include <sys/systick.h>
#include <sys/systimer.h>
#include "systick_internal.h"

#ifdef KERNEL_MODE

// SysTick driver state
typedef struct {
  // Set if the driver is initialized
  bool initialized;
  // Number of hw cycles per millisecond (tick period)
  uint32_t cycles_per_ms;
  // Number of hw cycles per microsecond
  uint32_t cycles_per_us;
  // Current tick value in hardware cycles
  volatile uint64_t cycles;
  // Number of ticks (ms) since the system start
  volatile uint32_t ticks;
} systick_driver_t;

static systick_driver_t g_systick_driver = {
    .initialized = false,
};

void systick_init(void) {
  systick_driver_t* drv = &g_systick_driver;

  if (drv->initialized) {
    return;
  }

  drv->cycles = 0;
  drv->ticks = 0;

  // Set 1ms tick period
  drv->cycles_per_ms = HAL_RCC_GetSysClockFreq() / 1000;
  drv->cycles_per_us = drv->cycles_per_ms / 1000;

  // Initialize and enable SysTick timer
  SysTick_Config(drv->cycles_per_ms);

  // We need to ensure that SysTick has the expected priority.
  // The SysTick priority is configured in the boardloader,
  // and some early versions didn't set this properly.
  NVIC_SetPriority(SysTick_IRQn, IRQ_PRI_NORMAL);

  drv->initialized = true;
}

void systick_deinit(void) {
  systick_driver_t* drv = &g_systick_driver;

  if (!drv->initialized) {
    return;
  }

  NVIC_DisableIRQ(SysTick_IRQn);
  SysTick->CTRL = 0;
  NVIC_ClearPendingIRQ(SysTick_IRQn);

  drv->initialized = false;
}

void systick_update_freq(void) {
  systick_driver_t* drv = &g_systick_driver;

  if (!drv->initialized) {
    return;
  }

  uint32_t clock_freq = HAL_RCC_GetSysClockFreq();
  drv->cycles_per_ms = clock_freq / 1000;
  drv->cycles_per_us = drv->cycles_per_ms / 1000;
  SysTick_Config(drv->cycles_per_ms);

  // We need to ensure that SysTick has the expected priority.
  // The SysTick priority is configured in the boardloader,
  // and some early versions didn't set this properly.
  NVIC_SetPriority(SysTick_IRQn, IRQ_PRI_NORMAL);
}

uint64_t systick_cycles(void) {
  systick_driver_t* drv = &g_systick_driver;

  irq_key_t irq_key = irq_lock();

  // Current value of the SysTick counter
  uint32_t val = SysTick->VAL;

  // Check if the SysTick has already counted down to 0 or wrapped around
  // Reading CTRL register automatically clears COUNTFLAG
  if ((SysTick->CTRL & SysTick_CTRL_COUNTFLAG_Msk) != 0) {
    // Re-read the current value of the SysTick counter
    val = SysTick->VAL;
    // Update the hardware cycles counter
    // Since we have cleared COUNTFLAG, SysTick_Handler will not increment
    drv->cycles += drv->cycles_per_ms;
    // Increment regular ticks counter
    drv->ticks++;
  }

  uint64_t cycles = drv->cycles + ((val > 0) ? (drv->cycles_per_ms - val) : 0);

  irq_unlock(irq_key);

  return cycles;
}

uint64_t systick_us_to_cycles(uint64_t us) {
  systick_driver_t* drv = &g_systick_driver;

  return us * drv->cycles_per_us;
}

uint32_t systick_ms(void) {
  systick_driver_t* drv = &g_systick_driver;

  return drv->ticks;
}

uint64_t systick_us(void) {
  systick_driver_t* drv = &g_systick_driver;

  if (drv->cycles_per_us == 0) {
    // The driver was not initialized yet - this could happen
    // only if the function is called from the early initialization
    // stage, before the `systick_init()` was called. In this case,
    // we can't provide the correct value, so we return 0.
    return 0;
  }

  return systick_cycles() / drv->cycles_per_us;
}

void SysTick_Handler(void) {
  IRQ_LOG_ENTER();

  mpu_mode_t mpu_mode = mpu_reconfig(MPU_MODE_DEFAULT);

  systick_driver_t* drv = &g_systick_driver;

  if (drv->initialized) {
    // Increment `cycles` counter if COUNTFLAG is set.
    // If COUNTFLAG is not set, `cycles` were already incremented
    // in `systick_cycles()` that also cleared the COUNTFLAG.
    if ((SysTick->CTRL & SysTick_CTRL_COUNTFLAG_Msk) != 0) {
      // Clear COUNTFLAG by reading VAL
      (void)SysTick->VAL;
      // Increment cycles counter by SysTick period
      drv->cycles += drv->cycles_per_ms;
      // Increment regular ticks counter
      drv->ticks++;
    }

    // Invoke callbacks of expired timers
    systimer_dispatch_expired_timers(drv->cycles);
  }

  mpu_restore(mpu_mode);

  IRQ_LOG_EXIT();
}

#endif  // KERNEL_MODE

void systick_delay_us(uint64_t us) {
  uint64_t delay_cycles = systick_us_to_cycles(us);
  int64_t cycles_per_ms = systick_us_to_cycles(1000);

  uint64_t end = systick_cycles() + delay_cycles;
  bool irq_enabled = IS_IRQ_ENABLED(query_irq());
  int64_t diff;

  while ((diff = end - systick_cycles()) > 0) {
    if (irq_enabled && (diff > cycles_per_ms)) {
      // Enter sleep mode and wait for (at least)
      // the SysTick interrupt.
      __WFI();
    }
  }
}

void systick_delay_ms(uint32_t ms) { systick_delay_us((uint64_t)ms * 1000); }

// We provide our own version of HAL_Delay that calls __WFI while waiting,
// and works when interrupts are disabled.  This function is intended to be
// used only by the ST HAL functions.
void HAL_Delay(uint32_t ms) { systick_delay_ms(ms); }

// We provide our own version of HAL_GetTick that replaces the default
// ST HAL function reading uwTick global variable.
uint32_t HAL_GetTick(void) { return systick_ms(); }
