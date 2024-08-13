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

#ifndef TREZORHAL_SYSTIMER_H
#define TREZORHAL_SYSTIMER_H

#include <stdbool.h>
#include <stdint.h>

#ifdef KERNEL_MODE

// Initializes systimer subsystem
//
// Before calling this function, none of the other functions
// from this module should be called.
void systimer_init(void);

// Deinitialize sytimer subsystem
void systimer_deinit(void);

// Timer handle
typedef struct systimer systimer_t;

// Timer callback routine invoked when timer expires
//
// The callback should be as short as possible and should not
// block. It is invoked from the timer interrupt context.
//
// `context` is the pointer passed to `timer_create`
typedef void (*systimer_callback_t)(void* context);

// Initializes the timer and returns its handle.
//
// There a limited number of timers and `NULL` is returned
// if no timer is available.
systimer_t* systimer_create(systimer_callback_t callback, void* context);

// Deletes the timer
//
// Timer is unset and its resources are released.
void systimer_delete(systimer_t* timer);

// Sets the timer to expire in `delay_ms` milliseconds
//
// If the timer is already set, it will be rescheduled.
void systimer_set(systimer_t* timer, uint32_t delay_ms);

// Sets the timer to expire periodically every `period_ms` milliseconds
//
// If the timer is already set, it will be rescheduled.
void systimer_set_periodic(systimer_t* timer, uint32_t period_ms);

// Unsets the timer (cancels the expiration)
//
// Timer is not deleted and can be set again.
//
// Returns `true` if the timer was unset before its expiration
// so the callback will not be invoked.
bool systimer_unset(systimer_t* timer);

// Timer suspension state (opaque type).
// Allows to recursively suspend/resume timer.
typedef bool systimer_key_t;

// Suspends timer callback invocation
//
// The purpose of this function is to prevent the timer callback
// from being invoked for synchronization purposes. The function
// returns a lock that should be passed to `systimer_resume()` to
// resume the timer callback invocation.
systimer_key_t systimer_suspend(systimer_t* timer);

// Resumes timer callback invocation
//
// The timer callback invocation is resumed. The `key` should
// be the same as returned by `timer_suspend()`.
void systimer_resume(systimer_t* timer, systimer_key_t key);

#endif  // KERNEL_MODE

#endif  // TREZORHAL_SYSTIMER_H
