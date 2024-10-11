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


#ifndef TREZORHAL_POLL_H
#define TREZORHAL_POLL_H

// Poll events are flags manually set or reset by the drivers to
// wake up the main loop. The main loop waits for these events to
// occur and then processes them.
//
// Events are level-triggered, i.e., they are set by the driver and
// reset by the main loop by calling the driver's specific
// function.

// Touch event
// - Set by the touch driver when any touch event is detected
// - Reset by `touch_get_event()` when all touch events are read
#define POLL_EVENT_TOUCH    (1ULL << 0)

// Button event
// - Set by the button driver when a button event is detected
// - Reset by `button_get_event()` when all button events are read
#define POLL_EVENT_BUTTON   (1ULL << 1)

// Read-ready event (USB, Bluetooth, NFC, etc.)
// - Set by the driver when data is available to read
// - Reset by `io_read_buf()` when no more data is available
#define POLL_EVENT_RRDY(h)  (1ULL << (16 + h * 2))

// Write-ready event (USB, Bluetooth, NFC, etc.)
// - Set by the driver when data can be written
// - Reset by `io_write_buf()` when no more data can be written
#define POLL_EVENT_WRDY(h)  (1ULL << (17 + h * 2))



// The event mask - any combination of the above events
typedef uint32_t poll_mask_t;

// Initialize the event flags
void poll_init();

// Waits for events for a given timeout.
//
// The function blocks until one of the events in the mask is set or
// the timeout is reached. It returns the events that are set or
// 0 if the timeout is reached.
//
// `mask` - the events to wait for
// `timeout` - the maximum time to wait for events in milliseconds
poll_mask_t pool_wait_events(pool_mask_t mask, uint32_t timeout);

// Sets the event flags
//
// Used internally by drivers to signal events to the main loop.
void poll_set_events(poll_mask_t mask);

// Resets the event flags
//
// Used internally by drivers to clear no longer relevant events.
void poll_clear_events(poll_mask_t mask);

#endif  // TREZORHAL_POLL_H
