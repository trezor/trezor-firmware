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

#ifndef TREZORHAL_RANDOM_DELAYS_H
#define TREZORHAL_RANDOM_DELAYS_H

#include <stdint.h>

/*
Random delay interrupts (RDI) is a contermeasure against side channel attacks.
It consists of an interrupt handler that is supposed to be called every
millisecond or so. The handler waits for a random number of cpu ticks that is a
sample of so called floating mean distribution. That means that the number is
the sum of two numbers generated uniformly at random in the interval [0, 255].
The first number is generated freshly for each call of the handler, the other
number is supposed to be refreshed when the device performs an operation that
leaks the current state of the execution flow, such as sending or receiving an
usb packet.

See Differential Power Analysis in the Presence of Hardware Countermeasures by
Christophe Clavier, Jean-Sebastien Coron, Nora Dabbous and Efficient Use of
Random Delays in Embedded Software by Michael Tunstall, Olivier Benoit:
https://link.springer.com/content/pdf/10.1007%2F3-540-44499-8_20.pdf
https://link.springer.com/content/pdf/10.1007%2F978-3-540-72354-7_3.pdf
*/

#ifdef KERNEL_MODE

// Initializes the random number generator for `wait_random()` and the RDI
//
// RDI is stopped by default and can be started by calling
// `random_delays_start_rdi()`.
void random_delays_init(void);

// Starts the RDI, introducing small random delays every millisecond via
// systimer callback.
void random_delays_start_rdi(void);

// Stops the RDI
void random_delays_stop_rdi(void);

// Refreshes the second random number in the floating mean distribution.
// (see the module description above)
void random_delays_refresh_rdi(void);

// Waits for a random number (0-255) of CPU ticks.
//
// This function is independent of the RDI and can be used in any context.
void wait_random(void);

#endif  // KERNEL_MODE

#endif  // TREZORHAL_RANDOM_DELAYS_H
