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
#include <sys/systimer.h>
#include "systick_internal.h"

#ifdef KERNEL_MODE

// Maximum number of registered user timer
//
// Consider different implementation (i.e. priority queue
// using binary heap if MAX_SYSTIMERS exceeds 10 or more)
#define MAX_SYSTIMERS 16

// User timer instance
struct systimer {
  // User callback function
  // Non-NULL if the timer entry is valid
  volatile systimer_callback_t callback;
  // User callback context
  void* context;
  // Set if the timer is suspended
  volatile bool suspended;
  // Set if the timer is scheduled
  volatile bool scheduled;
  // Expiration time (valid if scheduled is set)
  volatile uint64_t expiration;
  // Period (= 0 for non-periodic timers)
  volatile uint64_t period;
};

// systimer driver state
typedef struct {
  // Set if the driver is initialized
  bool initialized;
  // Registered timers
  // (unused slots have callback field set to NULL)
  systimer_t timers[MAX_SYSTIMERS];
} systimer_driver_t;

static systimer_driver_t g_systimer_driver = {
    .initialized = false,
};

void systimer_init(void) {
  systimer_driver_t* drv = &g_systimer_driver;

  if (drv->initialized) {
    return;
  }

  memset(drv, 0, sizeof(systimer_driver_t));
  drv->initialized = true;
}

void systimer_deinit(void) {
  systimer_driver_t* drv = &g_systimer_driver;

  drv->initialized = false;
}

static inline bool timer_valid(const systimer_driver_t* drv,
                               const systimer_t* timer) {
  return drv->initialized && (timer >= &drv->timers[0]) &&
         (timer < &drv->timers[MAX_SYSTIMERS]);
}

systimer_t* systimer_create(systimer_callback_t callback, void* context) {
  systimer_driver_t* drv = &g_systimer_driver;

  if (!drv->initialized) {
    return NULL;
  }

  if (callback == NULL) {
    // Since the callback is used to determine if the
    // timer is valid, it must be non-NULL.
    return NULL;
  }

  irq_key_t irq_key = irq_lock();

  // Find a free timer entry
  for (int i = 0; i < MAX_SYSTIMERS; i++) {
    systimer_t* timer = &drv->timers[i];

    if (timer->callback == NULL) {
      timer->scheduled = false;
      timer->suspended = false;
      timer->context = context;
      timer->callback = callback;

      irq_unlock(irq_key);
      return timer;
    }
  }

  // No free timer entry found
  irq_unlock(irq_key);
  return NULL;
}

void systimer_delete(systimer_t* timer) {
  systimer_driver_t* drv = &g_systimer_driver;
  if (!timer_valid(drv, timer)) {
    return;
  }

  timer->callback = NULL;
}

void systimer_set(systimer_t* timer, uint32_t delay_ms) {
  systimer_driver_t* drv = &g_systimer_driver;

  if (!timer_valid(drv, timer)) {
    return;
  }

  uint64_t delay = systick_us_to_cycles((uint64_t)delay_ms * 1000);
  uint64_t expiration = systick_cycles() + delay;

  irq_key_t irq_key = irq_lock();
  timer->expiration = expiration;
  timer->period = 0;
  timer->scheduled = true;
  irq_unlock(irq_key);
}

void systimer_set_periodic(systimer_t* timer, uint32_t period_ms) {
  systimer_driver_t* drv = &g_systimer_driver;

  if (!timer_valid(drv, timer)) {
    return;
  }

  uint64_t period = systick_us_to_cycles((uint64_t)period_ms * 1000);
  uint64_t expiration = systick_cycles() + period;

  irq_key_t irq_key = irq_lock();
  timer->expiration = expiration;
  timer->period = period;
  timer->scheduled = true;
  irq_unlock(irq_key);
}

bool systimer_unset(systimer_t* timer) {
  systimer_driver_t* drv = &g_systimer_driver;

  if (!timer_valid(drv, timer)) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  bool was_scheduled = timer->scheduled;
  timer->scheduled = false;
  irq_unlock(irq_key);
  return was_scheduled;
}

systimer_key_t systimer_suspend(systimer_t* timer) {
  systimer_driver_t* drv = &g_systimer_driver;

  if (!timer_valid(drv, timer)) {
    return false;
  }

  irq_key_t irq_key = irq_lock();
  bool was_suspended = timer->suspended;
  timer->suspended = true;
  irq_unlock(irq_key);
  return was_suspended;
}

void systimer_resume(systimer_t* timer, systimer_key_t key) {
  systimer_driver_t* drv = &g_systimer_driver;

  if (!timer_valid(drv, timer)) {
    return;
  }

  timer->suspended = key;
}

// Called from interrupt context
void systimer_dispatch_expired_timers(uint64_t cycles) {
  systimer_driver_t* drv = &g_systimer_driver;

  if (!drv->initialized) {
    return;
  }

  // Go through all timer slots and invoke callbacks of expired timers
  // This algorithm is not efficient for large number of timers
  // but it is good enough if MAX_SYSTIMERS ~ 10

  for (int i = 0; i < MAX_SYSTIMERS; i++) {
    systimer_t* timer = &drv->timers[i];

    if (timer->callback == NULL || timer->suspended || !timer->scheduled) {
      continue;
    }

    if (cycles < timer->expiration) {
      continue;
    }

    if (timer->period > 0) {
      // Reschedule periodic timer
      timer->expiration = cycles + timer->period;
    } else {
      // Stop one-shot timer
      timer->scheduled = false;
    }

    // Callback is invoked from interrupt context
    timer->callback(timer->context);
  }
}

#endif  // KERNEL_MODE
